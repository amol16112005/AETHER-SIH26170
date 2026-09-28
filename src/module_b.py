"""Module B — 24 h → 168 h drift predictor.

A linear extrapolation is the physics baseline (constant aging rate at fixed
125 °C). Ridge regression on engineered features is the primary model because
every coefficient is inspectable by a QA engineer. A histogram gradient
boosting model is blended in only when it reduces validation MAE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import PARAM_META, PARAMS, RANDOM_STATE
from src.features import drift_feature_frame


@dataclass
class DriftModel:
    param: str
    ridge: Pipeline
    booster: HistGradientBoostingRegressor
    blend: float  # weight on booster in [0, 1]
    feature_names: list[str]
    ridge_mae: float
    booster_mae: float
    blend_mae: float
    safety_slope: float  # 95th percentile healthy slope from 0→168 h


def _fit_one(train: pd.DataFrame, val: pd.DataFrame, param: str) -> DriftModel:
    y_train = train[f"{param}_168h"].to_numpy(dtype=float)
    y_val = val[f"{param}_168h"].to_numpy(dtype=float)
    X_train = drift_feature_frame(train, param)
    X_val = drift_feature_frame(val, param)

    ridge = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", RidgeCV(alphas=np.logspace(-3, 3, 13))),
        ]
    )
    ridge.fit(X_train, y_train)
    ridge_pred = ridge.predict(X_val)
    ridge_mae = float(mean_absolute_error(y_val, ridge_pred))

    booster = HistGradientBoostingRegressor(
        max_depth=4,
        learning_rate=0.06,
        max_iter=250,
        l2_regularization=0.1,
        random_state=RANDOM_STATE,
    )
    booster.fit(X_train, y_train)
    boost_pred = booster.predict(X_val)
    boost_mae = float(mean_absolute_error(y_val, boost_pred))

    best_w, best_mae = 0.0, ridge_mae
    for w in (0.0, 0.25, 0.4, 0.55, 0.7):
        pred = (1 - w) * ridge_pred + w * boost_pred
        mae = float(mean_absolute_error(y_val, pred))
        if mae < best_mae:
            best_w, best_mae = w, mae

    healthy = train.loc[~train["is_defective"], f"{param}_168h"] - train.loc[~train["is_defective"], f"{param}_0h"]
    healthy_slope = (healthy / 168.0).to_numpy()
    aging = PARAM_META[param].get("aging", "up")
    if len(healthy_slope) == 0:
        safety_slope = 0.0
    elif aging == "down":
        safety_slope = float(np.quantile(healthy_slope, 0.05))
    else:
        safety_slope = float(np.quantile(healthy_slope, 0.95))

    return DriftModel(
        param=param,
        ridge=ridge,
        booster=booster,
        blend=best_w,
        feature_names=list(X_train.columns),
        ridge_mae=ridge_mae,
        booster_mae=boost_mae,
        blend_mae=best_mae,
        safety_slope=safety_slope,
    )


def fit_drift_models(train: pd.DataFrame, val: pd.DataFrame) -> dict[str, DriftModel]:
    return {param: _fit_one(train, val, param) for param in PARAMS}


def predict_drift(df: pd.DataFrame, models: dict[str, DriftModel]) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for param, model in models.items():
        if f"{param}_0h" not in df.columns or f"{param}_24h" not in df.columns:
            continue
        X = drift_feature_frame(df, param)
        ridge_pred = model.ridge.predict(X)
        boost_pred = model.booster.predict(X)
        pred = (1.0 - model.blend) * ridge_pred + model.blend * boost_pred
        extrap = X["extrap_168"].to_numpy()
        v0 = df[f"{param}_0h"].to_numpy(dtype=float)
        slope_pred = (pred - v0) / 168.0
        meta = PARAM_META[param]
        datasheet = meta["datasheet_max"]
        aging = meta.get("aging", "up")
        lo = meta.get("datasheet_min")
        if aging == "down":
            exceeds_safety = slope_pred < (model.safety_slope * 1.5)
        else:
            exceeds_safety = slope_pred > (model.safety_slope * 1.5)
        exceeds_sheet = pred > (0.90 * datasheet)
        if lo is not None:
            exceeds_sheet = exceeds_sheet | (pred < (1.10 * float(lo)))
        out[f"pred_{param}_168h"] = pred
        out[f"extrap_{param}_168h"] = extrap
        out[f"pred_{param}_slope"] = slope_pred
        out[f"{param}_safety_slope"] = model.safety_slope
        out[f"{param}_exceeds_safety"] = exceeds_safety
        out[f"{param}_exceeds_datasheet"] = exceeds_sheet
        out[f"{param}_ridge_mae"] = model.ridge_mae
        out[f"{param}_blend_mae"] = model.blend_mae
    return out


def ridge_contributions(row: pd.Series, model: DriftModel) -> dict[str, float]:
    """Approximate per-feature additive contributions in original target units."""
    X = drift_feature_frame(pd.DataFrame([row]), model.param)
    scaler: StandardScaler = model.ridge.named_steps["scaler"]
    ridge = model.ridge.named_steps["model"]
    z = scaler.transform(X)[0]
    contrib = z * ridge.coef_
    return {
        "intercept": float(ridge.intercept_),
        **{name: float(val) for name, val in zip(model.feature_names, contrib)},
        "prediction": float(model.ridge.predict(X)[0]),
    }
