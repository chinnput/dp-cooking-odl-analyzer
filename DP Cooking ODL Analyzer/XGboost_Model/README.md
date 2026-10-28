# XGboost_Model — Viscosity model comparison

Compares XGBoost against simpler models on the same batches and the same time split,
then shows which process X drive Press 1 **Viscosity** and whether the models agree.

Read-only: uses `../Digester_Analysis/data/batch_master.csv`. **No PI access.**

## Files

| File | What it does | Edit? |
|---|---|---|
| `config.py` | Y, X list (tags), filters, models, parameters | **Yes — the only file to edit** |
| `data.py` | Load master → filter → X / y, coverage table, derived features | Only for a new derived feature |
| `models.py` | Model zoo + `TimeSeriesSplit` → leaderboard, per-digester check | No |
| `explain.py` | Feature-effect table (Ridge, permutation, SHAP, drop-one), binned means | No |
| `plots.py` | Leaderboard, SHAP, PDP, actual vs predicted → `output/*.png` | No |
| `01_compare.ipynb` | Runs everything, shows tables and charts | No |
| `golden.py` | Golden window: fail rate vs X, threshold + permutation p, month-adjusted (Mantel-Haenszel), future check, FDR, window | No |
| `02_golden_window.ipynb` | Runs the golden window screen, charts and combined window check | No |
| `update.md` | Dated log of each run | After each run |
| `output/` | Charts (git-ignored, rebuilt every run) | — |

Flow: `batch_master.csv` → `data.py` → `models.py` → `explain.py` / `plots.py` → notebook.

## How to add a tag

**A. The column is already in `batch_master.csv`** (≈75 columns)

1. Find the name: in the notebook run `data.list_columns("alkali")` (text filter is optional).
2. Add one line to `FEATURES` in `config.py`:
   ```python
   "black_liquor_conductivity_mean_displacement": "BL conductivity",   # PM2.104CIC551
   ```
3. Restart & Run All. A wrong or empty column is skipped with a WARNING, it does not crash.

**B. A PI tag that has never been pulled**

1. Add the tag to `../Digester_Analysis/config.py` (tag group + a `BATCH_FEATURES` line).
2. The PI pull is done by the user (`Digester_Analysis/pull_data.py`).
3. Rebuild the master with `../Digester_Analysis/01_build_master.ipynb`.
4. Then step A.

**C. A derived feature** (computed from other columns)

1. Add one line in `data.add_derived()`, e.g. the existing `alkali_charge_per_ton_chip`.
2. Add its name to `FEATURES`. Once it is stable, move it into `Digester_Analysis/build_master.py`.

To drop a feature, comment its line out in `FEATURES`.

## Golden window (`02_golden_window.ipynb`)

Question: *if X is at this value, is a batch more likely to fail QC — enough to justify controlling X?*

- Golden = every Y inside `GOLDEN_SPEC` (Kappa 8–10, Viscosity 700–800). Fail modes are tested separately
  (Kappa high, Viscosity high, Viscosity low) because one X can push two Y.
- X tested = `FEATURES` + `GOLDEN_EXTRA`, each on its own rows (a tag with no D1 data does not drop D1 for the others).
- Evidence per X: fail rate per quintile → best cut with a **permutation p shuffled inside each month** →
  **Mantel-Haenszel by month** → cut from early months checked on **later months** → **Benjamini-Hochberg**.
  Grade A / B / C / –.
- Combined window to test: `GOLDEN_WINDOW_RULES` (edit after reading the screen).
- Settings: `GOLDEN_MIN_SIDE`, `GOLDEN_N_PERM`, `GOLDEN_N_BOOT`, `GOLDEN_FDR`, `GOLDEN_DATE_FROM/TO`.
- Outliers of X: `GOLDEN_OUTLIER` = `None` (default) / `"2sd"` / `"iqr3"`, removed one X at a time and per digester
  (`GOLDEN_OUTLIER_BY_DIGESTER`). The notebook shows how many each method removes and a sensitivity table.
  Sensor-validity limits (physically impossible values) belong in `Digester_Analysis` later, not here.

## Reading the output

- **Gate:** out-of-time R² ≥ `GATE_R2` (0.30). Below it, do not optimize — treat the feature table as hypotheses.
- **baseline** predicts the train mean; it is below 0 when Viscosity drifts over time. A model is useful only if it beats baseline clearly.
- **Feature effects:** trust a driver when the sign and the rank agree across columns *and* the binned-means table shows the same shape as the PDP.
- N = batches with a real lab result (≈1 sample per batch), not interpolated points.

## Environment

System Python 3.13 with `xgboost` 3.4, `shap` 0.54, `scikit-learn`, `pandas`, `matplotlib`.
