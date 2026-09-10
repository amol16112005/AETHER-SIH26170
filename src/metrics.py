"""Evaluation tailored to high-reliability screening."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    mean_absolute_error,
    precision_recall_fscore_support,
)

from src.config import PARAMS


def binary_from_decision(decision: pd.Series) -> np.ndarray:
    return decision.ne("PASS").to_numpy()


def detection_report(df: pd.DataFrame) -> dict:
    y = df["is_defective"].to_numpy()
    yhat = binary_from_decision(df["decision"])
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[False, True]).ravel()
    prec, rec, f1, _ = precision_recall_fscore_support(y, yhat, average="binary", zero_division=0)
    latent = df["latent_escape"].to_numpy()
    latent_caught = int((latent & yhat).sum())
    latent_total = int(latent.sum())
    static_only = df["static_fail"].to_numpy()
    # How many defectives would a datasheet-only screen miss at 24 h?
    static_24 = np.zeros(len(df), dtype=bool)
    for param in PARAMS:
        static_24 |= df[f"{param}_24h"] > df[f"datasheet_{param}_max"]
    static_fn = int((y & ~static_24).sum())
    return {
        "n": int(len(df)),
        "defectives": int(y.sum()),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "fn_rate": float(fn / max(int(y.sum()), 1)),
        "latent_total": latent_total,
        "latent_caught": latent_caught,
        "latent_catch_rate": float(latent_caught / max(latent_total, 1)),
        "static_24h_missed_defectives": static_fn,
        "hours_saved_total": int(df["hours_saved"].sum()),
        "early_rejects": int(df["decision"].eq("REJECT").sum()),
        "holds": int(df["decision"].eq("HOLD").sum()),
        "passes": int(df["decision"].eq("PASS").sum()),
        "reject_precision": float((df["decision"].eq("REJECT") & df["is_defective"]).sum() / max(int(df["decision"].eq("REJECT").sum()), 1)),
    }


def drift_mae(df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for param in PARAMS:
        y = df[f"{param}_168h"].to_numpy(dtype=float)
        yhat = df[f"pred_{param}_168h"].to_numpy(dtype=float)
        extra = df[f"extrap_{param}_168h"].to_numpy(dtype=float)
        out[f"{param}_mae"] = float(mean_absolute_error(y, yhat))
        out[f"{param}_extrap_mae"] = float(mean_absolute_error(y, extra))
        out[f"{param}_mae_healthy"] = float(
            mean_absolute_error(y[~df["is_defective"]], yhat[~df["is_defective"]])
        )
    return out
