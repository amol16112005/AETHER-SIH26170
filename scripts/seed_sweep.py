"""Five-seed ranges for catch rate, REJECT-only recall, and healthy HOLD rate.

Each seed regenerates the synthetic lots and redraws the lot holdout. Results
go to models/metrics_seeds.json. This script does not replace
models/screening_bundle.joblib, models/metrics.json, data/screening_results.csv,
or data/burnin_parts.csv. The pitch numbers stay the frozen scikit-learn 1.8.0 run.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sklearn

from src.config import DATA_DIR, MODELS_DIR
from src.generate_data import generate_burnin_dataset
from src.metrics import summarize_seed_runs
from src.pipeline import train_bundle

DEFAULT_SEEDS = (42, 7, 11, 19, 23)
PROTECTED = (
    DATA_DIR / "burnin_parts.csv",
    DATA_DIR / "screening_results.csv",
    MODELS_DIR / "screening_bundle.joblib",
    MODELS_DIR / "metrics.json",
)
FROZEN_TEST = {
    "defectives": 102,
    "fn": 0,
    "reject_true_positives": 75,
    "defect_holds": 27,
    "healthy_holds": 171,
    "healthy_n": 1347,
    "passes": 1175,
    "holds": 198,
    "early_rejects": 76,
}


def _fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_slice(seed: int) -> dict:
    df = generate_burnin_dataset(seed=seed)
    _bundle, report, _train, _val, _test = train_bundle(df, split_seed=seed)
    test = report["test"]
    row = {
        "data_seed": seed,
        "split_seed": seed,
        "test_lots": report["splits"]["test_lots"],
        "n": test["n"],
        "defectives": test["defectives"],
        "fn": test["fn"],
        "catch_rate": test["catch_rate"],
        "reject_only_recall": test["reject_only_recall"],
        "reject_true_positives": test["reject_true_positives"],
        "defect_holds": test["defect_holds"],
        "healthy_hold_rate": test["healthy_hold_rate"],
        "healthy_holds": test["healthy_holds"],
        "healthy_n": test["healthy_n"],
        "passes": test["passes"],
        "holds": test["holds"],
        "early_rejects": test["early_rejects"],
        "by_defect_type": test["by_defect_type"],
    }
    if seed == 42:
        row["matches_frozen_test_counts"] = all(test[key] == value for key, value in FROZEN_TEST.items())
    return row


def main(seeds: list[int]) -> None:
    if sklearn.__version__ != "1.8.0":
        raise SystemExit(
            f"Refusing to sweep on scikit-learn {sklearn.__version__}. The frozen bundle is pinned to 1.8.0."
        )
    before = {path: _fingerprint(path) for path in PROTECTED}
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / "metrics_seeds.json"
    runs: list[dict] = []
    for seed in seeds:
        print(f"seed {seed} — training, not writing the frozen bundle", flush=True)
        runs.append(_run_slice(seed))
        payload = {
            "sklearn": sklearn.__version__,
            "seeds": seeds,
            "note": (
                "Each seed regenerates synthetic lots and redraws the lot holdout. "
                "Pitch numbers stay on the frozen scikit-learn 1.8.0 run in metrics.json."
            ),
            "runs": runs,
        }
        if len(runs) == len(seeds):
            payload["summary"] = summarize_seed_runs(runs)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        test = runs[-1]
        print(
            f"seed {seed} done  catch {test['catch_rate']:.3f}  "
            f"reject-only {test['reject_only_recall']:.3f}  "
            f"healthy HOLD {test['healthy_hold_rate']:.3f}  "
            f"FN {test['fn']}/{test['defectives']}",
            flush=True,
        )

    after = {path: _fingerprint(path) for path in PROTECTED}
    moved = [str(path) for path in PROTECTED if before[path] != after[path]]
    if moved:
        raise SystemExit("Sweep touched frozen artifacts: " + ", ".join(moved))
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    chosen = [int(arg) for arg in sys.argv[1:]] or list(DEFAULT_SEEDS)
    main(chosen)
