"""
Feature effects: which X matter for Viscosity, in which direction, and do the models agree?

Columns of the feature-effect table:
  direction      sign of the Spearman correlation with Y (all rows)
  ridge_per_unit Ridge coefficient in Y units per 1 unit of X (fit on all rows)
  rf_perm        Random Forest permutation importance on the hold-out (R^2 drop)
  xgb_perm       XGBoost permutation importance on the hold-out (R^2 drop)
  xgb_shap       XGBoost mean |SHAP| on the hold-out (Y units)
  drop_one_dR2   change in XGBoost out-of-time R^2 when this X is removed (negative = it helps)
  rank           mean rank over rf_perm, xgb_perm, xgb_shap, drop_one (1 = most important)

Pure logic, no plotting. Hold-out = last config.TEST_SHARE of rows in time.
"""
import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance

import config
import models
from data import label


def time_holdout(df):
    """(train, test) split by time: the last TEST_SHARE of rows is the test block."""
    cut = int(len(df) * (1 - config.TEST_SHARE))
    return df.iloc[:cut], df.iloc[cut:]


def fit_on_train(df, feats, name):
    """Fit one model on the train block, return (model, train, test)."""
    train, test = time_holdout(df)
    mdl = models.make_model(name).fit(train[feats], train[config.TARGET])
    return mdl, train, test


def shap_values(df, feats):
    """XGBoost SHAP values on the hold-out. Returns (explanation, test rows)."""
    mdl, _, test = fit_on_train(df, feats, "xgboost")
    explainer = shap.TreeExplainer(mdl)
    sv = explainer(test[feats])
    sv.feature_names = [label(f) for f in feats]
    return sv, test


def _perm(df, feats, name):
    mdl, _, test = fit_on_train(df, feats, name)
    pi = permutation_importance(mdl, test[feats], test[config.TARGET], n_repeats=30,
                                random_state=config.RANDOM_STATE, scoring="r2")
    return pd.Series(pi.importances_mean, index=feats)


def _drop_one(df, feats, name="xgboost"):
    base, _, _ = models.score(df, models.time_split_predict(df, feats, name))
    out = {}
    for f in feats:
        rest = [x for x in feats if x != f]
        r2, _, _ = models.score(df, models.time_split_predict(df, rest, name))
        out[f] = r2 - base
    return pd.Series(out)


def feature_effects(df, feats):
    """One row per feature, most important first (see module docstring for columns)."""
    y = df[config.TARGET]
    print("  direction + ridge")
    direction = df[feats].corrwith(y, method="spearman")
    ridge = models.make_model("ridge").fit(df[feats], y)
    ridge_per_unit = pd.Series(ridge[-1].coef_ / df[feats].std().values, index=feats)
    print("  permutation importance (random forest, xgboost)")
    rf_perm = _perm(df, feats, "random_forest")
    xgb_perm = _perm(df, feats, "xgboost")
    print("  SHAP (xgboost)")
    sv, _ = shap_values(df, feats)
    xgb_shap = pd.Series(np.abs(sv.values).mean(axis=0), index=feats)
    print("  drop-one (xgboost, time split)")
    drop = _drop_one(df, feats)

    t = pd.DataFrame({
        "label": [label(f) for f in feats],
        "spearman": direction.round(2),
        "direction": np.where(direction >= 0, "+", "-"),
        "ridge_per_unit": ridge_per_unit.round(3),
        "rf_perm": rf_perm.round(3),
        "xgb_perm": xgb_perm.round(3),
        "xgb_shap": xgb_shap.round(1),
        "drop_one_dR2": drop.round(3),
    }, index=feats)
    ranks = pd.concat([t["rf_perm"].rank(ascending=False), t["xgb_perm"].rank(ascending=False),
                       t["xgb_shap"].rank(ascending=False), t["drop_one_dR2"].rank(ascending=True)], axis=1)
    t["rank"] = ranks.mean(axis=1).round(1)
    return t.sort_values("rank")


def binned_means(df, feat, q=5):
    """Mean Y and count per quantile bin of one feature - the plain-language check of a PDP."""
    bins = pd.qcut(df[feat], q, duplicates="drop")
    return df.groupby(bins, observed=True)[config.TARGET].agg(["mean", "count"]).round(1)
