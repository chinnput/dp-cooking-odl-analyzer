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

---

## 2026-10-28 - Golden window with statistical evidence

**What was done**
- `golden.py` + `02_golden_window.ipynb`; config `GOLDEN_SPEC` (Kappa 8-10, Viscosity 700-800, both sides,
  confirmed by user), `GOLDEN_EXTRA` (H-factor, alkali / t chip, WL m3, chip weight, P-factor final),
  `GOLDEN_WINDOW_RULES`, permutation / bootstrap / FDR settings. Plots: `fail_curves`, `window_months`.
- Per X and fail mode: quintile fail rate (Wilson CI), best cut (chi-square), permutation p with the
  outcome shuffled inside each month (pays for the cut search + removes season), week-block bootstrap
  of the cut, Mantel-Haenszel RR/RD by month, cut from the first 70% checked on the last 30%, BH q, grade.
- Data: 654 batches with Kappa + Viscosity (2026-05-09 .. 10-18, after the pull to 03-01 .. 10-20).

**Results**
- Golden 38%. Fail modes: Kappa high 51%, Viscosity high 25%, Viscosity low 3%, Kappa low ~0.
  Golden rate by month: May 65%, Jun 71%, Jul-Sep 21-29%, Oct 46% -> strong season.
- Fail QC (any): **P-factor overshoot <= 64.3 -> grade A** (fail 78% vs 52%, RR 1.49, p_perm 0.001,
  MH RR 1.28 p<0.001, 6/6 months, later months 78% vs 62% p=0.02). Grade B: H-factor <= 333.8,
  Alkali conc 1 <= 36.17, LP pressure <= 6.565 (future check not confirmed for alkali / LP).
- Kappa high: P-factor overshoot A, LP pressure B. Viscosity high: 9 X grade B, all "under-cooked" side
  (P-factor rate <= 4.41, P-factor <= 355, P-factor final <= 425, H-factor <= 334, alkali <= 36.1,
  H&C <= 35 min, P-temp max <= 166, prehydrolysis > 70 min). Viscosity low: no X passes FDR.
- Every limit found is a LOWER limit (cook enough). No evidence for an upper limit -> stay below data P95.
- Combined window (overshoot > 64.3 and H-factor > 333.8): 46% of batches inside; fail 46% [40-52]
  vs 75% [70-79] outside, Fisher p 7e-14, MH RR 1.35, lower in 6/6 months; Kappa high 39% vs 62%,
  Viscosity high 13% vs 36%, Viscosity low 2% vs 4% (no over-cook penalty).

**Found by** AI assistant (Claude), user's golden-batch question with statistical proof.

---

## 2026-10-28 - Outlier option for the golden window (XGboost_Model only)

**What was done**
- `config.GOLDEN_OUTLIER` (None / "2sd" / "iqr3") + `GOLDEN_OUTLIER_BY_DIGESTER`; `golden.outlier_mask`,
  `clean_x` (one X at a time, other columns untouched), `outlier_report`, `sensitivity`. Applied in
  `screen`, `curve`, `window_check`. Notebook: new "Outliers of X" section after Step 0.
  Default stays None. Not done in build_master (shared by other work; cache not on this machine).
- Added scatter cell (P-factor overshoot vs Viscosity, coloured Golden / Non-Golden).

**Results**
- 2 SD on every X at once would drop 31% of batches (654 -> 454); per X it removes 10-46 values,
  mostly on the long side of skewed X. 3 IQR removes 0-40 per X.
- Sensitivity (Fail QC any): P-factor overshoot cut 64.3 / 64.7 / 64.6, fail 78/52 -> 77/51, RR 1.49-1.51,
  6/6 months in all three. H-factor cut 333.8-334.3, RR 1.44-1.47, 5/6 months. -> not driven by outliers.
- With "iqr3" for the full screen: overshoot still A, H-factor and alkali still B, **LP pressure drops
  from B to - (q 0.06)** -> LP pressure evidence depends on a few extreme values. Window 44% vs 74%, 6/6.
- Extreme overshoot (200-645) batches have long HOT LIQUOR FILLING (80-125 min vs 65): real process
  events, not sensor errors.

**Found by** AI assistant (Claude), user question on outliers / 2-sigma.
