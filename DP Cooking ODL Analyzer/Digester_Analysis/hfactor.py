# H-factor: one number for "how much cooking" (temperature x time), per batch.
#   relative rate k(T) = exp(43.2 - 16115 / T_kelvin)     (100 C = 1)
#   H-factor          = sum of k(T) x hours over the cook

import numpy as np
import pandas as pd


def relative_rate(temp_c):
    """Vroom relative reaction rate. 100 C -> 1, 160 C -> about 400."""
    return np.exp(43.2 - 16115 / (temp_c + 273.15))


def h_factor(temp):
    """H-factor of one temperature series (pd.Series with a time index, in C)."""
    temp = temp.dropna()
    if len(temp) < 2:
        return np.nan
    hours = temp.index.to_series().diff().dt.total_seconds().fillna(0) / 3600
    return float((relative_rate(temp) * hours).sum())


def h_factor_per_batch(df, phases, phase_names=("HEAT&COOK",)):
    """
    H-factor for every batch, using the temperature during the given phases.
    Returns: digester, batch_id, h_factor, max_temp
    """
    cook = phases[phases["phase"].isin(phase_names) & (phases["batch_id"] > 0)]

    rows = []
    for _, p in cook.iterrows():
        temp = df.loc[p["start"]:p["end"], f"D{p['digester']}_temp"]
        rows.append({
            "digester": p["digester"],
            "batch_id": p["batch_id"],
            "h_factor": h_factor(temp),
            "max_temp": temp.max(),
        })

    result = pd.DataFrame(rows)
    # A batch can have more than one HEAT&COOK run (e.g. a short interruption) -> add them up
    return result.groupby(["digester", "batch_id"]).agg(
        h_factor=("h_factor", "sum"), max_temp=("max_temp", "max")).reset_index()
