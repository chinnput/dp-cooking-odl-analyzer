"""
Feature selection for the surrogate model (Step 0 helper).

Loops over feature subsets to find the best predictor set per target, using
k-fold cross-validation (not a single split) so the chosen set is not just
lucky on one test fold. Two methods:

  - forward_select: start empty, add the feature that most improves CV R^2,
    stop when nothing helps.
  - rfecv_select:   sklearn RFECV, drops weak features automatically.

EFFECT_FEATURES are process *outcomes* (not setpoints). They can inflate R^2
but the optimizer cannot set them, so they are flagged in the report.

Pure logic, no plotting. Reads the master via build_master.load_outputs().
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV
from sklearn.model_selection import KFold, cross_val_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_master  # noqa: E402

TARGETS = ["press1_kappa", "press1_viscosity"]

# ---- Full candidate pool the selector may choose from (master column names).
CANDIDATES = [
    "pfactor_setpoint_last_prehydrolysis",
    "chip_weight_max_chip_filling",
    "circulation_temp_max_hot_liquor_filling",
    "circulation_temp_max_heat_and_cook",
    "circulation_temp_mean_heat_and_cook",
    "bottom_circulation_temp_mean_heat_and_cook",
    "digester_pressure_mean_heat_and_cook",
    "digester_pressure_max_prehydrolysis",
    "steam_to_heater_flow_mean_heat_and_cook",
    "steam_heater_temp_max_heat_and_cook",
    "LP_pressure_mean_heat_and_cook",
    "screen_diff_pressure_mean_heat_and_cook",
    "circulation_pump_current_mean_heat_and_cook",
    "white_liquor_dosing_flow_mean_hot_liquor_filling",
    "alkali_accumulator1_conc_mean_hot_liquor_filling",
    "alkali_accumulator2_conc_mean_hot_liquor_filling",
    "hbl_accumulator_cond_mean_hot_liquor_filling",
    "displacement_liquor_temp_mean_displacement",
    "black_liquor_conductivity_mean_displacement",
    "ventilation_temp_max_chip_filling",
    "chip_weight_max_hot_liquor_filling",
    # derived / effect (flagged, not true setpoints)
    "h_factor",
    "pfactor_actual_last_prehydrolysis",
    "white_liquor_m3",
    "white_liquor_per_ton_chip",
    "liquor_to_wood_ratio",
    "pfactor_gap",
]

# Features that are outcomes, not controllable setpoints.
EFFECT_FEATURES = {
    "h_factor",
    "pfactor_actual_last_prehydrolysis",
    "white_liquor_m3",
    "white_liquor_per_ton_chip",
    "liquor_to_wood_ratio",
    "pfactor_gap",
}

N_SPLITS = 5
RANDOM_STATE = 42


def _rf():
    return RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1)


def _cv():
    return KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)


def load_master():
    master, _ = build_master.load_outputs()
    if "quality_flag" in master.columns:
        master = master[master["quality_flag"] == "ok"].copy()
    return master


def available_candidates(df):
    """Candidates that exist and are not all-NaN, de-duplicated, order kept."""
    out = []
    for c in CANDIDATES:
        if c in out:
            continue
        if c in df.columns and df[c].notna().any():
            out.append(c)
    return out


def cv_r2(df, target, feats):
    """Mean, std of k-fold CV R^2 for a RandomForest on the given feature set."""
    sub = df[feats + [target]].dropna()
    if len(sub) < 50 or not feats:
        return np.nan, np.nan, len(sub)
    scores = cross_val_score(_rf(), sub[feats], sub[target], cv=_cv(), scoring="r2")
    return scores.mean(), scores.std(), len(sub)


def forward_select(df, target, pool, min_gain=0.005):
    """
    Greedy forward selection on CV R^2. Add the feature that helps most each
    round; stop when the best gain is below min_gain. Returns dict with the
    chosen set and its CV R^2 history.
    """
    chosen, history = [], []
    remaining = list(pool)
    best = -np.inf
    while remaining:
        scored = []
        for f in remaining:
            m, _, _ = cv_r2(df, target, chosen + [f])
            scored.append((m if not np.isnan(m) else -np.inf, f))
        scored.sort(reverse=True)
        gain_score, gain_feat = scored[0]
        if gain_score - best < min_gain:
            break
        best = gain_score
        chosen.append(gain_feat)
        remaining.remove(gain_feat)
        history.append({"added": gain_feat, "cv_r2": round(best, 3),
                        "is_effect": gain_feat in EFFECT_FEATURES})
    return {"target": target, "features": chosen, "cv_r2": round(best, 3),
            "history": history}


def rfecv_select(df, target, pool):
    """sklearn RFECV: drop weak features automatically, keep the best subset."""
    sub = df[pool + [target]].dropna()
    if len(sub) < 50:
        return {"target": target, "features": [], "cv_r2": np.nan, "n": len(sub)}
    sel = RFECV(_rf(), step=1, cv=_cv(), scoring="r2", min_features_to_select=1)
    sel.fit(sub[pool], sub[target])
    feats = [f for f, keep in zip(pool, sel.support_) if keep]
    m, s, n = cv_r2(df, target, feats)
    return {"target": target, "features": feats, "cv_r2": round(m, 3),
            "cv_r2_std": round(s, 3), "n": n}


def run_all(df=None, method="forward", exclude_effect=False):
    """
    Run the selector for every target.
    method: "forward" or "rfecv".
    exclude_effect: True -> only consider true setpoints (drop EFFECT_FEATURES).
    Returns a summary DataFrame + the raw results dict.
    """
    if df is None:
        df = load_master()
    pool = available_candidates(df)
    if exclude_effect:
        pool = [c for c in pool if c not in EFFECT_FEATURES]

    results, rows = {}, []
    for t in TARGETS:
        r = forward_select(df, t, pool) if method == "forward" else rfecv_select(df, t, pool)
        results[t] = r
        n_eff = sum(f in EFFECT_FEATURES for f in r["features"])
        rows.append({"target": t, "method": method, "cv_r2": r["cv_r2"],
                     "n_features": len(r["features"]), "n_effect": n_eff})
    return pd.DataFrame(rows), results


if __name__ == "__main__":
    for m in ("forward", "rfecv"):
        summary, _ = run_all(method=m)
        print(f"\n=== method = {m} ===")
        print(summary.to_string(index=False))
