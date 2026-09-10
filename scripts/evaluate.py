"""Print SIH26170 judging metrics from the held-out lot report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import MODELS_DIR
from src.explain import explain_part
from src.pipeline import load_bundle


def main() -> None:
    report = json.loads((MODELS_DIR / "metrics.json").read_text(encoding="utf-8"))
    t = report["test"]
    d = report["drift_test"]
    print("SIH26170 — held-out lots")
    print("=" * 56)
    print("\n1. Anomaly Detection Score  (false negatives are catastrophic)")
    print(f"   Recall                 {t['recall']:.1%}")
    print(f"   False negatives        {t['fn']} / {t['defectives']}")
    print(f"   Latent-escape catch    {t['latent_catch_rate']:.1%}  ({t['latent_caught']}/{t['latent_total']})")
    print(f"   Static 24 h misses     {t['static_24h_missed_defectives']} defectives (datasheet only)")
    print("\n2. Drift Prediction Accuracy  (MAE vs hidden Value_168h)")
    print(f"   IDDQ                   {d['iddq_mae']:.4f} µA   (linear extrap {d['iddq_extrap_mae']:.4f})")
    print(f"   Leakage                {d['ileak_mae']:.4f} µA   (linear extrap {d['ileak_extrap_mae']:.4f})")
    print(f"   Propagation delay      {d['tpd_mae']:.4f} ns  (linear extrap {d['tpd_extrap_mae']:.4f})")
    print("\n3. Explainability")
    results = ROOT / "data" / "screening_results.csv"
    if results.exists():
        df = pd.read_csv(results)
        bundle = load_bundle()
        if "sih_example" in df.columns and df["sih_example"].astype(bool).any():
            row = df.loc[df["sih_example"].astype(bool)].iloc[0]
            card = explain_part(row, bundle.drift)
            contrast = card["static_vs_dynamic"]
            print(f"   Textbook part          {card['part_id']}")
            print(f"   Static datasheet       {contrast['static']}")
            print(f"   Dynamic lot-relative   {contrast['dynamic']}")
            print(f"   Inspector brief        {card['inspector_brief']}")
        else:
            print("   QA inspector briefs are generated per part in the dashboard.")
    print()


if __name__ == "__main__":
    main()
