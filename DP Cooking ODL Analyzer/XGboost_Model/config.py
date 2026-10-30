# Settings for the Viscosity model comparison (XGBoost vs the others).
# This is the ONLY file you need to edit. The other files read from here.
# Data source: ../Digester_Analysis/data/batch_master.csv (1 row = 1 batch). No PI access.

import os

# ---- Paths
HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(HERE, "..", "Digester_Analysis", "data", "batch_master.csv")
OUTPUT_DIR = os.path.join(HERE, "output")   # git-ignored, rebuilt on every run

# ===== Y =====
TARGET = "press1_viscosity"   # PULP-LINE2-VISCOSITY-PRESS1, real lab samples linked to the batch
TARGET_LABEL = "Viscosity"
TARGET_BAND = (700, 800)      # accept band, used for the PDP shading only

# ===== X =====
# 1 line = 1 feature.  "batch_master column": "short label for plots",   # PI tag
# Comment a line out to drop it. Use data.list_columns() to see every column you can add.
# A derived feature (see data.add_derived) is added the same way, by its name.
FEATURES = {
    "alkali_accumulator1_conc_mean_hot_liquor_filling": "Alkali conc 1",    # PM2.404AIC670 (shared, g/l)
    #"alkali_accumulator2_conc_mean_hot_liquor_filling": "Alkali conc 2",    # PM2.404AIC667 (shared, g/l)
    "pfactor_actual_last_prehydrolysis":                "P-factor",         # PM2.10xDkPFACTOR.CALC
    "heat_and_cook_minutes":                            "H&C minutes",      # main sequence phase length
    "white_liquor_per_ton_chip":                        "WL / t chip",      # derived: FIC532 x HLF time / chip
    "liquor_to_wood_ratio":                             "L:W",              # derived: chip weight WIk29
    "LP_pressure_mean_heat_and_cook":                   "LP pressure",      # PM2.10xPICk02:MV (bar)
    #"black_liquor_conductivity_mean_displacement":      "BL conductivity",  # PM2.104CIC551 (shared, mS/cm)
    # --- prehydrolysis speed / temperature (added 2026-10-27)
    "pfactor_rate":                                     "P-factor rate",    # derived: P-factor / PREHYDRAU minutes
    "pfactor_temp_max_prehydrolysis":                   "P-temp max",       # PM2.10xDkPFTEMP.CALC (C)
    #"mp_steam_valve_mean_prehydrolysis":                "MP valve (PH)",    # PM2.404HICk45:MV (%)
    "pfactor_temp_setpoint_last_prehydrolysis":       "P-temp SP",        # OPESPPT, no D1 tag -> drops all D1 rows
    "prehydrolysis_minutes":                          "Prehyd minutes",   # no effect on Viscosity alone
    # --- prehydrolysis.py features (2026-10-27). Strong alone, but collinear with the group above:
    #     switching them on did not raise out-of-time R^2 (Ridge 0.17-0.18 vs 0.21).
    # "pfactor_final":                                  "P-factor final",   # where the counter stops (in HLF)
     "pfactor_overshoot":                              "P-factor overshoot",  # final - setpoint
    # "minutes_above_168":                              "Min > 168C",       # P-temp >= 168 C in PREHYDRAU
    "ptemp_overshoot":                                "P-temp overshoot", # max - SP, no D1 SP tag -> drops D1
    # "steam_users_other":                              "Other steam users",  # no effect within week
    # "h_factor":                                       "H-factor",         # TI123/223/323/423
    # "alkali_charge_per_ton_chip":                     "Alkali / t chip",  # derived in data.add_derived
    # "steam_to_heater_flow_mean_heat_and_cook":        "Steam flow",       # OFF: D1-D3 zero offset, D4 pegged
}

USE_DIGESTER_ID = True   # add D2..D4 dummies (D1 = reference)

# ===== Filters =====
QUALITY_FLAG_OK = True          # keep only batches with quality_flag == "ok"
TARGET_RANGE = (400, 2000)      # Viscosity spike filter (same as the notebooks)
DATE_FROM = "2026-05-01"        # e.g. "2026-07-01"  (batch_start)
DATE_TO = "2026-10-16"

# ===== Validation =====
CV_FOLDS = 3      # TimeSeriesSplit: always train on the past, test on the future
GATE_R2 = 0.30    # a model below this is too weak to optimize on

# ===== Models =====
# Remove a name to skip that model.
MODELS = ["baseline", "ridge", "random_forest", "sklearn_gbm", "xgboost"]
RANDOM_STATE = 42

XGB_PARAMS = dict(
    max_depth=2,            # shallow: only ~450 batches
    n_estimators=300,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=10,
    reg_lambda=5.0,
)
RF_PARAMS = dict(n_estimators=300, max_depth=4, min_samples_leaf=10)
GBM_PARAMS = dict(max_depth=2, n_estimators=200, learning_rate=0.03, subsample=0.8, min_samples_leaf=15)

# ===== Explain =====
TEST_SHARE = 0.30   # last 30% in time = hold-out for permutation importance / SHAP
TOP_N_PDP = 3       # partial dependence plots for the top N features

# ===== Golden window (golden.py / 02_golden_window.ipynb) =====
# Golden = every Y inside its QC spec (confirmed by user 2026-10-28). Viscosity > 800 is a fail too.
GOLDEN_SPEC = {
    "press1_kappa": (8, 10),
    "press1_viscosity": (700, 800),
}
# X tested = FEATURES + these extra columns (cooking strength: Kappa-high is the main fail mode).
# Each X is tested on its own rows, so a column with no D1 data does not drop D1 for the others.
GOLDEN_EXTRA = {
    "h_factor":                    "H-factor",          # TI123/223/323/423, HLF + H&C + DPL
    "alkali_charge_per_ton_chip":  "Alkali / t chip",   # derived in data.add_derived (kg/t wet chip)
    "white_liquor_m3":             "WL m3",             # FIC532 x HLF time
    "chip_weight_max_chip_filling": "Chip weight",      # WIk29 (t, wet)
    "pfactor_final":               "P-factor final",    # prehydrolysis.py
}
GOLDEN_DATE_FROM = None       # None = every batch with both lab results
GOLDEN_DATE_TO = None
GOLDEN_MIN_SIDE = 0.15        # each side of a threshold keeps >= 15% of the batches (and >= 20)
GOLDEN_N_PERM = 1000          # permutations (shuffled inside each month) for the threshold p-value
GOLDEN_N_BOOT = 300           # week-block bootstrap rounds for the threshold CI
GOLDEN_FDR = 0.05             # Benjamini-Hochberg false discovery rate
# Outliers of X: None = keep all (the golden tests use ranks / cuts, so they are robust anyway),
# "2sd" = outside mean +/- 2 SD, "iqr3" = outside Q1 - 3 IQR .. Q3 + 3 IQR.
# Removed one X at a time (a batch is only dropped for that X), per digester (D4 is smaller).
GOLDEN_OUTLIER = None
GOLDEN_OUTLIER_BY_DIGESTER = True
# Combined window to test (a batch is INSIDE when it meets every rule). Edit after reading the screen.
GOLDEN_WINDOW_RULES = [
    ("pfactor_overshoot", ">", 64.3),   # grade A for Fail QC (2026-10-28 run)
    ("h_factor", ">", 333.8),           # grade B for Fail QC
]
