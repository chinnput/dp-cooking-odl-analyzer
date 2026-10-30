# Settings for the batch digester analysis.
# Edit this file to change WHAT to pull. The code in the other files stays the same.
# Tag source: ../batch_digester_tags_per_digester.csv (verify before use)

import os

# ---- Time range for the pull
START_TIME = "2026-03-01 00:00:00"
END_TIME = "2026-10-20 00:00:00"
INTERVAL = "5m"        # temperature ramps fast, needed for H-factor
CHUNK_DAYS = 7         # pull one week per request

# ---- MI Cube API
MI_CUBE_API_URL = "https://micube.scg.com/v2/api/Datacenter/PIServer/InterpolatedValue/MultiTag/"
PI_SERVER = "VPKGDRBPPI01"
# Token is read from the .env file in the project root (MI_CUBE_API_TOKEN)

# ---- Where pulled data is saved: always the "data" folder next to this file
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# =====================================================================
# TAGS BY CATEGORY
# Per-digester groups: {name: {digester: PI tag}} -> columns "D1_name", "D2_name", ...
# Shared groups:       {name: PI tag}             -> column "name"
# =====================================================================

# ===== 1. BATCH ID, SEQUENCE & DOWNSTREAM STATUS =====
BATCH_STATUS = {
    "batch_number":  {1: "PM2.104D1COOKNO.CALC", 2: "PM2.104D2COOKNO.CALC",
                      3: "PM2.104D3COOKNO.CALC", 4: "PM2.404D4COOKNO.CALC"},
    "main_sequence": {1: "PM2.104DIG1MAINSEQ", 2: "PM2.104DIG2MAINSEQ",        # phase (text)
                      3: "PM2.104DIG3MAINSEQ", 4: "PM2.404DIG4MAINSEQ"},
    # Pulp of digester k at Press 1: value k or 0 (use status == k exactly)
    "press1_status": {1: "PPPC_DP_Cooking.B1_Discharge_FinalTime_Press1_Status",
                      2: "PPPC_DP_Cooking.B2_Discharge_FinalTime_Press1_Status",
                      3: "PPPC_DP_Cooking.B3_Discharge_FinalTime_Press1_Status",
                      4: "PPPC_DP_Cooking.B4_Discharge_FinalTime_Press1_Status"},
}

# ===== 2. PHASE TIMERS (MINUTES) =====
# PI unit shows "No." - values behave like minutes elapsed in the phase
PHASE_TIMERS = {
    "chip_filling_time":       {1: "PM2.104DIG1CHF_T", 2: "PM2.104DIG2CHF_T",
                                3: "PM2.104DIG3CHF_T", 4: "PM2.404DIG4CHF_T"},
    "prehydrolysis_time":      {1: "PM2.104DIG1PHP_T", 2: "PM2.104DIG2PHP_T",
                                3: "PM2.104DIG3PHP_T", 4: "PM2.404DIG4PHP_T"},
    "hot_liquor_filling_time": {1: "PM2.104DIG1HLF_T", 2: "PM2.104DIG2HLF_T",
                                3: "PM2.104DIG3HLF_T", 4: "PM2.404DIG4HLF_T"},
    "heat_and_cook_time":      {1: "PM2.104DIG1HAC_T", 2: "PM2.104DIG2HAC_T",
                                3: "PM2.104DIG3HAC_T", 4: "PM2.404DIG4HAC_T"},
    "displacement_time":       {1: "PM2.104DIG1DPL_T", 2: "PM2.104DIG2DPL_T",
                                3: "PM2.104DIG3DPL_T", 4: "PM2.404DIG4DPL_T"},
    "discharge_time":          {1: "PM2.104DIG1DCH_T", 2: "PM2.104DIG2DCH_T",
                                3: "PM2.104DIG3DCH_T", 4: "PM2.404DIG4DCH_T"},
}

