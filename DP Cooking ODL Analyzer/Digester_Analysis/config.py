# Settings for the batch digester analysis.
# Edit this file to change WHAT to pull. The code in the other files stays the same.
# Tag source: ../batch_digester_tags_per_digester.csv (verify before use)

import os

# ---- Time range for the pull
START_TIME = "2026-08-01 00:00:00"
END_TIME = "2026-10-01 00:00:00"
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
    "displacement_liquor_temp": {1: "PM2.104TIS114", 2: "PM2.104TIS214",
                                 3: "PM2.104TIS314", 4: "PM2.404TIS414"},
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

# ===== 9. LAB QUALITY AT PRESS 1 (Y) =====
# Written to PI by onedrive_to_pi. PI interpolates between samples (Step = 0):
# in the analysis keep only the real sample times from the log book.
LAB_TAGS = {
    "press1_kappa": "PULP-LINE2-KAPPA-PRESS1",
    "press1_viscosity": "PULP-LINE2-VISCOSITY-PRESS1",
    "press1_brightness": "PULP-LINE2-BRIGHTNESS-PRESS1",
}

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
    "lab": LAB_TAGS,
}

# Tags that hold text states, not numbers (kept as text when pulled)
TEXT_NAMES = ["main_sequence", "evacuation_valve"]

# ---- Phase names seen in the MAINSEQ tags (for reference)
PHASES = ["CHIP FILLING", "PREHYDRAU", "HOT LIQUOR FILLING", "HEAT&COOK",
          "DISPLACEMENT", "DISCHARGE", "WAIT"]

# Phases used for the H-factor (kraft cook)
H_FACTOR_PHASES = ["HEAT&COOK"]


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


def columns_in(category):
    """Return the column names of one category, e.g. columns_in('cooking') -> ['D1_circulation_temp', ...]."""
    if category in PER_DIGESTER_CATEGORIES:
        group = PER_DIGESTER_CATEGORIES[category]
        return [f"D{dig}_{name}" for name, per_dig in group.items() for dig in per_dig]
    return list(SHARED_CATEGORIES[category].keys())
