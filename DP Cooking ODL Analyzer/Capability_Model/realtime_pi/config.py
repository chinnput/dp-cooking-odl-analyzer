"""
realtime_pi/config.py  --  all PI settings in ONE place, so you can read and
check them without digging through code.

This folder fetches the X of a batch that has JUST FINISHED (after discharge, so
every X is final), formats it the same way predict.score() expects, and hands it
over. It does NOT write anything to PI.

The agent never runs anything here (no PI access rule). You fill in the few
remaining TODOs and run fetch_current.py yourself.

Endpoint / tags / server are taken straight from Digester_Analysis/config.py,
which is the working MI Cube pull used elsewhere in the repo.
"""

import os

# ====================================================================
# 1) ENDPOINT  --  where the current-batch data comes from
# ====================================================================
# MI Cube interpolated-value API (same one Digester_Analysis/Lab_Analysis use).
PI_ENDPOINT = "https://micube.scg.com/v2/api/Datacenter/PIServer/InterpolatedValue/MultiTag/"
PI_SERVER = "VPKGDRBPPI01"

# Token is read from the .env file in the PROJECT ROOT (git root), i.e.
#   D:\chinnput\DP Cooking ODL Analyzer\.env
# which already has this key. NEVER hard-code the token here.
# fetch_current.py finds it with find_dotenv(usecwd=True), so it works no matter
# which folder you run from. Key name in .env:
PI_TOKEN_ENV = "MI_CUBE_API_TOKEN"

# Request timeout (seconds).
PI_TIMEOUT = 30


# ====================================================================
# 2) PAYLOAD  --  what we send (matches the real MI Cube body)
# ====================================================================
# Real request body shape (snake_case, time RANGE + interval):
#   {
#       "token":      "<from .env>",
#       "server":     PI_SERVER,
#       "tags":       ["...", "...", "..."],   # filled from the tags we need
#       "start_time": "2026-10-01 00:00:00",   # batch CHIP-FILLING start (plant local)
#       "end_time":   "2026-10-01 10:00:00",   # batch DISCHARGE end (plant local)
#       "interval":   "5m",
#   }
# We pull the WHOLE finished batch as a time series, then compute each X in
# Python (max over chip-filling, mean over HLF, overshoot, prehyd minutes) the
# same way Digester_Analysis does -- NOT a single-instant value.
PAYLOAD_TEMPLATE = {
    "token": None,          # filled from .env at request time
    "server": PI_SERVER,
    "tags": [],             # filled from the tag lists below, per request
    "start_time": None,     # batch start (chip filling), plant local "YYYY-MM-DD HH:MM:SS"
    "end_time": None,       # batch end (discharge),       plant local
    "interval": "5m",       # same as Digester_Analysis
}

# Response shape (confirmed against Digester_Analysis/pull_data.py):
#   {"status": "success",
#    "results": {"<tag>": [{"timestamp": "...", "value": ...}, ...], ...}}
# results is a DICT keyed by tag (not a list), and each record has timestamp/value.
RESPONSE_RESULTS_KEY = "results"      # dict: tag -> list of records
RESPONSE_VALUE_KEY = "value"
RESPONSE_TIME_KEY = "timestamp"


# ====================================================================
# 3) TAGS  --  {k} = digester number (1-4); taken from Digester_Analysis/config.py
# ====================================================================
# The X that predict.score() needs are the keys of Capability_Model/config.CAP_X:
#   pfactor_overshoot, alkali_accumulator1_conc_mean_hot_liquor_filling,
#   prehydrolysis_minutes, chip_weight_max_chip_filling, digester,
#   pfactor_temp_setpoint_last_prehydrolysis
#
# Per-digester tags: D1-D3 use the "104" prefix, D4 uses "404" (older digester).

# --- Direct X -> PI tag (per digester) ---
CHIP_WEIGHT_TAG = {1: "PM2.104WI129", 2: "PM2.104WI229",
                   3: "PM2.104WI329", 4: "PM2.404WI429"}           # ton, max over CHIP FILLING

