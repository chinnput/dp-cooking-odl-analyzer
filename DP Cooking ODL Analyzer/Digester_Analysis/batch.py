# Batches and phases from the main sequence tag of each digester,
# plus per-batch features and quality flags.

import numpy as np
import pandas as pd

import config


def build_phase_table(df, dig):
    """
    One row per phase run of digester `dig`:
    digester, phase, start, end, duration_minutes, batch_number, batch_id

    batch_id counts CHIP FILLING starts (each new chip filling = a new batch).
    batch_number is the DCS batch number read at the start of the phase (for reference).
    """
    sequence = df[f"D{dig}_main_sequence"].dropna()

    # A new run starts every time the phase text changes
    run_id = (sequence != sequence.shift()).cumsum()

    rows = []
    for _, run in sequence.groupby(run_id):
        start, end = run.index[0], run.index[-1]
        rows.append({
            "digester": dig,
            "phase": run.iloc[0],
            "start": start,
            "end": end,
            "duration_minutes": (end - start).total_seconds() / 60,
            "batch_number": df.at[start, f"D{dig}_batch_number"],
        })
    phases = pd.DataFrame(rows)

    # New batch at every CHIP FILLING; phases before the first one get batch_id 0
    phases["batch_id"] = (phases["phase"] == "CHIP FILLING").cumsum()
    return phases


def all_phase_tables(df, digesters=(1, 2, 3, 4)):
    """Phase tables for all digesters, stacked into one table (batch_id 0 = incomplete start, dropped)."""
    phases = pd.concat([build_phase_table(df, d) for d in digesters], ignore_index=True)
    return phases[phases["batch_id"] > 0].reset_index(drop=True)


def build_batch_table(phases):
    """
    One row per batch:
    digester, batch_id, batch_number, batch_start, batch_end, batch_hours,
    <phase>_start / <phase>_end / <phase>_minutes for every known phase,
    unknown_phase_count (runs with a phase text not in config.PHASE_NAMES, e.g. "8", "0").
    If a phase appears more than once in a batch: first start, last end, minutes added up.
    """
    batches = phases.groupby(["digester", "batch_id"]).agg(
        batch_number=("batch_number", "first"),
        batch_start=("start", "min"),
        batch_end=("end", "max"),
    )
    batches["batch_hours"] = (batches["batch_end"] - batches["batch_start"]).dt.total_seconds() / 3600

    known = phases[phases["phase"].isin(config.PHASE_NAMES)]
    per_phase = known.groupby(["digester", "batch_id", "phase"]).agg(
        start=("start", "min"), end=("end", "max"), minutes=("duration_minutes", "sum")
    ).unstack("phase")
    for phase, short in config.PHASE_NAMES.items():          # keep the cooking order
        if ("start", phase) in per_phase.columns:
            batches[f"{short}_start"] = per_phase[("start", phase)]
            batches[f"{short}_end"] = per_phase[("end", phase)]
            batches[f"{short}_minutes"] = per_phase[("minutes", phase)]

    unknown = phases[~phases["phase"].isin(config.PHASE_NAMES)]
    batches["unknown_phase_count"] = unknown.groupby(["digester", "batch_id"]).size()
    batches["unknown_phase_count"] = batches["unknown_phase_count"].fillna(0).astype(int)
    return batches.reset_index()


def summarise(values, statistic):
    """One number from a series: 'max', 'min', 'mean' or 'last' (last valid value)."""
    values = values.dropna()
    if values.empty:
        return np.nan
    if statistic == "last":
        return values.iloc[-1]
    return getattr(values, statistic)()


def batch_features(df, phases, features):
    """
    For every batch and every (sensor, phases, statistic) in `features` (config.BATCH_FEATURES):
    take the sensor while the batch is in those phases and summarise it.
    Per-digester sensors use column D<k>_<sensor>; shared sensors use column <sensor>.
    Returns: digester, batch_id, one column per feature, e.g. chip_weight_max_chip_filling.
    """
    rows = []
    for (dig, batch_id), p in phases.groupby(["digester", "batch_id"]):
        row = {"digester": dig, "batch_id": batch_id}
        for sensor, phase_list, statistic in features:
            column = f"D{dig}_{sensor}" if f"D{dig}_{sensor}" in df.columns else sensor
            name = f"{sensor}_{statistic}_" + "_".join(config.PHASE_NAMES[ph] for ph in phase_list)
            if column not in df.columns:            # e.g. no screen_diff_pressure tag for D4
                row[name] = np.nan
                continue
            windows = p[p["phase"].isin(phase_list)]
            values = pd.concat([df.loc[w.start:w.end, column] for w in windows.itertuples()]) \
                if len(windows) else pd.Series(dtype=float)
            row[name] = summarise(values, statistic)
        rows.append(row)
    return pd.DataFrame(rows)


def add_quality_flags(master):
    """
    Column quality_flag: "ok", or one or more of (joined with ";"):
      missing_phase  - no HEAT&COOK or no DISCHARGE (sequence broken, or cut by the data range)
      unknown_phase  - phase text that is not a real phase (e.g. "8", "0")
      long_batch     - batch longer than config.LONG_BATCH_HOURS (probably includes a stop)
      no_h_factor    - H-factor missing or 0
    Nothing is removed; filter on quality_flag == "ok" in the analysis.
    """
    flags = []
    for _, b in master.iterrows():
        f = []
        if pd.isna(b.get("heat_and_cook_start")) or pd.isna(b.get("discharge_start")):
            f.append("missing_phase")
        if b["unknown_phase_count"] > 0:
            f.append("unknown_phase")
        if b["batch_hours"] > config.LONG_BATCH_HOURS:
            f.append("long_batch")
        if not b["h_factor"] > 0:
            f.append("no_h_factor")
        flags.append(";".join(f) if f else "ok")
    master = master.copy()
    master["quality_flag"] = flags
    return master