# ===== 3. TEMPERATURE, STEAM, PRESSURE & P-FACTOR =====
COOKING = {
    "circulation_temp":         {1: "PM2.104TI123", 2: "PM2.104TI223",          # used for H-factor
                                 3: "PM2.104TI323", 4: "PM2.404TI423"},         # D4: TO VERIFY (PI says "Bottom Circ.")
    "bottom_circulation_temp":  {1: "PM2.104TI118", 2: "PM2.104TI218",
                                 3: "PM2.104TI318", 4: "PM2.404TI418"},
    "steam_to_heater_flow":     {1: "PM2.104FI137", 2: "PM2.104FI237",          # t/h
                                 3: "PM2.104FI337", 4: "PM2.404FI437"},         # D4: TO VERIFY ("Steam H. 404.044")
    "digester_pressure":        {1: "PM2.104PIC104:MV", 2: "PM2.104PIC204:MV",  # bar
                                 3: "PM2.104PIC304:MV", 4: "PM2.404PIC404:MV"},
    "pfactor_actual":           {1: "PM2.104D1PFACTOR.CALC", 2: "PM2.104D2PFACTOR.CALC",
                                 3: "PM2.104D3PFACTOR.CALC", 4: "PM2.404D4PFACTOR.CALC"},
    "pfactor_setpoint":         {1: "PM2.104D1OPESPPF.CALC", 2: "PM2.104D2OPESPPF.CALC",
                                 3: "PM2.104D3OPESPPF.CALC", 4: "PM2.404D4OPESPPF.CALC"},
    "pfactor_temp":             {1: "PM2.104D1PFTEMP.CALC", 2: "PM2.104D2PFTEMP.CALC",   # C, P-factor temperature
                                 3: "PM2.104D3PFTEMP.CALC", 4: "PM2.404D4PFTEMP.CALC"},
    "pfactor_temp_setpoint":    {2: "PM2.104D2OPESPPT.CALC", 3: "PM2.104D3OPESPPT.CALC",  # C (no D1 tag)
                                 4: "PM2.404D4OPESPPT.CALC"},
    "displacement_liquor_temp": {1: "PM2.104TIS114", 2: "PM2.104TIS214",
                                 3: "PM2.104TIS314", 4: "PM2.404TIS414"},
    "steam_heater_temp":        {1: "PM2.104TIC120:MV", 2: "PM2.104TIC220:MV",   # C, steam heater
                                 3: "PM2.104TIC320:MV", 4: "PM2.404TIC420:MV"},
    "lp_steam_valve":           {1: "PM2.404HIC144:MV", 2: "PM2.404HIC244:MV",   # %, LP steam valve
                                 3: "PM2.404HIC344:MV", 4: "PM2.404HIC444:MV"},
    "mp_steam_valve":           {1: "PM2.404HIC145:MV", 2: "PM2.404HIC245:MV",   # %, MP steam valve
                                 3: "PM2.404HIC345:MV", 4: "PM2.404HIC445:MV"},
    "LP_pressure":              {1: "PM2.104PIC102:MV", 2: "PM2.104PIC202:MV",   # bar, LP pressure (PIC102)
                                 3: "PM2.104PIC302:MV", 4: "PM2.404PIC402:MV"},
}

# ===== 4. RAW MATERIAL & CHEMICAL CHARGE =====
RAW_MATERIAL = {
    "chip_weight": {1: "PM2.104WI129", 2: "PM2.104WI229",               # ton
                    3: "PM2.104WI329", 4: "PM2.404WI429"},
}
CHEMICAL_SHARED = {
    "white_liquor_flow": "PM2.104FIC620:MV",          # m3/h
    "white_liquor_dosing_flow": "PM2.104FIC532:MV",   # m3/h
    "alkali_accumulator1_conc": "PM2.404AIC670:MV",   # g/l - EA or AA? to confirm
    "alkali_accumulator2_conc": "PM2.404AIC667:MV",   # g/l
}

# ===== 5. EQUIPMENT HEALTH & STRAINER =====
EQUIPMENT = {
    "screen_diff_pressure":     {1: "PM2.104PDI105", 2: "PM2.104PDI205",   # bar, no D4 tag
                                 3: "PM2.104PDI305"},
    "circulation_pump_current": {1: "PM2.104M561", 2: "PM2.104M562",       # A
                                 3: "PM2.104M563", 4: "PM2.404M564"},
}

# ===== 6. AIR EVACUATION & PRE-STEAMING =====
AIR_EVACUATION = {
    "ventilation_temp": {1: "PM2.104TI125", 2: "PM2.104TI225",           # C
                         3: "PM2.104TI325", 4: "PM2.404TI425"},
    "evacuation_valve": {1: "PM2.104HS126", 2: "PM2.104HS226",           # digital (text)
                         3: "PM2.104HS326", 4: "PM2.404HS426"},
}
AIR_EVACUATION_SHARED = {
    "evacuation_fan_current": "PM2.104M539",   # A
}

# ===== 7. SHARED HEADERS & DOWNSTREAM BUFFER =====
HEADERS_SHARED = {
    "discharge_tank_level": "PM2.104LIA701",       # %
    "MP_steam_header_flow": "PM2.104FIC508:MV",    # t/h
    "MP_steam_header_pressure": "PM2.104PI534",    # bar
    "LP_steam_header_flow": "PM2.104FIQ507",       # t/h
    "LP_steam_header_pressure": "PM2.104PI535",    # bar
}

