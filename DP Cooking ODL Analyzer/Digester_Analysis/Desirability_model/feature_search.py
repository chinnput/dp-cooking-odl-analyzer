"""
Feature + model search for the surrogate model (Step 0 helper).

Loops over several linear models and runs forward feature selection on k-fold
CV R^2 for each. The goal is to find the best (model, feature-set) per target
and rank them in one leaderboard, so the Step 0 gate is decided on the best
honest R^2 we can get - not a single model on a single split.

Why only linear models here: the user asked for Linear + Ridge + Lasso. They are
cheap, give interpretable coefficients, and won't inflate R^2 the way a tree can
on a small observational table. RandomForest stays in feature_select.py.

  - MODELS:  pipelines (scale + estimator) to compare.
  - forward_select: start empty, add the feature that most improves CV R^2,
    stop when the best gain is below min_gain.
  - run_search: forward-select every (model, target), return a leaderboard.

EFFECT_FEATURES are process *outcomes* (not setpoints). exclude_effect=True
(default) drops them so the reported R^2 reflects what real setpoints can predict.

Pure logic, no plotting. Reads the master via build_master.load_outputs().
Reuses CANDIDATES / EFFECT_FEATURES / load_master from feature_select.py.
"""
import os
import sys
from itertools import count

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_master  # noqa: E402

# Reuse the candidate pool, effect flags and master loader already defined.
from feature_select import (  # noqa: E402
    CANDIDATES,
    EFFECT_FEATURES,
    TARGETS,
    available_candidates,
    load_master,
)

N_SPLITS = 5
RANDOM_STATE = 42
MIN_GAIN = 0.005   # stop forward selection when the best CV R^2 gain is below this


def _models():
    """Linear models to compare. Scaled so Ridge/Lasso penalties are fair."""
    return {
        "linear": make_pipeline(StandardScaler(), LinearRegression()),
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0, random_state=RANDOM_STATE)),
        "lasso": make_pipeline(StandardScaler(), Lasso(alpha=0.01, random_state=RANDOM_STATE, max_iter=10000)),
    }


def _cv():
    return KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)


def cv_r2(df, target, feats, model):
    """Mean, std of k-fold CV R^2 for one model on the given feature set."""
    sub = df[feats + [target]].dropna()
    if len(sub) < 50 or not feats:
        return np.nan, np.nan, len(sub)
    scores = cross_val_score(model, sub[feats], sub[target], cv=_cv(), scoring="r2")
    return scores.mean(), scores.std(), len(sub)


def forward_select(df, target, pool, model, min_gain=MIN_GAIN):
    """
    Greedy forward selection on CV R^2 for one model. Add the feature that helps
    most each round; stop when the best gain is below min_gain. Returns the chosen
    set, its CV R^2 (mean/std) and the step-by-step history.
    """
    chosen, history = [], []
    remaining = list(pool)
    best = -np.inf
    best_std = np.nan
    for _ in count():
        if not remaining:
            break
        scored = []
        for f in remaining:
            m, s, _ = cv_r2(df, target, chosen + [f], model)
            scored.append((m if not np.isnan(m) else -np.inf, s, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        gain_score, gain_std, gain_feat = scored[0]
        if gain_score - best < min_gain:
            break
        best, best_std = gain_score, gain_std
        chosen.append(gain_feat)
        remaining.remove(gain_feat)
        history.append({"added": gain_feat, "cv_r2": round(best, 3),
                        "is_effect": gain_feat in EFFECT_FEATURES})
    n = len(df[chosen + [target]].dropna()) if chosen else 0
    return {"target": target, "features": chosen,
            "cv_r2": round(best, 3) if np.isfinite(best) else np.nan,
            "cv_r2_std": round(best_std, 3) if np.isfinite(best_std) else np.nan,
            "n": n, "history": history}


def run_search(df=None, exclude_effect=True, min_gain=MIN_GAIN):
    """
    Forward-select every (model, target) and return a leaderboard + raw results.

    exclude_effect=True (default): only true setpoints are considered, so the
    R^2 reflects what operators can actually control.

    Leaderboard is sorted by CV R^2 (best first). Use it to decide the Step 0
    gate and to seed CONTROLLABLE in surrogate.py.
    """
    if df is None:
        df = load_master()
    pool = available_candidates(df)
    if exclude_effect:
        pool = [c for c in pool if c not in EFFECT_FEATURES]

    models = _models()
    results, rows = {}, []
    for target in TARGETS:
        results[target] = {}
        for name, model in models.items():
            r = forward_select(df, target, pool, model, min_gain)
            results[target][name] = r
            n_eff = sum(f in EFFECT_FEATURES for f in r["features"])
            rows.append({"target": target, "model": name,
                         "cv_r2": r["cv_r2"], "cv_r2_std": r["cv_r2_std"],
                         "n_features": len(r["features"]), "n_effect": n_eff,
                         "n": r["n"]})
    leaderboard = (
        pd.DataFrame(rows)
        .sort_values(["target", "cv_r2"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return leaderboard, results


def best_per_target(results):
    """Pick the top (model, feature-set) per target from a run_search result."""
    best = {}
    for target, by_model in results.items():
        pick = max(by_model.values(),
                   key=lambda r: r["cv_r2"] if np.isfinite(r["cv_r2"]) else -np.inf)
        best[target] = pick
    return best


if __name__ == "__main__":
    for exclude in (True, False):
        leaderboard, res = run_search(exclude_effect=exclude)
        tag = "setpoint-only" if exclude else "with effect features"
        print(f"\n=== feature+model search ({tag}) ===")
        print(leaderboard.to_string(index=False))
        print("\n-- best per target --")
        for t, r in best_per_target(res).items():
            print(f"{t}: cv_r2={r['cv_r2']} ({len(r['features'])} feats) {r['features']}")
