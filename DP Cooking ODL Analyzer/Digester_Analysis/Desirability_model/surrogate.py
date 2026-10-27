"""
Surrogate model X -> Y for the DP cooking quality targets.

Step 0 gate: before any optimization we must know whether the process features
can predict Kappa / Viscosity at all. This module fits Linear and RandomForest
models per target and reports test R^2 + feature importance. If R^2 is low the
optimization has nothing solid to stand on.

Pure logic, no plotting. Reads the master table via build_master.load_outputs().
Edit CONTROLLABLE / EXTRA_FEATURES to change which X go into the model.
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_master  # noqa: E402

# ---- Targets to model (master column names).
TARGETS = ["press1_kappa", "press1_viscosity"]

# ---- X the operators can actually set at the plant (optimizer will tune these).
# Add / remove a line to change the controllable set - nothing else needs editing.
CONTROLLABLE = [   # optimizer ปรับได้จริง
    "pfactor_setpoint_last_prehydrolysis",
    #"chip_weight_max_chip_filling",
    #"circulation_temp_max_heat_and_cook",
    #"digester_pressure_mean_heat_and_cook",
    "steam_to_heater_flow_mean_heat_and_cook",
    "steam_heater_temp_max_heat_and_cook",
    "alkali_accumulator1_conc_mean_hot_liquor_filling",
    "alkali_accumulator2_conc_mean_hot_liquor_filling",
    #"black_liquor_conductivity_mean_displacement",
    #"hbl_accumulator_cond_mean_hot_liquor_filling",
]
EXTRA_FEATURES = [   # ช่วยทำนาย แต่ optimizer ไม่แตะ (derived/effect)
    #"h_factor",
    "pfactor_actual_last_prehydrolysis",
    "white_liquor_m3",
    "white_liquor_per_ton_chip",
    "liquor_to_wood_ratio",
]

RANDOM_STATE = 42
TEST_SIZE = 0.25


def load_master():
    """Master table filtered to batches that passed the quality_flag == 'ok' check."""
    master, _ = build_master.load_outputs()
    if "quality_flag" in master.columns:
        master = master[master["quality_flag"] == "ok"].copy()
    return master


def feature_columns(df, include_extra=True):
    """Model feature list that actually exists and has data (drops all-NaN columns)."""
    cols = list(CONTROLLABLE) + (list(EXTRA_FEATURES) if include_extra else [])
    out = []
    for c in cols:
        if c in df.columns and df[c].notna().any():
            out.append(c)
    return out


def build_xy(df, target, include_extra=True):
    """Return (X, y) with rows that have the target and all chosen features present."""
    feats = feature_columns(df, include_extra)
    sub = df[feats + [target]].dropna()
    return sub[feats], sub[target], feats


def fit_target(df, target, include_extra=True):
    """
    Fit Linear + RandomForest for one target.
    Returns a dict with test R^2 for both models, n rows, features, and RF importance.
    """
    X, y, feats = build_xy(df, target, include_extra)
    if len(X) < 30:
        return {"target": target, "n": len(X), "features": feats, "error": "too few rows"}

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    lin = LinearRegression().fit(Xtr, ytr)
    rf = RandomForestRegressor(
        n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1
    ).fit(Xtr, ytr)

    importance = (
        pd.Series(rf.feature_importances_, index=feats)
        .sort_values(ascending=False)
    )
    return {
        "target": target,
        "n": len(X),
        "features": feats,
        "r2_linear": r2_score(yte, lin.predict(Xte)),
        "r2_rf": r2_score(yte, rf.predict(Xte)),
        "importance": importance,
        "model_linear": lin,
        "model_rf": rf,
    }


def run_gate(df=None, include_extra=True, r2_pass=0.3):
    """
    Fit every target and return a summary DataFrame + the raw results.
    r2_pass is the minimum test R^2 (RF) to call the gate 'passed' for a target.
    """
    if df is None:
        df = load_master()
    results = {t: fit_target(df, t, include_extra) for t in TARGETS}
    rows = []
    for t, r in results.items():
        if "error" in r:
            rows.append({"target": t, "n": r["n"], "r2_linear": np.nan,
                         "r2_rf": np.nan, "pass": False, "note": r["error"]})
        else:
            rows.append({"target": t, "n": r["n"],
                         "r2_linear": round(r["r2_linear"], 3),
                         "r2_rf": round(r["r2_rf"], 3),
                         "pass": r["r2_rf"] >= r2_pass, "note": ""})
    return pd.DataFrame(rows), results


if __name__ == "__main__":
    summary, _ = run_gate()
    print(summary.to_string(index=False))