PFACTOR_TEMP_SETPOINT_TAG = {2: "PM2.104D2OPESPPT.CALC",           # C, last value in PREHYDRAU
                             3: "PM2.104D3OPESPPT.CALC",
                             4: "PM2.404D4OPESPPT.CALC"}           # NOTE: no D1 tag

PREHYD_MINUTES_TAG = {1: "PM2.104DIG1PHP_T", 2: "PM2.104DIG2PHP_T",   # minutes elapsed in prehyd
                      3: "PM2.104DIG3PHP_T", 4: "PM2.404DIG4PHP_T"}   # take the max/last value

# --- Shared X ---
ALKALI_CONC1_TAG = "PM2.404AIC670:MV"                             # g/l, mean over HOT LIQUOR FILLING

# --- Tags needed to COMPUTE the derived X ---
# pfactor_overshoot = max(pfactor_actual over PREHYDRAU + HOT LIQUOR FILLING)
#                     - pfactor_setpoint(last value in PREHYDRAU)
# (matches Digester_Analysis/prehydrolysis.py, the definition the model trains on)
PFACTOR_ACTUAL_TAG = {1: "PM2.104D1PFACTOR.CALC", 2: "PM2.104D2PFACTOR.CALC",
                      3: "PM2.104D3PFACTOR.CALC", 4: "PM2.404D4PFACTOR.CALC"}
PFACTOR_SETPOINT_TAG = {1: "PM2.104D1OPESPPF.CALC", 2: "PM2.104D2OPESPPF.CALC",
                        3: "PM2.104D3OPESPPF.CALC", 4: "PM2.404D4OPESPPF.CALC"}

# Phase boundaries come from the main-sequence text tag (PREHYDRAU / HOT LIQUOR
# FILLING / ... / DISCHARGE). Slice the series by when this tag changes.
MAIN_SEQUENCE_TAG = {1: "PM2.104DIG1MAINSEQ", 2: "PM2.104DIG2MAINSEQ",
                     3: "PM2.104DIG3MAINSEQ", 4: "PM2.404DIG4MAINSEQ"}


def tags_for(k):
    """Every PI tag fetch_current needs for digester k (skips missing ones)."""
    tags = [
        CHIP_WEIGHT_TAG.get(k),
        PFACTOR_TEMP_SETPOINT_TAG.get(k),    # None for D1
        PREHYD_MINUTES_TAG.get(k),
        ALKALI_CONC1_TAG,
        PFACTOR_ACTUAL_TAG.get(k),
        PFACTOR_SETPOINT_TAG.get(k),
        MAIN_SEQUENCE_TAG.get(k),
    ]
    return [t for t in tags if t]


# How the fetched series map onto the X that predict expects, and how to reduce
# each one over its phase window:
#   batch_master column                                  (source tag, phase, how)
REDUCTION = {
    "chip_weight_max_chip_filling":                       ("CHIP_WEIGHT_TAG",  "CHIP FILLING",       "max"),
    "alkali_accumulator1_conc_mean_hot_liquor_filling":   ("ALKALI_CONC1_TAG", "HOT LIQUOR FILLING", "mean"),
    "pfactor_temp_setpoint_last_prehydrolysis":           ("PFACTOR_TEMP_SETPOINT_TAG", "PREHYDRAU", "last"),
    "prehydrolysis_minutes":                              ("PREHYD_MINUTES_TAG", "PREHYDRAU",        "max"),
    # pfactor_overshoot is DERIVED in fetch_current (end-HLF minus end-prehyd).
    # digester is known already.
}


# ====================================================================
# 4) WHICH DIGESTER / WHEN  --  identify the finished batch
# ====================================================================
# You tell fetch_current.py which digester just discharged and its start/end
# time (chip-filling start -> discharge end). Nothing is auto-pulled until you
# run it. Phase names above must match the exact MAINSEQ text in PI
# (e.g. "PREHYDRAU", "HOT LIQUOR FILLING", "DISCHARGE") -- confirm the strings.
