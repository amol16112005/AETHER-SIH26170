"""Score published IDDQ / burn-in confirmed-defect ICs with the trained AETHER bundle.

The source table only reports IDDQ (and delay on two parts). Values are converted
to microamps. Each IC is scored against a known-good reference lot (LOT01 healthy
parts) — these twelve devices are not one manufacturing lot, so in-lot PAT among
themselves would be the wrong test.
"""

from __future__ import annotations

import pandas as pd

from src.explain import explain_part, static_vs_dynamic
from src.live_screen import screen_one_part
from src.module_a import iforest_raw_range
from src.pipeline import load_bundle

# part_id, pre-BI IDDQ (uA), first post-BI IDDQ (uA), delay delta ns, defect, mapping note
CASES = [
    ("2274", 20.0, 45.0, 0.0, "gate-to-drain short (128 kOhm)", "pre 20 uA -> 45 / 44 / 43 uA"),
    ("3392", 5400.0, 5350.0, 0.0, "poly-to-poly short (1.63 kOhm)", "pre 5.4 mA, nearly constant"),
    ("2795", 361.0, 56.0, 0.0, "poly-to-NWell short (340 kOhm)", "pre 361 uA -> 56 / 116 / 74 uA (dropped)"),
    ("2890", 343.0, 290.0, 0.0, "poly-to-NWell short (194 kOhm)", "pre 343 uA -> 290 / 165 / 118 uA"),
    ("3488", 5300.0, 212.0, 0.0, "metal-to-metal short (184 Ohm)", "pre 5.3 mA; first post 212 uA then >8 mA at 150 h"),
    ("2663", 131.0, 68.0, 0.50, "poly short in gate-array fill (two defects)", "delay fail +500 ps after 6 h; IDDQ 131 -> 68 uA"),
    ("1787", 2.0, 8000.0, 3.0, "metal-to-metal short (75 Ohm)", "pre 2 uA then stuck-fault + delay + IDDQ >8 mA after 6 h"),
    ("1947", 6.0, 8.0, 0.0, "source-to-drain leakage", "pre 6 uA -> 8 / 9.5 / 9 uA (small rise)"),
    ("2968", 628.0, 660.0, 4.0, "poly-to-diffusion / substrate leakage (28 transistors)", "pre 628 uA -> 660 uA; delay +4 ns at 78 / 150 h"),
    ("3457", 5990.0, 2400.0, 0.0, "leakage in gate array fill logic", "pre 5.99 mA constant -> 2.4 mA / 92 uA / 133 uA"),
    ("2557", 2990.0, 2700.0, 0.0, "leakage in gate array fill logic", "pre 2.99 mA constant -> 2.7 / 2.65 / 2.6 mA"),
    ("2713", 176.0, 288.0, 0.0, "leakage in gate array fill logic", "pre 176 uA constant -> 288 / 410 / 311 uA"),
]


def main() -> None:
    bundle = load_bundle()
    parts = pd.read_csv("data/burnin_parts.csv")
    screened = pd.read_csv("data/screening_results.csv")
    ctx = screened[screened["split"] == "train"]
    if_range = iforest_raw_range(ctx, bundle.outlier)
    ref = parts[(parts["lot_id"] == "LOT01") & (~parts["is_defective"])].copy()
    tpd0 = float(ref["tpd_0h"].median())
    tpd24_nom = float(ref["tpd_24h"].median())

    rows = []
    for part_id, v0, v24, delay_ns, defect, note in CASES:
        meas = {
            "part_id": part_id,
            "lot_id": "LOT01",
            "iddq_0h": v0,
            "iddq_24h": v24,
            "ileak_0h": v0,
            "ileak_24h": v24,
            "tpd_0h": tpd0,
            "tpd_24h": tpd0 + delay_ns if delay_ns else tpd24_nom,
        }
        out = screen_one_part(meas, ref, bundle, iforest_range=if_range).iloc[0]
        brief = explain_part(out, bundle.drift)
        vs = static_vs_dynamic(out)
        rows.append(
            {
                "part_id": part_id,
                "iddq_0h_uA": v0,
                "iddq_24h_uA": v24,
                "static_24h": vs["static"],
                "decision": out["decision"],
                "stage": out["decision_stage"],
                "hours_saved": int(out["hours_saved"]),
                "iddq_24h_z": round(float(out["iddq_24h_z"]), 1),
                "pat_hit": bool(out["pat_hit"]),
                "pred_iddq_168h": round(float(out["pred_iddq_168h"]), 1),
                "fused_score": round(float(out["fused_score"]), 3),
                "actual_defect": defect,
                "mapping": note,
                "reason": str(out["decision_reason"]),
                "brief": brief["inspector_brief"],
            }
        )
        print("=" * 88)
        print(f"IC {part_id}   actual defect: {defect}")
        print(f"  mapped IDDQ  0 h = {v0:g} uA   24 h = {v24:g} uA")
        print(f"  {note}")
        print(
            f"  static datasheet @24 h: {vs['static']}    "
            f"AETHER: {out['decision']} ({out['decision_stage']})"
        )
        print(
            f"  IDDQ z@24 h = {float(out['iddq_24h_z']):.1f}   "
            f"PAT = {bool(out['pat_hit'])}   "
            f"pred 168 h = {float(out['pred_iddq_168h']):.1f} uA   "
            f"score = {float(out['fused_score']):.3f}"
        )
        print(f"  reason: {out['decision_reason']}")
        print(f"  inspector: {brief['inspector_brief']}")

    res = pd.DataFrame(rows)
    print()
    print(res[["part_id", "iddq_0h_uA", "iddq_24h_uA", "static_24h", "decision", "iddq_24h_z", "pred_iddq_168h", "actual_defect"]].to_string(index=False))
    print()
    print("decision counts:", res["decision"].value_counts().to_dict())
    n = len(res)
    print(f"static FAIL {int((res.static_24h == 'FAIL').sum())}/{n}   static PASS {int((res.static_24h == 'PASS').sum())}/{n}")
    caught = int(res["decision"].isin(["REJECT", "HOLD"]).sum())
    print(f"AETHER HOLD+REJECT {caught}/{n}   REJECT {int((res.decision == 'REJECT').sum())}/{n}")
    res.to_csv("data/realtime_iddq_predictions.csv", index=False)
    print("wrote data/realtime_iddq_predictions.csv")


if __name__ == "__main__":
    main()