# ===== 8. EXTRA CHEMICAL (optional) =====
EXTRA_CHEMICAL_SHARED = {
    "white_liquor_to_displacement_flow": "PM2.104FIC550:MV",   # m3/h
    "black_liquor_conductivity": "PM2.104CIC551:MV",           # mS/cm, residual alkali proxy
    "cooking_aid_flow": "PM2.104FI638",                        # L/h
}

# ===== 10. EXTRA ALKALI, CONDUCTIVITY, HEAT EXCHANGER, MOISTURE (from workflow.md focus) =====
# Added to cover the "alkaline, steam, heat exchanger" focus in workflow.md. Verify meaning before use.
ALKALI_SHARED = {
    "dig4_alkali_conc": "PM2.404AI446",            # g/l, DIG.4 alkali
    "bl_conductivity_acc": "PM2.104AIC664:MV",     # mS, B.L. cond (accumulator)
    "hbl_accumulator_cond": "PM2.104CIC660:MV",    # mS/cm, HBL accumulator cond
}
HEAT_EXCHANGER_SHARED = {
    "heat_exchanger_in_temp": "PM2.104TI611A",     # C, heat exchanger WL/BL inlet
    "heat_exchanger_temp": "PM2.104TI611",         # C, heat exchanger WL/BL
    "heat_exchanger_wl_temp": "PM2.104TIC614:MV",  # C, heat exchanger WL/steam
    "heat_exchanger_bl_temp": "PM2.104TIC642:MV",  # C, heat exchanger BL/steam
}
MOISTURE_SHARED = {
    "chip_moisture": "PM2.404MI801",               # %, chip moisture (reported stuck at 35 - verify)
}

# ===== 9. LAB QUALITY AT PRESS 1 (Y) =====
# NOT pulled from PI - the lab values come from the log book Excel files (logbook.py).
# Reason: PI interpolates between samples (Step = 0), so the real sample times are lost.
# The PI tag names are kept here for reference only.
LAB_TAGS = {
    "press1_kappa": "PULP-LINE2-KAPPA-PRESS1",
    "press1_viscosity": "PULP-LINE2-VISCOSITY-PRESS1",
    "press1_brightness": "PULP-LINE2-BRIGHTNESS-PRESS1",
}

# ---- Log book Excel files (read only) - the source of the REAL lab sample times (logbook.py)
# Folder with the monthly files, e.g. "10. LINE NO.2_Log Sheet_ in Oct 2026.xlsx" (one sheet per day "1".."31").
# Default = the copy that onedrive_to_pi downloads; point it anywhere else if you keep your own copy.
LOG_BOOK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "onedrive_to_pi",
                            "OneDrive_2026-08-26", "Log book Pulp Line 2 - 2026")
LOG_BOOK_FIRST_ROW = 7      # Excel row where the hourly data starts
LOG_BOOK_LAST_ROW = 30      # last Excel row to read
LOG_BOOK_TIME_COLUMN = 1    # column B (0 = A)
LOG_BOOK_LAB_COLUMNS = {    # name used here -> column (0 = A)
    "press1_kappa": 5,       # column F
    "press1_viscosity": 8,   # column I
    "press1_brightness": 15, # column P
}
LOG_BOOK_DAY_STARTS_HOUR = 8   # a sheet runs 08:00 -> 07:00 next day: times before 08:00 belong to the next date

# ---- Lab tables (lab.py): sensor values at real lab sample times
LAB_INTERVAL = "1h"   # times to check: 10:00, 11:00, ... A time is skipped when the lab has no value.
                      # The pulled data (INTERVAL) must contain these times, e.g. 5m data has every hour.
LAB_VALID_RANGE = {   # values outside these ranges are typos/spikes -> treated as blank
    "press1_kappa": (5, 15),
    "press1_viscosity": (400, 1300),
    "press1_brightness": (25, 50),
}
LAB_SOP_LIMITS = {    # (low, high) - same as Lab_Analysis notebook, NOT yet confirmed by the process team
    "press1_kappa": (7.5, 8.5),
    "press1_viscosity": (680, 710),
    "press1_brightness": (37, 40),
}

# Target band (low, high) for the "good" quality zone -> grade column (low / good / high).
# lab column -> short name used for the grade column (e.g. press1_kappa -> kappa_grade).
QUALITY_TARGETS = {
    "press1_kappa": (8, 10),
    "press1_viscosity": (700, 800),
}
QUALITY_GRADE_NAMES = {"press1_kappa": "kappa", "press1_viscosity": "viscosity"}

