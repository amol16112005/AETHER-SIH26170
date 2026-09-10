"""Fuse Module A and Module B into PASS / HOLD / REJECT."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import FN_COST, FP_COST, HOLD_DEFECT_COST, HOLD_HEALTHY_COST, MIN_RECALL, PARAMS


def screening_cost(y_true: np.ndarray, pred: np.ndarray) -> float:
    """pred in {0=PASS, 1=HOLD, 2=REJECT}; y_true is defective flag."""
    cost = 0.0
    for yt, yp in zip(y_true, pred):
        if yp == 2 and yt:
            continue
        if yp == 2 and not yt:
            cost += FP_COST
        elif yp == 0 and yt:
            cost += FN_COST
        elif yp == 0 and not yt:
            continue
        elif yp == 1 and yt:
            cost += HOLD_DEFECT_COST
        else:
            cost += HOLD_HEALTHY_COST
    return float(cost)


def calibrate_thresholds(y_true: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    """t_hold: highest cut that still meets MIN_RECALL. t_rej sits above it."""
    y_true = np.asarray(y_true, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    n_pos = max(int(y_true.sum()), 1)
    candidates = np.unique(np.quantile(scores, np.linspace(0.05, 0.95, 90)))

    def _best_cut(min_rec: float) -> tuple[float | None, float]:
        chosen = None
        best_prec = -1.0
        for t in candidates:
            flagged = scores >= t
            tp = int((flagged & y_true).sum())
            rec = tp / n_pos
            if rec < min_rec:
                continue
            prec = tp / max(int(flagged.sum()), 1)
            if prec > best_prec + 1e-9 or (
                abs(prec - best_prec) < 1e-9 and (chosen is None or t > chosen)
            ):
                best_prec = prec
                chosen = float(t)
        return chosen, best_prec

    t_hold, _ = _best_cut(MIN_RECALL)
    if t_hold is None:
        for min_rec in (0.93, 0.88, 0.80):
            t_hold, _ = _best_cut(min_rec)
            if t_hold is not None:
                break
    if t_hold is None:
        t_hold = float(np.quantile(scores, 0.6))

    above = scores[scores >= t_hold]
    t_rej = float(np.quantile(above, 0.55)) if above.size else t_hold + 0.08
    if t_rej <= t_hold:
        t_rej = t_hold + 0.08
    return t_hold, t_rej


def fuse_decision(df: pd.DataFrame, t_hold: float, t_rej: float) -> pd.DataFrame:
    drift_flag = np.zeros(len(df), dtype=bool)
    drift_reasons = [[] for _ in range(len(df))]
    for param in PARAMS:
        safety = df[f"{param}_exceeds_safety"].to_numpy()
        sheet = df[f"{param}_exceeds_datasheet"].to_numpy()
        drift_flag |= safety | sheet
        for i in range(len(df)):
            if sheet[i]:
                drift_reasons[i].append(f"predicted {param}@168h exceeds 90% of datasheet")
            elif safety[i]:
                drift_reasons[i].append(f"predicted {param} drift exceeds healthy 95th-pct safety slope")

    score = df["outlier_score"].to_numpy() + 0.18 * drift_flag.astype(float)
    decisions: list[str] = []
    stages = []
    why: list[str] = []

    for i in range(len(df)):
        raw = df["pat_reasons"].iloc[i]
        if isinstance(raw, list):
            reasons = list(raw)
        elif isinstance(raw, str) and raw.strip():
            reasons = [part.strip() for part in raw.split("|") if part.strip()]
        else:
            reasons = []
        reasons = reasons + drift_reasons[i]
        pat_hit = bool(df["pat_hit"].iloc[i])
        # Scrap only with two views agreeing: high fused score AND (PAT or unsafe drift).
        if score[i] >= t_rej and (pat_hit or drift_flag[i]):
            decisions.append("REJECT")
            stages.append("EARLY_24H")
            if not reasons:
                reasons.append(f"combined anomaly score {score[i]:.2f} ≥ reject threshold {t_rej:.2f}")
        elif score[i] >= t_hold or drift_flag[i] or pat_hit:
            decisions.append("HOLD")
            stages.append("NEEDS_96H")
            if not reasons:
                reasons.append(f"borderline score {score[i]:.2f}; continue burn-in to 96 h")
        else:
            decisions.append("PASS")
            stages.append("CONTINUE_168H")
            reasons.append("lot-relative parameters and predicted 168 h drift within safety envelope")
        why.append("; ".join(reasons))

    out = df.copy()
    out["fused_score"] = score
    out["decision"] = decisions
    out["decision_stage"] = stages
    out["decision_reason"] = why
    # Flight parts that look healthy still finish burn-in. Hours are only recovered
    # when a doomed part is pulled at 24 h instead of occupying the chamber to 168 h.
    out["hours_saved"] = np.where(out["decision"].eq("REJECT"), 144, 0)
    return out
