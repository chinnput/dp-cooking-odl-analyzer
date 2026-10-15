# H-factor: one number for "how much kraft cooking" (temperature x time), per batch.
#   relative rate k(T) = exp(43.2 - 16115 / T_kelvin)     (Vroom; 100 C = 1, 160 C ~ 400)
#   H-factor          = sum of k(T) x hours over the cook
# Temperature = circulation temperature (config: circulation_temp). It is only valid while the liquor
# circulates (HOT LIQUOR FILLING -> DISPLACEMENT); during PREHYDRAU it stays ~85 C (no circulation).

import numpy as np
import pandas as pd

import config


def relative_rate(temp_c):
    """Vroom relative reaction rate. 100 C -> 1, 160 C -> about 400."""
    return np.exp(43.2 - 16115 / (temp_c + 273.15))


def h_factor_by_phase(df, digesters=(1, 2, 3, 4)):
    """
    H-factor added in every phase of every batch.
    H is calculated once over the whole timeline and each step (e.g. 5 min) goes to the phase it
    ends in, so no step is lost between phases.
    Returns: digester, batch_id, h_<phase> for every known phase (e.g. h_heat_and_cook).
    batch_id is counted the same way as in batch.py (a new batch at every CHIP FILLING).
    """
    parts = []
    hours = df.index.to_series().diff().dt.total_seconds().fillna(0) / 3600
    for dig in digesters:
        sequence = df[f"D{dig}_main_sequence"]
        temp = df[f"D{dig}_circulation_temp"]
        new_run = sequence != sequence.shift()
        steps = pd.DataFrame({
            "digester": dig,
            "batch_id": (new_run & (sequence == "CHIP FILLING")).cumsum(),
            "phase": sequence,
            "h": relative_rate(temp) * hours,      # H added in the step ending at this row
        })
        steps = steps[steps["phase"].isin(config.PHASE_NAMES)]
        parts.append(steps.groupby(["digester", "batch_id", "phase"])["h"].sum())

    result = pd.concat(parts).unstack("phase")
    result = result.rename(columns={p: f"h_{s}" for p, s in config.PHASE_NAMES.items()})
    result = result.reset_index()
    return result[result["batch_id"] > 0]


def h_factor_per_batch(df, phase_names=None):
    """
    H-factor per batch = sum of the H of the phases in config.H_FACTOR_PHASES,
    plus the H of every single phase for comparison.
    Returns: digester, batch_id, h_factor, h_<phase> ...
    """
    phase_names = phase_names or config.H_FACTOR_PHASES
    result = h_factor_by_phase(df)
    cols = [f"h_{config.PHASE_NAMES[p]}" for p in phase_names if f"h_{config.PHASE_NAMES[p]}" in result]
    result["h_factor"] = result[cols].sum(axis=1, min_count=1)
    per_phase = [f"h_{s}" for s in config.PHASE_NAMES.values() if f"h_{s}" in result]   # cooking order
    return result[["digester", "batch_id", "h_factor"] + per_phase]
