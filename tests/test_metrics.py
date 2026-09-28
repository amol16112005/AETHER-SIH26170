"""Honest screening counts: HOLD is not a reject, and the frozen run stays quotable."""

from pathlib import Path

import pandas as pd

from src.metrics import detection_report, screening_headline, seed_span_line, summarize_seed_runs

ROOT = Path(__file__).resolve().parents[1]


def _mini_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "is_defective": [True, True, True, False, False],
            "decision": ["REJECT", "HOLD", "PASS", "HOLD", "PASS"],
            "defect_type": ["maverick", "latent_drift", "runaway", "healthy", "healthy"],
            "latent_escape": [True, True, True, False, False],
            "hours_saved": [144, 0, 0, 0, 0],
            "iddq_24h": [1.0, 1.0, 1.0, 1.0, 1.0],
            "ileak_24h": [1.0, 1.0, 1.0, 1.0, 1.0],
            "tpd_24h": [1.0, 1.0, 1.0, 1.0, 1.0],
            "datasheet_iddq_max": [50.0, 50.0, 50.0, 50.0, 50.0],
            "datasheet_ileak_max": [50.0, 50.0, 50.0, 50.0, 50.0],
            "datasheet_tpd_max": [10.0, 10.0, 10.0, 10.0, 10.0],
        }
    )


def test_hold_counts_as_catch_and_not_as_reject():
    report = detection_report(_mini_frame())
    assert report["recall"] == report["catch_rate"] == 2 / 3
    assert report["fn"] == 1
    assert report["reject_only_recall"] == 1 / 3
    assert report["reject_true_positives"] == 1
    assert report["defect_holds"] == 1
    assert report["defect_passes"] == 1
    assert report["healthy_holds"] == 1
    assert report["healthy_n"] == 2
    assert report["healthy_hold_rate"] == 0.5
    assert report["by_defect_type"]["maverick"]["reject"] == 1
    assert report["by_defect_type"]["latent_drift"]["hold"] == 1
    assert report["by_defect_type"]["runaway"]["pass"] == 1
    assert "healthy" not in report["by_defect_type"]
    assert screening_headline(report) == (
        "1 escapes: 1 rejected at 24 h, 1 sent to the 96 h check, "
        "50.0% of healthy parts held. 67% is the catch rate (HOLD or REJECT)."
    )


def test_frozen_test_split_matches_pitch_counts():
    frame = pd.read_csv(ROOT / "data" / "screening_results.csv")
    report = detection_report(frame.loc[frame["split"] == "test"])
    assert report["defectives"] == 102
    assert report["fn"] == 0
    assert report["recall"] == 1.0
    assert report["reject_true_positives"] == 75
    assert report["defect_holds"] == 27
    assert report["early_rejects"] == 76
    assert report["healthy_holds"] == 171
    assert report["healthy_n"] == 1347
    assert report["healthy_rejects"] == 1
    assert report["passes"] == 1175
    assert report["holds"] == 198
    assert abs(report["reject_only_recall"] - 75 / 102) < 1e-12
    assert abs(report["healthy_hold_rate"] - 171 / 1347) < 1e-12
    assert abs(report["reject_precision"] - 75 / 76) < 1e-12
    kinds = report["by_defect_type"]
    assert kinds["maverick"] == {
        "n": 42,
        "reject": 42,
        "hold": 0,
        "pass": 0,
        "reject_recall": 1.0,
        "catch_rate": 1.0,
    }
    assert kinds["latent_drift"]["reject"] == 18
    assert kinds["latent_drift"]["hold"] == 15
    assert kinds["latent_drift"]["pass"] == 0
    assert kinds["runaway"]["reject"] == 15
    assert kinds["runaway"]["hold"] == 12
    assert kinds["runaway"]["pass"] == 0
    assert screening_headline(report) == (
        "0 escapes: 75 rejected at 24 h, 27 sent to the 96 h check, "
        "12.7% of healthy parts held. 100% is the catch rate (HOLD or REJECT)."
    )
    assert "vth_0h" in frame.columns
    assert "idsat_24h" in frame.columns
    assert "irev_0h" in frame.columns
    assert "iddq_25c" in frame.columns


def test_seed_span_line_keeps_the_frozen_run_as_the_pitch():
    summary = summarize_seed_runs(
        [
            {"catch_rate": 1.0, "reject_only_recall": 0.70, "healthy_hold_rate": 0.11, "fn": 0},
            {"catch_rate": 1.0, "reject_only_recall": 0.80, "healthy_hold_rate": 0.15, "fn": 2},
        ]
    )
    line = seed_span_line(summary)
    assert line.startswith("2 seeds, each with new synthetic lots and a new lot holdout:")
    assert "catch rate 100.0% on every seed" in line
    assert "REJECT-only recall mean 75.0% (range 70.0%–80.0%)" in line
    assert "healthy HOLD rate mean 13.0% (range 11.0%–15.0%)" in line
    assert "False negatives per seed: mean 1.0 (range 0–2)." in line
    assert "frozen scikit-learn 1.8.0 run" in line
