"""Train screening models and write evaluation artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR, MODELS_DIR
from src.generate_data import save_dataset
from src.pipeline import save_bundle, train_bundle
import pandas as pd


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "burnin_parts.csv"
    print("Generating synthetic burn-in lots...")
    save_dataset(csv_path)

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} parts across {df['lot_id'].nunique()} lots")
    bundle, report, train_out, val_out, test_out = train_bundle(df)
    save_bundle(bundle)

    screened = pd.concat(
        [
            train_out.assign(split="train"),
            val_out.assign(split="val"),
            test_out.assign(split="test"),
        ],
        ignore_index=True,
    )
    # pat_reasons is a list; stringify for CSV.
    screened = screened.copy()
    screened["pat_reasons"] = screened["pat_reasons"].apply(
        lambda xs: " | ".join(xs) if isinstance(xs, list) else xs
    )
    screened.to_csv(DATA_DIR / "screening_results.csv", index=False)

    report_path = MODELS_DIR / "metrics.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    t = report["test"]
    d = report["drift_test"]
    print("\n=== Held-out lots (Module A) ===")
    print(f"  Recall {t['recall']:.3f}   Precision {t['precision']:.3f}   FN {t['fn']}/{t['defectives']}")
    print(f"  Latent-escape catch rate {t['latent_catch_rate']:.3f}  ({t['latent_caught']}/{t['latent_total']})")
    print(f"  Static 24 h screen would miss {t['static_24h_missed_defectives']} defectives")
    print(f"  Decisions  PASS={t['passes']}  HOLD={t['holds']}  REJECT={t['early_rejects']}  (reject precision {t['reject_precision']:.3f})")
    print(f"  Chamber hours saved {t['hours_saved_total']}")
    print("\n=== Held-out lots (Module B MAE @ 168 h) ===")
    for param in ("iddq", "ileak", "tpd"):
        print(f"  {param:6s}  model {d[f'{param}_mae']:.4f}   linear-extrap {d[f'{param}_extrap_mae']:.4f}")
    print(f"\nWrote {MODELS_DIR / 'screening_bundle.joblib'}")
    print(f"Wrote {report_path}")
    print(f"Wrote {DATA_DIR / 'screening_results.csv'}")


if __name__ == "__main__":
    main()
