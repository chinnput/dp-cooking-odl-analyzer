# Desirability model - update log

Dated log for this folder only. Roll up big changes into the main `summaryUpdate.md`.

---

## 2026-10-27 - Folder created, Step 0 gate run

**What was done**
- Created `Desirability_model/` with `desirability.py`, `surrogate.py`,
  `00_model_check.ipynb`, and the summary/workflow/update docs.
- `desirability.py`: Derringer-Suich d_i (nominal-is-best / larger-is-better) +
  weighted geometric-mean D. Targets: Kappa 9.2 (w=1), Viscosity 750 (w=2).
- `surrogate.py`: Linear + RandomForest per target, test R^2 + feature importance.
  Controllable X in an editable `CONTROLLABLE` list.
- Ran the Step 0 gate on `batch_master.csv` (quality_flag == ok).

**Results**
- Verified desirability: Kappa 9.2 -> 1.0, Viscosity 750 -> 1.0, D=0 when any target
  leaves its band (one-bad-sinks works, Viscosity weighted higher).
- **Gate FAILED:**
  - Kappa: R^2 RF = -0.13, Linear = 0.05 (n=450).
  - Viscosity: R^2 RF = 0.17, Linear = 0.20 (n=447).
- Decision: do not build `01_optimize.ipynb` / run the optimizer yet. The surrogate
  is too weak - setpoints from it would be unreliable. Improve features/confounders first.

**Found by** AI assistant (Copilot), setpoint-optimization setup.

---

## 2026-10-27 - Feature + model search (best R^2 loop)

**What was done**
- Added `feature_search.py`: loops over Linear / Ridge / Lasso (scaled pipelines) with
  forward feature selection on 5-fold CV R^2, per target. Returns a leaderboard
  (best CV R^2 first) + `best_per_target`. Reuses CANDIDATES / EFFECT_FEATURES /
  load_master from `feature_select.py`. `exclude_effect=True` = setpoint-only.
- Added `01_feature_search.ipynb`: runs the search, shows the leaderboard, the best
  feature set per target, and a CV R^2 bar chart with the ~0.3 gate line.

**Results** (quality_flag == ok, setpoint-only)
- Kappa:     best CV R^2 = 0.046 +/- 0.044 (n=365, 4 feats) - all 3 models tie.
- Viscosity: best CV R^2 = 0.204 +/- 0.062 (n=447, 2 feats: alkali_accumulator1_conc,
  pfactor_setpoint). With effect features Viscosity rises to 0.247 (adds h_factor, white_liquor_m3).
- Still below the ~0.3 gate -> consistent with Step 0. Do not optimize yet.

**Found by** AI assistant (Copilot), feature+model search.
