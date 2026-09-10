import pandas as pd

from src.generate_data import generate_burnin_dataset
from src.metrics import detection_report, drift_mae
from src.pipeline import train_bundle


def test_end_to_end_high_recall_on_held_out_lots():
    df = generate_burnin_dataset(n_lots=10, parts_per_lot=(80, 100), seed=7)
    bundle, report, _train, _val, test_out = train_bundle(df)

    assert bundle.t_rej > bundle.t_hold
    assert report["test"]["recall"] >= 0.85
    assert report["test"]["fn_rate"] <= 0.15
    assert report["test"]["latent_catch_rate"] >= 0.80

    mae = drift_mae(test_out)
    assert mae["iddq_mae"] < 4.0
    assert mae["ileak_mae"] < 2.5
    assert mae["tpd_mae"] < 0.8


def test_dataset_contains_latent_escapes():
    df = generate_burnin_dataset(n_lots=8, parts_per_lot=(90, 110), seed=3)
    assert df["latent_escape"].sum() > 0
    assert set(df["defect_type"]) >= {"healthy", "maverick", "latent_drift", "runaway"}
    assert df["lot_id"].nunique() == 9
    assert "LOTSIH" in set(df["lot_id"])
    assert pd.api.types.is_numeric_dtype(df["iddq_0h"])
