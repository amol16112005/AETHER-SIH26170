"""Evaluation tailored to high-reliability screening."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    mean_absolute_error,
    precision_recall_fscore_support,
)

from src.config import PARAMS


DEFECT_LABELS = {
    "maverick": "Maverick",
    "latent_drift": "Latent drift",
    "runaway": "Runaway",
}
_DEFECT_ORDER = ("maverick", "latent_drift", "runaway")


def binary_from_decision(decision: pd.Series) -> np.ndarray:
    """Catch flag: HOLD and REJECT both count. A miss is a defective PASS."""
    return decision.ne("PASS").to_numpy()


def _type_counts(group: pd.DataFrame) -> dict:
    n = int(len(group))
    reject = int(group["decision"].eq("REJECT").sum())
    hold = int(group["decision"].eq("HOLD").sum())
    passed = int(group["decision"].eq("PASS").sum())
    return {
        "n": n,
        "reject": reject,
        "hold": hold,
        "pass": passed,
        "reject_recall": float(reject / n) if n else 0.0,
        "catch_rate": float((reject + hold) / n) if n else 0.0,
    }


def _by_defect_type(df: pd.DataFrame) -> dict[str, dict]:
    if "defect_type" not in df.columns:
        return {}
    present = {str(kind) for kind in df["defect_type"].dropna().unique()}
    ordered = [kind for kind in _DEFECT_ORDER if kind in present]
    ordered += sorted(kind for kind in present if kind not in _DEFECT_ORDER and kind != "healthy")
    out: dict[str, dict] = {}
    for kind in ordered:
        out[kind] = _type_counts(df.loc[df["defect_type"].astype(str) == kind])
    return out


def detection_report(df: pd.DataFrame) -> dict:
    y = df["is_defective"].to_numpy()
    y_bool = np.asarray(y, dtype=bool)
    yhat = binary_from_decision(df["decision"])
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[False, True]).ravel()
    prec, rec, f1, _ = precision_recall_fscore_support(y, yhat, average="binary", zero_division=0)
    latent = np.asarray(df["latent_escape"], dtype=bool)
    latent_caught = int((latent & yhat).sum())
    latent_total = int(latent.sum())
    # How many defectives would a datasheet-only screen miss at 24 h?
    static_24 = np.zeros(len(df), dtype=bool)
    for param in PARAMS:
        col = f"{param}_24h"
        cap = f"datasheet_{param}_max"
        if col not in df.columns or cap not in df.columns:
            continue
        static_24 |= df[col].to_numpy() > df[cap].to_numpy()
        lo_col = f"datasheet_{param}_min"
        if lo_col in df.columns:
            static_24 |= df[col].to_numpy() < df[lo_col].to_numpy()
    static_fn = int((y_bool & ~static_24).sum())

    rejected = df["decision"].eq("REJECT").to_numpy()
    held = df["decision"].eq("HOLD").to_numpy()
    n_def = int(y_bool.sum())
    n_healthy = int((~y_bool).sum())
    reject_tp = int((rejected & y_bool).sum())
    healthy_holds = int((held & ~y_bool).sum())
    n_reject = int(rejected.sum())
    return {
        "n": int(len(df)),
        "defectives": n_def,
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(prec),
        "recall": float(rec),
        "catch_rate": float(rec),
        "f1": float(f1),
        "fn_rate": float(fn / max(n_def, 1)),
        "latent_total": latent_total,
        "latent_caught": latent_caught,
        "latent_catch_rate": float(latent_caught / max(latent_total, 1)),
        "static_24h_missed_defectives": static_fn,
        "hours_saved_total": int(df["hours_saved"].sum()),
        "early_rejects": n_reject,
        "holds": int(held.sum()),
        "passes": int(df["decision"].eq("PASS").sum()),
        "reject_precision": float((rejected & y_bool).sum() / max(n_reject, 1)),
        "reject_only_recall": float(reject_tp / max(n_def, 1)),
        "reject_true_positives": reject_tp,
        "defect_holds": int((held & y_bool).sum()),
        "defect_passes": int((df["decision"].eq("PASS").to_numpy() & y_bool).sum()),
        "healthy_n": n_healthy,
        "healthy_holds": healthy_holds,
        "healthy_hold_rate": float(healthy_holds / max(n_healthy, 1)),
        "healthy_rejects": int((rejected & ~y_bool).sum()),
        "by_defect_type": _by_defect_type(df),
    }


def screening_headline(test: dict) -> str:
    """Pitch line for the frozen run. Catch rate stays separate from REJECT-only recall."""
    if "reject_true_positives" not in test:
        return (
            f"Catch rate {float(test['recall']):.0%} "
            f"({int(test['fn'])} miss / {int(test['defectives'])} defectives)."
        )
    escapes = int(test["fn"])
    escape_txt = "0 escapes" if escapes == 0 else f"{escapes} escapes"
    catch = float(test.get("catch_rate", test["recall"]))
    return (
        f"{escape_txt}: {int(test['reject_true_positives'])} rejected at 24 h, "
        f"{int(test['defect_holds'])} sent to the 96 h check, "
        f"{float(test['healthy_hold_rate']):.1%} of healthy parts held. "
        f"{catch:.0%} is the catch rate (HOLD or REJECT)."
    )


def format_defect_lines(test: dict) -> list[str]:
    lines: list[str] = []
    for kind, row in test.get("by_defect_type", {}).items():
        label = DEFECT_LABELS.get(kind, kind)
        lines.append(
            f"{label}: {row['reject']} REJECT, {row['hold']} HOLD, {row['pass']} PASS "
            f"({row['reject_recall']:.1%} REJECT-only, n={row['n']})"
        )
    return lines


def _format_span(stats: dict, digits: int) -> str:
    mean = float(stats["mean"])
    lo = float(stats["min"])
    hi = float(stats["max"])
    spec = f".{digits}%"
    if f"{lo:{spec}}" == f"{hi:{spec}}":
        return f"{mean:{spec}} on every seed"
    return f"mean {mean:{spec}} (range {lo:{spec}}–{hi:{spec}})"


def summarize_seed_runs(runs: list[dict]) -> dict:
    def span(key: str) -> dict[str, float]:
        vals = [float(run[key]) for run in runs]
        return {"mean": float(np.mean(vals)), "min": float(np.min(vals)), "max": float(np.max(vals))}

    return {
        "n_seeds": len(runs),
        "catch_rate": span("catch_rate"),
        "reject_only_recall": span("reject_only_recall"),
        "healthy_hold_rate": span("healthy_hold_rate"),
        "false_negatives": span("fn"),
    }


def seed_span_line(summary: dict) -> str:
    """Range line. It sits beside the frozen-run pitch line and does not replace it."""
    n = int(summary["n_seeds"])
    fn = summary.get("false_negatives")
    fn_txt = ""
    if fn is not None:
        fn_txt = (
            f" False negatives per seed: mean {float(fn['mean']):.1f} "
            f"(range {float(fn['min']):.0f}–{float(fn['max']):.0f})."
        )
    return (
        f"{n} seeds, each with new synthetic lots and a new lot holdout: "
        f"catch rate {_format_span(summary['catch_rate'], 1)}, "
        f"REJECT-only recall {_format_span(summary['reject_only_recall'], 1)}, "
        f"healthy HOLD rate {_format_span(summary['healthy_hold_rate'], 1)}."
        f"{fn_txt} "
        "The pitch line is the frozen scikit-learn 1.8.0 run, not this average."
    )


def drift_mae(df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for param in PARAMS:
        y_col = f"{param}_168h"
        yhat_col = f"pred_{param}_168h"
        extra_col = f"extrap_{param}_168h"
        if y_col not in df.columns or yhat_col not in df.columns:
            continue
        mask = df[y_col].notna() & df[yhat_col].notna()
        if extra_col in df.columns:
            mask &= df[extra_col].notna()
        if int(mask.sum()) == 0:
            continue
        y = df.loc[mask, y_col].to_numpy(dtype=float)
        yhat = df.loc[mask, yhat_col].to_numpy(dtype=float)
        out[f"{param}_mae"] = float(mean_absolute_error(y, yhat))
        if extra_col in df.columns:
            extra = df.loc[mask, extra_col].to_numpy(dtype=float)
            out[f"{param}_extrap_mae"] = float(mean_absolute_error(y, extra))
        healthy = mask & ~df["is_defective"].astype(bool)
        if int(healthy.sum()):
            out[f"{param}_mae_healthy"] = float(
                mean_absolute_error(df.loc[healthy, y_col], df.loc[healthy, yhat_col])
            )
    return out
