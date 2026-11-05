"""
Model zoo + time-split validation.

Every model is scored the same way: TimeSeriesSplit (train on the past, test on
the next block), all test blocks pooled into one out-of-time R^2 and MAE.
Pure logic, no plotting.
"""
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

import config

MODEL_TYPE = {
    "baseline": "mean of train",
    "ridge": "linear",
    "random_forest": "trees (bagging)",
    "sklearn_gbm": "trees (boosting)",
    "xgboost": "trees (boosting)",
}


def make_model(name):
    """New, unfitted model by name (names listed in config.MODELS)."""
    rs = config.RANDOM_STATE
    if name == "baseline":
        return DummyRegressor(strategy="mean")
    if name == "ridge":
        return make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 30)))
    if name == "random_forest":
        return RandomForestRegressor(random_state=rs, n_jobs=-1, **config.RF_PARAMS)
    if name == "sklearn_gbm":
        return GradientBoostingRegressor(random_state=rs, **config.GBM_PARAMS)
    if name == "xgboost":
        return XGBRegressor(random_state=rs, n_jobs=-1, **config.XGB_PARAMS)
    raise ValueError(f"unknown model '{name}'")


def time_split_predict(df, feats, name):
    """Out-of-time predictions: Series aligned to df.index (NaN for the first train block)."""
    y = df[config.TARGET]
    pred = pd.Series(np.nan, index=df.index)
    for tr, te in TimeSeriesSplit(config.CV_FOLDS).split(df):
        mdl = make_model(name).fit(df.loc[tr, feats], y.loc[tr])
        pred.loc[te] = mdl.predict(df.loc[te, feats])
    return pred


def score(df, pred):
    """R^2 and MAE over the rows that have an out-of-time prediction."""
    ok = pred.notna()
    y = df.loc[ok, config.TARGET]
    return r2_score(y, pred[ok]), mean_absolute_error(y, pred[ok]), int(ok.sum())


def leaderboard(df, feats):
    """One row per model x (pooled / pooled + Digester_ID), best R^2 first."""
    dig = [f for f in feats if f.startswith("is_D")]
    process = [f for f in feats if not f.startswith("is_D")]
    variants = [("pooled", process)] + ([("pooled + DigID", process + dig)] if dig else [])
    rows = []
    for name in config.MODELS:
        for variant, cols in variants:
            if name == "baseline" and variant != "pooled":
                continue
            print(f"  scoring {name:14s} {variant}")
            r2, mae, n = score(df, time_split_predict(df, cols, name))
            rows.append({"model": name, "type": MODEL_TYPE[name], "features": variant,
                         "R2": round(r2, 3), "MAE": round(mae, 1), "n_test": n,
                         "pass_gate": r2 >= config.GATE_R2})
    return pd.DataFrame(rows).sort_values("R2", ascending=False).reset_index(drop=True)


def per_digester(df, feats, name="ridge"):
    """Same model trained on each digester alone (process features only) - for comparison."""
    process = [f for f in feats if not f.startswith("is_D")]
    rows = []
    for k, g in df.groupby("digester"):
        g = g.reset_index(drop=True)
        r2, mae, n = score(g, time_split_predict(g, process, name))
        rows.append({"digester": f"D{k}", "model": name, "R2": round(r2, 3), "MAE": round(mae, 1),
                     "n_batches": len(g), "n_test": n})
    return pd.DataFrame(rows)
