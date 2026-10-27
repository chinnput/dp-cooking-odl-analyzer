# XGboost_Model - update log

Dated log for this folder only. Roll up big changes into the main `summaryUpdate.md`.

---

## 2026-10-27 - Folder created, first run (Viscosity)

**What was done**
- Created `config.py` (single edit point: `FEATURES` = column -> label, one line each),
  `data.py`, `models.py`, `explain.py`, `plots.py`, `01_compare.ipynb`, `README.md`.
- Installed `xgboost` 3.4.1 and `shap` 0.54.1 into system Python 3.13 (approved by user).
- First run on 447 batches (2026-07-01 .. 2026-10-09), 7 process features + D2..D4.
  Notebook logic verified by running the same calls as a script (no nbconvert installed).

**Results**
- Leaderboard (out-of-time R^2 / MAE): xgboost pooled 0.111 / 31.6, sklearn_gbm 0.109 / 32.0,
  ridge 0.074 / 32.8, random_forest 0.046 / 32.7, baseline -0.105 / 36.6. Gate 0.30 NOT passed.
  Digester_ID does not help any model.
- Per digester (xgboost): D1 -0.00, D2 -0.00, D3 0.01, D4 0.11 -> pooled wins.
- Feature effects rank: 1 Alkali conc 1 (all four importance measures agree, -16 Visc per g/l,
  drop-one -0.079), 2 P-factor (high SHAP / permutation but drop-one +0.028 -> unstable over time),
  3 H&C minutes, 4 WL / t chip. LP pressure, Alkali conc 2, L:W, digester dummies ~ 0.
- Binned means match the PDP: Alkali conc 1 <= 36.0 g/l -> ~805, > 37.3 -> ~752.

**Found by** AI assistant (Claude), XGBoost model comparison set-up.

---

## 2026-10-27 - Prehydrolysis speed and P-temp added

**What was done**
- Added to `Digester_Analysis` (option ก): `BATCH_FEATURES` PREHYDRAU `pfactor_temp` max/mean,
  `pfactor_temp_setpoint` last, `mp_steam_valve` / `lp_steam_valve` mean; derived `pfactor_rate`
  (P-factor / PREHYDRAU minutes) in `build_master.py`. Rebuilt master from the local cache
  (`lab_samples.csv`, refresh=False, no PI): 76 -> 82 columns, all old columns identical.
- `config.FEATURES` += `pfactor_rate`, `pfactor_temp_max_prehydrolysis`, `mp_steam_valve_mean_prehydrolysis`
  (P-temp SP left commented: no D1 tag, would drop all D1 rows).

**Results**
- Leaderboard: **ridge pooled 0.213 / MAE 29.4** (best so far), xgboost 0.121 / 31.2, gbm 0.112,
  rf 0.075, baseline -0.105. Gate 0.30 still not passed. Linear beats trees -> effect is ~linear,
  data too small for XGBoost to gain.
- MP valve % vs prehydrolysis minutes: -0.42 .. -0.63 in all 4 digesters (less steam -> longer).
- Prehydrolysis minutes alone: no effect on Viscosity (quintiles 784-793).
- P-factor rate: within-week rho -0.20 (survives season control); P-factor amount within-week -0.01.
- Collinear group (rate / P-temp max / MP valve, rho up to 0.78) shares importance, so each one
  ranks low alone in the XGBoost table although the group lifts Ridge R^2 0.07 -> 0.21.

**Found by** AI assistant (Claude), user question "low flow = slow cook vs high flow = fast cook".

---

## 2026-10-27 - Prehydrolysis detail: P-factor final, hot time, steam sharing

**What was done**
- New `Digester_Analysis/prehydrolysis.py` (+ `config.PH_TEMP_THRESHOLDS`, `config.STEAM_PHASES`), hooked
  into `build_master.py`: `pfactor_final`, `pfactor_overshoot`, `ptemp_overshoot`, `minutes_above_165/168`,
  `steam_users_other`. Master rebuilt from cache (82 -> 88 columns, old columns identical, no PI).
- Tested each vs Viscosity / Kappa (pooled, within-digester, within-week) and as extra model features.

**Results**
- P-factor does reach the setpoint (user was right); the negative `pfactor_gap` is 5-min sampling.
  But the counter keeps rising in HOT LIQUOR FILLING: final = setpoint + 67 median (P10 43, P90 100).
  Overshoot follows P-temp max (rho +0.70).
- Within-week rho vs Viscosity: pfactor_final -0.26 (strongest single X so far), overshoot -0.23,
  minutes>165 -0.17, minutes>168 -0.15, ptemp_overshoot -0.11, steam_users_other +0.03 (no effect).
  Kappa ~0 for all of them.
- Bins: P-factor final > 469 -> 755 vs ~800; > 20 min above 168 C -> 755 vs 793 at 0 min.
- Steam sharing makes PREHYDRAU longer (rho +0.44) but not faster/slower in P-factor rate (-0.03).
- Model: adding them does NOT raise out-of-time R^2 (Ridge 0.17-0.18 vs 0.213) - collinear with
  pfactor_rate / P-temp max. Kept commented in config.FEATURES.

**Found by** AI assistant (Claude), A1/A2/A4 + user's P-factor-setpoint question.
