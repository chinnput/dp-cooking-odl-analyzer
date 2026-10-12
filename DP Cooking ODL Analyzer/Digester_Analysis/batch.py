# Split the timeline into phases and batches using the main sequence (phase) tag of each digester.

import pandas as pd


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


def build_batch_table(phases):
    """
    One row per batch: digester, batch_id, batch_number, start, end,
    plus the minutes spent in each phase (one column per phase, e.g. "minutes_HEAT&COOK").
    """
    phases = phases[phases["batch_id"] > 0]   # skip the incomplete batch at the start

    batches = phases.groupby(["digester", "batch_id"]).agg(
        batch_number=("batch_number", "first"),
        start=("start", "min"),
        end=("end", "max"),
    )
    minutes = phases.pivot_table(index=["digester", "batch_id"], columns="phase",
                                 values="duration_minutes", aggfunc="sum")
    minutes.columns = [f"minutes_{c}" for c in minutes.columns]

    return batches.join(minutes).reset_index()


def all_phase_tables(df, digesters=(1, 2, 3, 4)):
    """Phase tables for all digesters, stacked into one table."""
    return pd.concat([build_phase_table(df, d) for d in digesters], ignore_index=True)
