"""Plain-language explanations for a QA inspector — not a black box."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import PARAM_META, PARAMS, PAT_K
from src.features import present_params
from src.module_b import DriftModel, ridge_contributions

FEATURE_LABELS = {
    "iddq_0h": "IDDQ @ 0 h",
    "iddq_24h": "IDDQ @ 24 h",
    "ileak_0h": "Leakage @ 0 h",
    "ileak_24h": "Leakage @ 24 h",
    "tpd_0h": "tpd @ 0 h",
    "tpd_24h": "tpd @ 24 h",
    "vth_0h": "VTH @ 0 h",
    "vth_24h": "VTH @ 24 h",
    "idsat_0h": "IDSAT @ 0 h",
    "idsat_24h": "IDSAT @ 24 h",
    "irev_0h": "Reverse leakage @ 0 h",
    "irev_24h": "Reverse leakage @ 24 h",
    "delta24": "24 h change",
    "slope24": "early slope",
    "rel24": "relative change",
    "log_v0": "log(0 h)",
    "log_v24": "log(24 h)",
    "extrap_168": "linear 168 h extrap",
}


def _fmt(value: float, unit: str) -> str:
    if abs(value) >= 10:
        return f"{value:.2f} {unit}"
    return f"{value:.3f} {unit}"


def static_vs_dynamic(row: pd.Series) -> dict[str, Any]:
    """The judging story: datasheet PASS vs lot-relative FAIL."""
    lines: list[str] = []
    static_pass = True
    for param in present_params(pd.DataFrame([row])):
        meta = PARAM_META[param]
        v24 = float(row[f"{param}_24h"])
        cap = float(row.get(f"datasheet_{param}_max", meta["datasheet_max"]))
        z24 = float(row[f"{param}_24h_z"])
        lot_med = float(row[f"{param}_0h_median"])
        lo = meta.get("datasheet_min")
        in_box = v24 <= cap
        if lo is not None:
            in_box = in_box and v24 >= float(lo)
        if not in_box:
            static_pass = False
        if (not in_box) or abs(z24) > 3:
            tag = "STATIC PASS" if in_box else "STATIC FAIL"
            dyn = "lot outlier" if abs(z24) > PAT_K else ("elevated vs lot" if abs(z24) > 3 else "in-lot")
            lines.append(
                f"{meta['label']}: {_fmt(v24, meta['unit'])} vs datasheet {_fmt(cap, meta['unit'])} → {tag}. "
                f"Lot median {_fmt(lot_med, meta['unit'])}, robust z = {z24:.1f} → {dyn}."
            )
    if not lines:
        lines.append("Every 24 h reading is both inside the datasheet box and close to the lot centroid.")
    return {
        "static": "PASS" if static_pass else "FAIL",
        "dynamic": str(row.get("decision", "")),
        "lines": lines,
        "is_textbook": bool(row.get("sih_example", False)),
    }


def explain_part(row: pd.Series, drift_models: dict[str, DriftModel]) -> dict[str, Any]:
    pat_bullets: list[str] = []
    drift_bullets: list[str] = []
    param_cards: list[dict[str, Any]] = []

    if "iddq_ea_z" in row.index and pd.notna(row["iddq_ea_z"]) and abs(float(row["iddq_ea_z"])) > PAT_K:
        tcoeff = float(row["iddq_tcoeff"]) if "iddq_tcoeff" in row.index and pd.notna(row["iddq_tcoeff"]) else float("nan")
        pat_bullets.append(
            f"IDDQ temperature coefficient is a lot outlier (activation-energy proxy z = {float(row['iddq_ea_z']):.1f}"
            + (f", {tcoeff:.4f} µA/°C" if tcoeff == tcoeff else "")
            + "). Weak T-dependence is a metallic / oxide-short signature."
        )

    for param in present_params(pd.DataFrame([row])):
        if param not in drift_models or f"pred_{param}_168h" not in row.index:
            continue
        meta = PARAM_META[param]
        unit = meta["unit"]
        v0 = float(row[f"{param}_0h"])
        v24 = float(row[f"{param}_24h"])
        z0 = float(row[f"{param}_0h_z"])
        z24 = float(row[f"{param}_24h_z"])
        slope_z = float(row[f"{param}_slope24_z"])
        pred = float(row[f"pred_{param}_168h"])
        actual = float(row[f"{param}_168h"]) if f"{param}_168h" in row and pd.notna(row[f"{param}_168h"]) else None
        lot_med = float(row[f"{param}_0h_median"])
        pat_hi = float(row[f"{param}_24h_pat_hi"])
        safety = float(row[f"{param}_safety_slope"])
        slope = float(row[f"{param}_slope24"])
        aging = meta.get("aging", "up")

        if abs(z24) > PAT_K:
            pat_bullets.append(
                f"{meta['label']} at 24 h is {_fmt(v24, unit)} — {z24:.1f} robust σ from the lot "
                f"median ({_fmt(lot_med, unit)}). Datasheet max is {_fmt(meta['datasheet_max'], unit)}, "
                f"so a static screen would miss this maverick."
            )
        elif abs(z24) > 3:
            pat_bullets.append(
                f"{meta['label']} at 24 h sits {z24:.1f} σ from the lot centroid "
                f"({_fmt(v24, unit)} vs lot {_fmt(lot_med, unit)})."
            )

        if (aging == "down" and slope_z < -PAT_K) or (aging != "down" and slope_z > PAT_K):
            pat_bullets.append(
                f"{meta['label']} is drifting {slope_z:.1f} σ faster than the lot "
                f"({slope:.4f} {unit}/h vs safety {safety:.4f} {unit}/h)."
            )

        if bool(row[f"{param}_exceeds_datasheet"]):
            drift_bullets.append(
                f"Predicted {meta['label']} at 168 h is {_fmt(pred, unit)}, past 90% of the "
                f"datasheet envelope ({_fmt(meta['datasheet_max'], unit)}). Early reject is safer than waiting."
            )
        elif bool(row[f"{param}_exceeds_safety"]):
            if aging == "down":
                drift_bullets.append(
                    f"Predicted 168 h {meta['label']} drop exceeds the healthy 5th-percentile safety slope."
                )
            else:
                drift_bullets.append(
                    f"Predicted 168 h {meta['label']} drift exceeds the healthy 95th-percentile safety slope."
                )

        contrib = ridge_contributions(row, drift_models[param])
        parts = [(k, v) for k, v in contrib.items() if k not in {"intercept", "prediction"}]
        parts_sorted = sorted(parts, key=lambda kv: abs(kv[1]), reverse=True)

        param_cards.append(
            {
                "param": param,
                "label": meta["label"],
                "unit": unit,
                "v0": v0,
                "v24": v24,
                "z0": z0,
                "z24": z24,
                "pred_168": pred,
                "actual_168": actual,
                "pat_hi_24": pat_hi,
                "datasheet_max": meta["datasheet_max"],
                "slope": slope,
                "safety_slope": safety,
                "ridge_top": [
                    {"feature": FEATURE_LABELS.get(k, k), "contribution": v} for k, v in parts_sorted[:3]
                ],
                "ridge_all": [
                    {"feature": FEATURE_LABELS.get(k, k), "contribution": v} for k, v in parts_sorted
                ],
                "ridge_intercept": contrib["intercept"],
                "ridge_prediction": contrib["prediction"],
            }
        )

    decision = str(row["decision"])
    if decision == "REJECT":
        headline = "Recommend REJECT at 24 h — pull this part from the chamber. Continuing burn-in only occupies a slot."
    elif decision == "HOLD":
        headline = "HOLD for a 96 h confirmation readout. Not a clean pass, not yet a confident reject."
    else:
        headline = "PASS relative to this lot. Complete the remaining burn-in; predicted 168 h drift stays inside the safety envelope."

    bullets = pat_bullets + drift_bullets
    if not bullets:
        bullets.append(
            "No single parameter is a PAT outlier. Combined score and predicted drift are inside limits."
        )

    inspector_brief = (
        f"Part {row['part_id']} (lot {row['lot_id']}) → {decision}. {headline} "
        + " ".join(bullets[:2])
    )

    return {
        "part_id": row["part_id"],
        "lot_id": row["lot_id"],
        "decision": decision,
        "headline": headline,
        "bullets": bullets,
        "inspector_brief": inspector_brief,
        "outlier_score": float(row["outlier_score"]),
        "fused_score": float(row["fused_score"]),
        "iforest_score": float(row["iforest_score"]),
        "mahalanobis_score": float(row["mahalanobis_score"]),
        "pat_hit": bool(row["pat_hit"]),
        "hours_saved": int(row["hours_saved"]),
        "defect_type": row.get("defect_type", "unknown"),
        "param_cards": param_cards,
        "static_vs_dynamic": static_vs_dynamic(row),
    }
