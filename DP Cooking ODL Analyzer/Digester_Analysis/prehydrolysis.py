# Prehydrolysis (PREHYDRAU) features per batch, from the pulled 5-min data.
#
#   pfactor_final         P-factor where the counter stops. The phase ends when P-factor reaches the
#                         setpoint, but the digester is still hot and acid until the hot liquor
#                         neutralises it, so the counter keeps rising during HOT LIQUOR FILLING.
#   pfactor_overshoot     pfactor_final - P-factor setpoint
#   ptemp_overshoot       P-temp max in PREHYDRAU - P-temp setpoint (no D1 setpoint tag -> NaN)
#   minutes_above_<T>     minutes in PREHYDRAU with P-temp >= T C (config.PH_TEMP_THRESHOLDS)
#   steam_users_other     mean number of OTHER digesters in a steam phase (config.STEAM_PHASES)
#                         while this batch is in PREHYDRAU: they share the MP steam header
#
# Used by build_master.py. Same batch_id as batch.py (a new batch at every CHIP FILLING).

import numpy as np
import pandas as pd

import config


def steam_users(df, digesters=(1, 2, 3, 4)):
    """Number of digesters in a steam phase at every timestamp."""
    in_steam = [df[f"D{d}_main_sequence"].isin(config.STEAM_PHASES) for d in digesters]
    return pd.concat(in_steam, axis=1).sum(axis=1)


def _window(df, column, windows):
    """Values of one column over a list of (start, end) phase windows."""
    if column not in df.columns or not len(windows):
        return pd.Series(dtype=float)
    return pd.concat([df.loc[w.start:w.end, column] for w in windows.itertuples()]).dropna()


def prehydrolysis_features(df, phases):
    """One row per batch: digester, batch_id + the columns listed at the top of this file."""
    users = steam_users(df)
    step_min = df.index.to_series().diff().dt.total_seconds().median() / 60   # 5 for 5-min data
    rows = []
    for (dig, batch_id), p in phases.groupby(["digester", "batch_id"]):
        ph = p[p["phase"] == "PREHYDRAU"]
        row = {"digester": dig, "batch_id": batch_id}
        if ph.empty:
            rows.append(row)
            continue
        ph_and_hlf = p[p["phase"].isin(["PREHYDRAU", "HOT LIQUOR FILLING"])]

        pf = _window(df, f"D{dig}_pfactor_actual", ph_and_hlf)
        pf_sp = _window(df, f"D{dig}_pfactor_setpoint", ph)
        row["pfactor_final"] = pf.max() if len(pf) else np.nan
        row["pfactor_overshoot"] = row["pfactor_final"] - pf_sp.iloc[-1] if len(pf_sp) else np.nan

        temp = _window(df, f"D{dig}_pfactor_temp", ph)
        temp_sp = _window(df, f"D{dig}_pfactor_temp_setpoint", ph)
        row["ptemp_overshoot"] = temp.max() - temp_sp.iloc[-1] if len(temp) and len(temp_sp) else np.nan
        for t in config.PH_TEMP_THRESHOLDS:
            row[f"minutes_above_{t}"] = (temp >= t).sum() * step_min if len(temp) else np.nan

        others = pd.concat([users.loc[w.start:w.end] for w in ph.itertuples()]) - 1
        row["steam_users_other"] = others.mean()
        rows.append(row)
    return pd.DataFrame(rows)
