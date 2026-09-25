"""Module A — dynamic, lot-relative outlier detection.

Static datasheet limits catch gross failures. This module flags parts that are
anomalous *relative to their lot*, which is the PAT / DPAT idea used in
automotive and space screening.

Three complementary views are fused:

1. Robust one-sided PAT on each parameter (median + k·MAD).
2. Isolation Forest on lot-normalized early features.
3. Robust Mahalanobis distance on the 0 h / 24 h vector.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.covariance import EmpiricalCovariance, MinCovDet
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from src.config import IFOREST_CONTAMINATION, PARAM_META, PARAMS, PAT_K, RANDOM_STATE
from src.features import early_model_matrix


@dataclass
class OutlierArtifacts:
    scaler: RobustScaler
    iforest: IsolationForest
    cov: object
    feature_names: list[str]
    maha_names: list[str]


def _pat_flags(df: pd.DataFrame) -> pd.DataFrame:
    flags = pd.DataFrame(index=df.index)
    score = np.zeros(len(df), dtype=float)
    reasons = [[] for _ in range(len(df))]

    for param in PARAMS:
        sided = PARAM_META[param]["sided"]
        for t in (0, 24):
            col = f"{param}_{t}h"
            z = df[f"{col}_z"].to_numpy()
            if sided == "upper":
                hit = z > PAT_K
                contrib = np.clip(z / PAT_K, 0, None)
            else:
                hit = np.abs(z) > PAT_K
                contrib = np.clip(np.abs(z) / PAT_K, 0, None)
            flags[f"pat_{col}"] = hit
            score += contrib
            for i, is_hit in enumerate(hit):
                if is_hit:
                    reasons[i].append(f"PAT {param}@{t}h z={z[i]:.2f}")
        z_s = df[f"{param}_slope24_z"].to_numpy()
        hit_s = z_s > PAT_K
        flags[f"pat_{param}_slope24"] = hit_s
        score += np.clip(z_s / PAT_K, 0, None)
        for i, is_hit in enumerate(hit_s):
            if is_hit:
                reasons[i].append(f"PAT {param} slope z={z_s[i]:.2f}")

    flags["pat_score"] = score
    flags["pat_hit"] = flags.filter(like="pat_").drop(columns=["pat_score"]).any(axis=1)
    flags["pat_reasons"] = reasons
    return flags


def fit_outlier_models(df: pd.DataFrame) -> OutlierArtifacts:
    X, names = early_model_matrix(df)
    scaler = RobustScaler()
    Xs = scaler.fit_transform(X)

    iforest = IsolationForest(
        n_estimators=400,
        contamination=IFOREST_CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    iforest.fit(Xs)

    # z-only vector is already lot-normalized and much better conditioned than
    # the raw+delta+log mix Isolation Forest sees.
    maha_names = [n for n in names if n.endswith("_z")]
    Z = X[maha_names].to_numpy(dtype=float)
    try:
        cov = MinCovDet(random_state=RANDOM_STATE, support_fraction=0.9)
        cov.fit(Z)
    except ValueError:
        cov = EmpiricalCovariance()
        cov.fit(Z)

    return OutlierArtifacts(
        scaler=scaler,
        iforest=iforest,
        cov=cov,
        feature_names=names,
        maha_names=maha_names,
    )


def iforest_raw_range(df: pd.DataFrame, art: OutlierArtifacts) -> tuple[float, float]:
    """Min/max of -decision_function on a reference population.

    Live scoring of one part (or a small uploaded lot) must use this range so
    Isolation Forest scores stay on the same scale as the calibrated thresholds.
    """
    X, _ = early_model_matrix(df)
    Xs = art.scaler.transform(X)
    raw_if = -art.iforest.decision_function(Xs)
    return float(np.min(raw_if)), float(np.max(raw_if))


def score_outliers(
    df: pd.DataFrame,
    art: OutlierArtifacts,
    iforest_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    X, _ = early_model_matrix(df)
    Xs = art.scaler.transform(X)

    # sklearn IF: lower decision_function => more anomalous. Map to [0, 1]-ish.
    raw_if = -art.iforest.decision_function(Xs)
    if iforest_range is not None:
        lo, hi = iforest_range
    else:
        lo = float(np.min(raw_if))
        hi = float(np.max(raw_if))
    if_score = (raw_if - lo) / ((hi - lo) + 1e-9)

    Z = X[art.maha_names].to_numpy(dtype=float)
    maha = art.cov.mahalanobis(Z)
    maha_score = np.clip(maha / (Z.shape[1] * 4.0), 0, 3) / 3.0

    pat = _pat_flags(df)
    pat_norm = np.clip(pat["pat_score"].to_numpy() / 4.0, 0, 1)

    combined = 0.40 * pat_norm + 0.35 * if_score + 0.25 * maha_score

    out = pd.DataFrame(
        {
            "pat_score": pat["pat_score"].to_numpy(),
            "pat_hit": pat["pat_hit"].to_numpy(),
            "pat_reasons": pat["pat_reasons"].to_numpy(),
            "iforest_score": if_score,
            "mahalanobis_score": maha_score,
            "outlier_score": combined,
        },
        index=df.index,
    )
    return out