# ---- All categories (name -> group). Used by tag_to_name() and columns_in().
PER_DIGESTER_CATEGORIES = {
    "batch_status": BATCH_STATUS,
    "phase_timer": PHASE_TIMERS,
    "cooking": COOKING,
    "raw_material": RAW_MATERIAL,
    "equipment": EQUIPMENT,
    "air_evacuation": AIR_EVACUATION,
}
SHARED_CATEGORIES = {
    "chemical": CHEMICAL_SHARED,
    "air_evacuation_shared": AIR_EVACUATION_SHARED,
    "headers": HEADERS_SHARED,
    "extra_chemical": EXTRA_CHEMICAL_SHARED,
    "alkali": ALKALI_SHARED,
    "heat_exchanger": HEAT_EXCHANGER_SHARED,
    "moisture": MOISTURE_SHARED,
    # LAB_TAGS is left out on purpose: lab values come from the log book, not PI
}

# Tags that hold text states, not numbers (kept as text when pulled)
TEXT_NAMES = ["main_sequence", "evacuation_valve"]

# =====================================================================
# BATCH SETTINGS (used by build_master.py)
# =====================================================================

# Phase text in the DCS main sequence -> short name used in column names (cooking order).
# Any other text (e.g. "8", "0" = PI system states) is treated as an unknown phase.
PHASE_NAMES = {
    "CHIP FILLING": "chip_filling",
    "PREHYDRAU": "prehydrolysis",
    "HOT LIQUOR FILLING": "hot_liquor_filling",
    "HEAT&COOK": "heat_and_cook",
    "DISPLACEMENT": "displacement",
    "DISCHARGE": "discharge",
    "WAIT": "wait",
}
PHASES = list(PHASE_NAMES)

# H-factor = cooking in these phases.
# Checked on Aug-Sep 2026 data: the liquor is already 130-165 C during HOT LIQUOR FILLING and
# still ~157 C during most of DISPLACEMENT, so HEAT&COOK alone misses 40-70% of the cook.
# The H-factor of every single phase is also kept (h_<phase> columns) for comparison.
H_FACTOR_PHASES = ["HOT LIQUOR FILLING", "HEAT&COOK", "DISPLACEMENT"]

# Per-batch features: (sensor name in this config, phase(s) to look at, statistic)
# statistic: "max", "min", "mean" or "last" (last valid value in the phase)
# Column name = <sensor>_<statistic>_<phase short name>, e.g. chip_weight_max_chip_filling
# Shared tags (no digester number) are read only while THIS digester is in the phase.
BATCH_FEATURES = [
    # Step 1 - chips in
    ("chip_weight",               ["CHIP FILLING"],       "max"),   # chips loaded (wet, ton)
    ("ventilation_temp",          ["CHIP FILLING"],       "max"),
    # Step 2 - prehydrolysis
    ("pfactor_actual",            ["PREHYDRAU"],          "last"),  # P-factor reached
    ("pfactor_setpoint",          ["PREHYDRAU"],          "last"),
    ("digester_pressure",         ["PREHYDRAU"],          "max"),
    ("steam_to_heater_flow",      ["PREHYDRAU"],          "mean"),
    ("pfactor_temp",              ["PREHYDRAU"],          "max"),   # how hot the prehydrolysis ran
    ("pfactor_temp",              ["PREHYDRAU"],          "mean"),
    ("pfactor_temp_setpoint",     ["PREHYDRAU"],          "last"),  # no D1 tag
    ("mp_steam_valve",            ["PREHYDRAU"],          "mean"),  # % open, steam proxy (flow tag unreliable)
    ("lp_steam_valve",            ["PREHYDRAU"],          "mean"),
    # Liquor in
    ("chip_weight",               ["HOT LIQUOR FILLING"], "max"),   # chips + liquor (for L:W ratio)
    ("circulation_temp",          ["HOT LIQUOR FILLING"], "max"),
    ("white_liquor_dosing_flow",  ["HOT LIQUOR FILLING"], "mean"),  # shared tag
    ("alkali_accumulator1_conc",  ["HOT LIQUOR FILLING"], "mean"),  # shared tag g/l
    ("alkali_accumulator2_conc",  ["HOT LIQUOR FILLING"], "mean"),  # shared tag
    ("hbl_accumulator_cond",      ["HOT LIQUOR FILLING"],       "mean"),  # shared tag
    # Step 3 - heat and cook
    ("circulation_temp",          ["HEAT&COOK"],          "max"),
    ("circulation_temp",          ["HEAT&COOK"],          "mean"),
    ("bottom_circulation_temp",   ["HEAT&COOK"],          "mean"),
    ("digester_pressure",         ["HEAT&COOK"],          "mean"),
    ("steam_to_heater_flow",      ["HEAT&COOK"],          "mean"),
    ("LP_pressure",               ["HEAT&COOK"],          "mean"),
    ("steam_heater_temp",         ["HEAT&COOK"],          "max"),   # D4 tag differs (TIC420) - compare per digester
    ("screen_diff_pressure",      ["HEAT&COOK"],          "mean"),  # no D4 tag
    ("circulation_pump_current",  ["HEAT&COOK"],          "mean"),
    # Step 4 - displacement
    ("displacement_liquor_temp",  ["DISPLACEMENT"],       "mean"),
    ("black_liquor_conductivity", ["DISPLACEMENT"],       "mean"),  # shared tag
    
]

