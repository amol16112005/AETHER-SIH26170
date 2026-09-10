"""Feature construction for early (0 h / 24 h) screening."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MAD_TO_SIGMA, MIN_SIGMA_FLOOR, PARAMS, PAT_K


def robust_center_scale(values: np.ndarray, floor: float) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 0.0, floor
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    sigma = MAD_TO_SIGMA * mad
    if sigma < floor:
        std = float(np.std(values))
        sigma = max(std, floor)
    return median, sigma


def pat_limits(median: float, sigma: float, sided: str, k: float = PAT_K) -> tuple[float | None, float | None]:
    lo = median - k * sigma
    hi = median + k * sigma
    if sided == "upper":
        return None, hi
    return lo, hi


def lot_stats(df: pd.DataFrame, times: tuple[int, ...] = (0, 24)) -> pd.DataFrame:
    records: list[dict] = []
    for lot_id, group in df.groupby("lot_id"):
        rec: dict = {"lot_id": lot_id, "n_parts": int(len(group))}
        for param in PARAMS:
            for t in times:
                col = f"{param}_{t}h"
                med, sig = robust_center_scale(group[col].to_numpy(), MIN_SIGMA_FLOOR[param])
                rec[f"{col}_median"] = med
                rec[f"{col}_sigma"] = sig
                rec[f"{col}_pat_hi"] = med + PAT_K * sig
                rec[f"{col}_pat_lo"] = med - PAT_K * sig
            v0 = group[f"{param}_0h"].to_numpy()
            v24 = group[f"{param}_24h"].to_numpy()
            slope = (v24 - v0) / 24.0
            med_s, sig_s = robust_center_scale(slope, MIN_SIGMA_FLOOR[param] / 24.0)
            rec[f"{param}_slope24_median"] = med_s
            rec[f"{param}_slope24_sigma"] = sig_s
            rec[f"{param}_slope24_pat_hi"] = med_s + PAT_K * sig_s
        records.append(rec)
    return pd.DataFrame(records)


def attach_lot_relative(df: pd.DataFrame, stats: pd.DataFrame, times: tuple[int, ...] = (0, 24)) -> pd.DataFrame:
    out = df.merge(stats, on="lot_id", how="left")
    for param in PARAMS:
        for t in times:
            col = f"{param}_{t}h"
            out[f"{col}_z"] = (out[col] - out[f"{col}_median"]) / out[f"{col}_sigma"]
        out[f"{param}_slope24"] = (out[f"{param}_24h"] - out[f"{param}_0h"]) / 24.0
        out[f"{param}_rel24"] = (out[f"{param}_24h"] - out[f"{param}_0h"]) / np.maximum(out[f"{param}_0h"], 0.05)
        out[f"{param}_slope24_z"] = (out[f"{param}_slope24"] - out[f"{param}_slope24_median"]) / out[f"{param}_slope24_sigma"]
    return out


def early_model_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cols: list[str] = []
    for param in PARAMS:
        cols.extend(
            [
                f"{param}_0h",
                f"{param}_24h",
                f"{param}_0h_z",
                f"{param}_24h_z",
                f"{param}_slope24",
                f"{param}_rel24",
                f"{param}_slope24_z",
            ]
        )
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing engineered columns: {missing}")
    return df[cols].astype(float), cols


def drift_feature_frame(df: pd.DataFrame, param: str) -> pd.DataFrame:
    v0 = df[f"{param}_0h"].to_numpy(dtype=float)
    v24 = df[f"{param}_24h"].to_numpy(dtype=float)
    return pd.DataFrame(
        {
            f"{param}_0h": v0,
            f"{param}_24h": v24,
            "delta24": v24 - v0,
            "slope24": (v24 - v0) / 24.0,
            "rel24": (v24 - v0) / np.maximum(v0, 0.05),
            "log_v0": np.log(np.maximum(v0, 0.05)),
            "log_v24": np.log(np.maximum(v24, 0.05)),
            "extrap_168": v0 + (v24 - v0) * (168.0 / 24.0),
        }
    )
