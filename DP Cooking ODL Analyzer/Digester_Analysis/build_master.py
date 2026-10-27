# Build the Batch Master Table (1 row = 1 batch) and the linked lab table in one call.
#
#   pulled sensor data (5 min) ──► phases ──► batches ──► + H-factor ──► + batch features
#                                                                   ──► + lab (linked by status) ──► + quality flag
#
# Used by 01_build_master.ipynb. 02_analysis.ipynb only reads the saved CSV files.

import os
import pandas as pd

import config
from batch import (all_phase_tables, build_batch_table, batch_features,
                   phase_summary, phase_summary_with_lab, add_quality_flags, add_lab_grades)
from hfactor import h_factor_per_batch
from lab import lab_tables, assign_digester, link_to_batch, lab_per_batch, lab_long_table


def build_master(df, lab):
    """
    df  = pulled sensor data (load_data), lab = real lab samples (load_lab_samples).
    Returns (master, phases, lab_linked, phases_summary, phases_summary_lab):
      master             - 1 row = 1 batch: times, phase times/minutes, H-factor, features, lab, quality_flag
      phases             - 1 row = 1 phase run (for checking)
      lab_linked         - 1 row = 1 real lab sample with its digester and batch_id
      phases_summary     - 1 row = 1 phase run with start/end/minutes + mean/min/max of every sensor
      phases_summary_lab - phases_summary + the batch's Press 1 lab values
    """
    keys = ["digester", "batch_id"]

    # 1. Phases and batches from the main sequence tag
    phases = all_phase_tables(df)
    master = build_batch_table(phases)

    # 2. H-factor (phases in config.H_FACTOR_PHASES) + H of every single phase
    master = master.merge(h_factor_per_batch(df), on=keys, how="left")

    # 3. Batch features from config.BATCH_FEATURES
    master = master.merge(batch_features(df, phases, config.BATCH_FEATURES), on=keys, how="left")

    # 4. Derived values
    chips = master.get("chip_weight_max_chip_filling")
    full = master.get("chip_weight_max_hot_liquor_filling")
    if chips is not None and full is not None:
        # Liquor added per ton of chips (wet chip weight -> approximate L:W ratio)
        master["liquor_to_wood_ratio"] = (full - chips) / chips.where(chips > 0)
    wl_flow = master.get("white_liquor_dosing_flow_mean_hot_liquor_filling")
    if chips is not None and wl_flow is not None:
        # White liquor volume in this batch (mean m3/h x hours of HOT LIQUOR FILLING), and per ton of wet chips.
        # H-factor does not see the chip weight, so the same temperature gives a different cook per ton of chips.
        master["white_liquor_m3"] = wl_flow * master["hot_liquor_filling_minutes"] / 60
        master["white_liquor_per_ton_chip"] = master["white_liquor_m3"] / chips.where(chips > 0)
    if "pfactor_actual_last_prehydrolysis" in master and "pfactor_setpoint_last_prehydrolysis" in master:
        master["pfactor_gap"] = master["pfactor_actual_last_prehydrolysis"] - master["pfactor_setpoint_last_prehydrolysis"]

    # 5. Lab: real samples -> digester at Press 1 -> batch, with a low/good/high grade per target
    tables = {name: assign_digester(t) for name, t in lab_tables(df, lab, config.LAB_INTERVAL).items()}
    linked = {name: link_to_batch(t, master, []) for name, t in tables.items()}
    lab_batch = add_lab_grades(lab_per_batch(linked))
    master = master.merge(lab_batch, on=keys, how="left")

    # 6. Quality flag (nothing removed)
    master = add_quality_flags(master)

    # 7. Phase summary: 1 row = 1 phase run, mean/min/max of every sensor (raw, filtered),
    #    plus a copy with the batch's Press 1 lab values merged in.
    phases_summary = phase_summary(df, phases)
    phases_summary_lab = phase_summary_with_lab(phases_summary, lab_batch)
    return master, phases, lab_long_table(linked), phases_summary, phases_summary_lab


def save_outputs(master, lab_linked, phases_summary=None, phases_summary_lab=None):
    """Save the tables to DATA_DIR (CSV, open in Excel)."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    master_path = os.path.join(config.DATA_DIR, config.BATCH_MASTER_FILE)
    lab_path = os.path.join(config.DATA_DIR, config.LAB_LINKED_FILE)
    master.to_csv(master_path, index=False)
    lab_linked.to_csv(lab_path, index=False)
    print(f"Saved {len(master)} batches    -> {master_path}")
    print(f"Saved {len(lab_linked)} lab rows -> {lab_path}")
    if phases_summary is not None:
        phase_path = os.path.join(config.DATA_DIR, config.PHASE_SUMMARY_FILE)
        phases_summary.to_csv(phase_path, index=False)
        print(f"Saved {len(phases_summary)} phase runs -> {phase_path}")
    if phases_summary_lab is not None:
        phase_lab_path = os.path.join(config.DATA_DIR, config.PHASE_SUMMARY_LAB_FILE)
        phases_summary_lab.to_csv(phase_lab_path, index=False)
        print(f"Saved {len(phases_summary_lab)} phase runs (with lab) -> {phase_lab_path}")


def load_outputs():
    """Read the saved tables (used by 02_analysis.ipynb)."""
    master = pd.read_csv(os.path.join(config.DATA_DIR, config.BATCH_MASTER_FILE))
    for col in master.columns:
        if col.endswith("_start") or col.endswith("_end") or col.endswith("_time"):
            master[col] = pd.to_datetime(master[col])
    lab_linked = pd.read_csv(os.path.join(config.DATA_DIR, config.LAB_LINKED_FILE), parse_dates=["timestamp"])
    return master, lab_linked


def load_phase_summary(with_lab=False):
    """Read the saved phase summary table (1 row = 1 phase run). with_lab=True reads the lab-merged copy."""
    name = config.PHASE_SUMMARY_LAB_FILE if with_lab else config.PHASE_SUMMARY_FILE
    phases_summary = pd.read_csv(os.path.join(config.DATA_DIR, name), parse_dates=["start", "end"])
    return phases_summary