# Prehydrolysis features (prehydrolysis.py)
PH_TEMP_THRESHOLDS = [165, 168]               # minutes_above_<T>: time in PREHYDRAU with P-temp >= T C
STEAM_PHASES = ["PREHYDRAU", "HEAT&COOK"]     # phases that draw MP steam (for steam_users_other)

# Quality flag: a batch longer than this (hours) probably includes a stop
LONG_BATCH_HOURS = 12

# Output files written by 01_build_master.ipynb into DATA_DIR
BATCH_MASTER_FILE = "batch_master.csv"   # 1 row = 1 batch
LAB_LINKED_FILE = "lab_linked.csv"       # 1 row = 1 real lab sample, with its digester and batch
PHASE_SUMMARY_FILE = "phase_summary.csv" # 1 row = 1 phase run, with mean/min/max of every sensor
PHASE_SUMMARY_LAB_FILE = "phase_summary_with_lab.csv" # phase_summary + the batch's Press 1 lab values

# Phase summary (batch.phase_summary): statistics taken for every numeric sensor in each phase run
PHASE_SUMMARY_STATS = ["mean", "min", "max"]
# Batch lab columns (from lab.lab_per_batch) added to phase_summary_with_lab.csv.
# Same value for every phase run of a batch (lab belongs to the whole batch); blank when the batch has no sample.
PHASE_SUMMARY_LAB_FIELDS = [c for col in LOG_BOOK_LAB_COLUMNS
                           for c in (col, f"{col}_samples")]
# Sensors whose mean/min/max is meaningless in a phase window, so they are left out:
#   batch_number  - an id (already a column of its own)
#   press1_status - digester-at-Press1 state (0-4), not a measurement
#   *_time        - the phase step timer (cumulative minutes, use *_minutes instead)
PHASE_SUMMARY_SKIP = ["batch_number", "press1_status"] + list(PHASE_TIMERS.keys())


def data_name():
    """Name of the pulled data file for the current START_TIME / END_TIME."""
    return f"digester_{START_TIME[:10]}_{END_TIME[:10]}"


def tag_to_name():
    """Return {PI tag: column name}, e.g. {'PM2.104TI123': 'D1_circulation_temp'}."""
    names = {}
    for group in PER_DIGESTER_CATEGORIES.values():
        for name, per_dig in group.items():
            for dig, tag in per_dig.items():
                names[tag] = f"D{dig}_{name}"
    for group in SHARED_CATEGORIES.values():
        for name, tag in group.items():
            names[tag] = name
    return names


def all_tags():
    """Return the list of all PI tags to pull."""
    return list(tag_to_name().keys())


def text_tags():
    """Return the PI tags that hold text (phase sequence, digital valves)."""
    tags = []
    for group in PER_DIGESTER_CATEGORIES.values():
        for name in TEXT_NAMES:
            if name in group:
                tags += list(group[name].values())
    return tags


def text_columns():
    """Return the renamed column names that hold text, e.g. ['D1_main_sequence', 'D1_evacuation_valve', ...]."""
    cols = []
    for group in PER_DIGESTER_CATEGORIES.values():
        for name in TEXT_NAMES:
            if name in group:
                cols += [f"D{dig}_{name}" for dig in group[name]]
    return cols


def columns_in(category):
    """Return the column names of one category, e.g. columns_in('cooking') -> ['D1_circulation_temp', ...]."""
    if category in PER_DIGESTER_CATEGORIES:
        group = PER_DIGESTER_CATEGORIES[category]
        return [f"D{dig}_{name}" for name, per_dig in group.items() for dig in per_dig]
    return list(SHARED_CATEGORIES[category].keys())
