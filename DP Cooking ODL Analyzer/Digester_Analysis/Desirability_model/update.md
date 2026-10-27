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

---

## 2026-10-27 - Per-digester vs pooled, time-split check

**What was done**
- Compared one model per digester (D1-D4) against pooled and pooled + Digester_ID,
  with `TimeSeriesSplit(4)` (out-of-time R^2), GradientBoosting depth 2 + Ridge,
  9 batch features. Also: Kappa noise ceiling from `lab_samples.csv`, per-digester
  good-vs-rest, steam tag audit. Scratchpad scripts only, no repo code changed.

**Results**
- n with Kappa: D1 111, D2 125, D3 129, D4 85.
- Kappa R^2: pooled -0.19 / -0.11 (GBM / Ridge); per digester -0.42 .. -0.10.
- Viscosity R^2: pooled 0.04 / 0.15; per digester -0.15 .. 0.23 (D4, n=85).
- Per-digester models do not help; Digester_ID adds nothing. Time split is lower than
  the random-split Step 0 numbers.
- Kappa: lag-1 autocorr 0.62, 59% variance between days, monthly mean 8.7 -> 10.5
  (Jan -> Sep). Within-digester Spearman of batch setpoints vs Kappa ~ 0.
- Viscosity: alkali_accumulator1_conc, heat_and_cook_minutes, white_liquor_m3,
  pfactor_actual all negative in every digester -> common response, pooled model fits.
- Steam flow tags unusable as-is (D1-D3 negative offset, D4 pegged at 21).
  LP_pressure now populated (1529/1540).

**Found by** AI assistant (Claude), per-digester feasibility check.

---

## 2026-10-27 - Viscosity-only surrogate

**What was done**
- Focus on Viscosity (Kappa parked). 447 batches, 7 X + Digester_ID, steam tags excluded.
- Ridge pooled / + DigID / partial pooling (feature x digester, ridge-shrunk),
  GBM depth 2 pooled, Ridge per digester. TimeSeriesSplit(4), gate R^2 >= 0.30.

**Results**
- Best = GBM pooled R^2 0.11, MAE 31.9 (baseline MAE 32.2). Gate NOT passed.
- Partial pooling 0.04 < pooled 0.07 -> no evidence of per-digester slopes. Per digester
  D1 0.01, D2 0.09, D3 -0.44, D4 0.25.
- alkali_accumulator1_conc (PM2.404AIC670, shared tag) dominates: drop-one dR^2 -0.17,
  ~ -16 Visc per g/l, quintiles 805 -> 752. P-factor > 361 and heat&cook > 35 min lower Visc.
- Alkali vs Visc rho: pooled -0.47, within-month -0.26, within-week -0.13 -> partly drift.
- Correction: AIC670 is shared by all digesters, so "same sign in all 4" is not independent
  evidence for alkali.

**Found by** AI assistant (Claude), Viscosity surrogate check.
