"""
realtime_pi/config.py  --  all PI settings in ONE place, so you can read and
check them without digging through code.

This folder fetches the X of a batch that has JUST FINISHED (after discharge, so
every X is final), formats it the same way predict.score() expects, and hands it
over. It does NOT write anything to PI.

The agent never runs anything here (no PI access rule). You fill in the TODOs
and run fetch_current.py yourself.
"""

# ====================================================================
# 1) ENDPOINT  --  where the current-batch data comes from
# ====================================================================
# MI Cube interpolated-value API (same one Lab_Analysis uses).
# TODO: confirm this is the endpoint you want and that your token has access.
PI_ENDPOINT = "https://micube.scg.com/v2/api/Datacenter/PIServer/InterpolatedValue/MultiTag/"

# Token is read from .env (never hard-code it). Key name in .env:
PI_TOKEN_ENV = "MI_CUBE_API_TOKEN"

# Request timeout (seconds).
PI_TIMEOUT = 30


# ====================================================================
# 2) PAYLOAD  --  what we send, and what shape we expect back
# ====================================================================
# The exact request body depends on the MI Cube API. Below is the SHAPE we
# assume; compare it to the real API doc / to Lab_Analysis's working call and
# fix if different.
#
# Example request body we plan to POST (edit to match the real API):
PAYLOAD_TEMPLATE = {
    "tags": [],            # filled from TAG_MAP below, per request
    "startTime": None,     # the finished batch's discharge time (plant local)
    "endTime": None,       # same instant (we want the final value)
    "interval": "1m",
}

# Example response shape we assume (list of {tag, value, timestamp}); the parser
# in fetch_current.py reads these keys. Change the keys here if the API differs.
RESPONSE_TAG_KEY = "tag"
RESPONSE_VALUE_KEY = "value"
RESPONSE_TIME_KEY = "timestamp"


# ====================================================================
# 3) TAG MAP  --  PI tag  ->  batch_master column used by predict/capability
# ====================================================================
# The X that predict.score() needs are the keys of Capability_Model/config.CAP_X:
#   pfactor_overshoot, alkali_accumulator1_conc_mean_hot_liquor_filling,
#   prehydrolysis_minutes, chip_weight_max_chip_filling, digester,
#   pfactor_temp_setpoint_last_prehydrolysis
#
# Map each to its PI tag. {k} = digester number (1-4). Some X are DERIVED (not a
# single tag) -- marked DERIVED; see DERIVED notes below.
#
# TODO: fill in the real PI tag names (see tag_summary.md / prehydrolysis.py).
TAG_MAP = {
    # batch_master column                              # PI tag (per digester k)
    "chip_weight_max_chip_filling":                    "PM2.WI{k}29",          # t, wet  (confirm)
    "alkali_accumulator1_conc_mean_hot_liquor_filling":"PM2.404AIC670",        # g/l, shared (confirm)
    "pfactor_temp_setpoint_last_prehydrolysis":        "PM2.10{k}OPESPPT",     # C, no D1 tag (confirm)
    # --- DERIVED (not one tag) -------------------------------------------------
    # pfactor_overshoot   = P-factor(final, end of HLF) - P-factor(end of prehyd)
    #                       -> needs PM2.10{k}DkPFACTOR.CALC at two sequence points.
    # prehydrolysis_minutes = duration of the PREHYDRAU sequence
    #                       -> from sequence start/end timestamps, not a value tag.
    # digester             = known already (which Dk the batch ran in).
}

# Raw tags needed to COMPUTE the derived X (fetch these, then compute in Python
# the same way prehydrolysis.py does). TODO: confirm tag names + sequence logic.
DERIVED_RAW_TAGS = {
    "pfactor_calc":   "PM2.10{k}D{k}PFACTOR.CALC",   # running P-factor counter
    "sequence_step":  "PM2.10{k}SEQSTEP",            # to find prehyd / HLF boundaries (confirm)
}


# ====================================================================
# 4) WHICH DIGESTER / WHEN  --  identify the finished batch
# ====================================================================
# You tell fetch_current.py which digester just discharged and at what time.
# (Or wire it to the discharge-detection logic later.)
# Nothing is auto-pulled until you run it.
