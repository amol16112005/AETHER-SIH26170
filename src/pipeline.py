"""End-to-end train / apply pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from src.config import MODELS_DIR, RANDOM_STATE
from src.decisions import calibrate_thresholds, fuse_decision
from src.explain import explain_part
from src.features import attach_lot_relative, lot_stats
from src.metrics import detection_report, drift_mae
from src.module_a import OutlierArtifacts, fit_outlier_models, score_outliers
from src.module_b import DriftModel, fit_drift_models, predict_drift

_OUTPUT_EXACT = {
    "pat_score",
    "pat_hit",
    "pat_reasons",
    "iforest_score",
    "mahalanobis_score",
    "outlier_score",
    "fused_score",
    "decision",
    "decision_stage",
    "decision_reason",
    "hours_saved",
}


def drop_model_outputs(df: pd.DataFrame) -> pd.DataFrame:
    keep = []
    for col in df.columns:
        name = str(col)
        if name in _OUTPUT_EXACT:
            continue
        if name.startswith(("pred_", "extrap_")):
            continue
        if name.endswith(("_exceeds_safety", "_exceeds_datasheet", "_ridge_mae", "_blend_mae", "_safety_slope")):
            continue
        keep.append(col)
    return df.loc[:, keep]


@dataclass
class ScreeningBundle:
    outlier: OutlierArtifacts
    drift: dict[str, DriftModel]
    t_hold: float
    t_rej: float
    train_lots: list[str]
    val_lots: list[str]
    test_lots: list[str]


def lot_splits(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=RANDOM_STATE)
    trainval_idx, test_idx = next(gss.split(df, groups=df["lot_id"]))
    trainval = df.iloc[trainval_idx].reset_index(drop=True)
    test = df.iloc[test_idx].reset_index(drop=True)
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_STATE)
    tr_idx, va_idx = next(gss2.split(trainval, groups=trainval["lot_id"]))
    train = trainval.iloc[tr_idx].reset_index(drop=True)
    val = trainval.iloc[va_idx].reset_index(drop=True)
    return train, val, test


def enrich(df: pd.DataFrame, times: tuple[int, ...] = (0, 24)) -> pd.DataFrame:
    stats = lot_stats(df, times=times)
    return attach_lot_relative(df, stats, times=times)


def apply_models(df: pd.DataFrame, bundle: ScreeningBundle) -> pd.DataFrame:
    scored = drop_model_outputs(df.copy())
    outliers = score_outliers(scored, bundle.outlier)
    drift = predict_drift(scored, bundle.drift)
    merged = pd.concat(
        [scored.reset_index(drop=True), outliers.reset_index(drop=True), drift.reset_index(drop=True)],
        axis=1,
    )
    return fuse_decision(merged, bundle.t_hold, bundle.t_rej)


def train_bundle(df: pd.DataFrame) -> tuple[ScreeningBundle, dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, val, test = lot_splits(df)
    train_e = enrich(train)
    val_e = enrich(val)
    test_e = enrich(test)

    outlier = fit_outlier_models(train_e)
    drift = fit_drift_models(train_e, val_e)

    val_scored = pd.concat(
        [val_e.reset_index(drop=True), score_outliers(val_e, outlier).reset_index(drop=True), predict_drift(val_e, drift).reset_index(drop=True)],
        axis=1,
    )
    # Use a soft pre-fusion score to set thresholds.
    pre = val_scored["outlier_score"].to_numpy() + 0.18 * (
        val_scored[[c for c in val_scored.columns if c.endswith("_exceeds_safety") or c.endswith("_exceeds_datasheet")]]
        .any(axis=1)
        .to_numpy()
        .astype(float)
    )
    t_hold, t_rej = calibrate_thresholds(val_scored["is_defective"].to_numpy(), pre)

    bundle = ScreeningBundle(
        outlier=outlier,
        drift=drift,
        t_hold=t_hold,
        t_rej=t_rej,
        train_lots=sorted(train["lot_id"].unique()),
        val_lots=sorted(val["lot_id"].unique()),
        test_lots=sorted(test["lot_id"].unique()),
    )
    val_out = fuse_decision(val_scored, t_hold, t_rej)
    test_out = apply_models(test_e, bundle)
    train_out = apply_models(train_e, bundle)

    report = {
        "thresholds": {"hold": t_hold, "reject": t_rej},
        "train": detection_report(train_out),
        "val": detection_report(val_out),
        "test": detection_report(test_out),
        "drift_val": drift_mae(val_out),
        "drift_test": drift_mae(test_out),
        "drift_models": {
            p: {
                "ridge_mae": m.ridge_mae,
                "booster_mae": m.booster_mae,
                "blend_mae": m.blend_mae,
                "blend_weight": m.blend,
                "safety_slope": m.safety_slope,
            }
            for p, m in drift.items()
        },
        "splits": {
            "train_lots": bundle.train_lots,
            "val_lots": bundle.val_lots,
            "test_lots": bundle.test_lots,
        },
    }
    return bundle, report, train_out, val_out, test_out


def save_bundle(bundle: ScreeningBundle, path: Path | None = None) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = path or (MODELS_DIR / "screening_bundle.joblib")
    joblib.dump(bundle, path)
    return path


def load_bundle(path: Path | None = None) -> ScreeningBundle:
    path = path or (MODELS_DIR / "screening_bundle.joblib")
    return joblib.load(path)


def inspector_card(part_id: str, screened: pd.DataFrame, bundle: ScreeningBundle) -> dict:
    hit = screened.loc[screened["part_id"] == part_id]
    if hit.empty:
        raise KeyError(part_id)
    return explain_part(hit.iloc[0], bundle.drift)
