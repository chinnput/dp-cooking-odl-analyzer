# Real Press 1 lab samples from the log book, linked to the digester batch the pulp came from.
# PI interpolates the lab tags, so a "blank" lab time can only be seen in the log book.
# Link: lab time t -> digester k (Dk_press1_status == k, already lagged by PI AF)
#       -> digester k's most recent batch that started discharging before t.

import os
import pandas as pd

import config
from logbook import read_log_books

LAB_CACHE = os.path.join(config.DATA_DIR, "lab_samples.csv")
LAB_COLUMNS = list(config.LOG_BOOK_LAB_COLUMNS)   # press1_kappa, press1_viscosity, press1_brightness


def load_lab_samples(refresh=False):
    """
    Real Press 1 samples: one row per sample time, columns press1_kappa / viscosity / brightness.
    Read from the log book Excel files (logbook.py, config.LOG_BOOK_DIR).
    Values outside LAB_VALID_RANGE (typos, spikes) become blank.
    Saved to data/lab_samples.csv; set refresh=True to read the Excel files again.
    """
    if os.path.exists(LAB_CACHE) and not refresh:
        return pd.read_csv(LAB_CACHE, index_col="timestamp", parse_dates=True)

    lab = read_log_books()
    for col, (low, high) in config.LAB_VALID_RANGE.items():
        values = pd.to_numeric(lab[col], errors="coerce")
        lab[col] = values.where(values.between(low, high))

    os.makedirs(config.DATA_DIR, exist_ok=True)
    lab.to_csv(LAB_CACHE)
    return lab


def to_pandas_interval(interval):
    """'1h' stays '1h'; '30m' -> '30min' (in pandas 'm' is not minutes)."""
    return interval[:-1] + "min" if interval.endswith("m") else interval


def lab_table(df, lab, lab_column, interval):
    """
    One table for one lab value, e.g. 'press1_kappa':
    - times every `interval` (10:00, 11:00, ...) inside the sensor data range
    - a time is skipped when the lab has no value for this parameter
    - sensor values are taken at that exact moment
    """
    grid = pd.date_range(df.index.min().ceil(to_pandas_interval(interval)), df.index.max(),
                         freq=to_pandas_interval(interval))
    values = lab[lab_column].dropna()
    values = values[values.index.isin(grid)]

    sensors = df.drop(columns=[c for c in config.LAB_TAGS if c in df.columns])  # drop PI-interpolated lab
    table = sensors.reindex(values.index)
    table.insert(0, lab_column, values)
    return table


def lab_tables(df, lab, interval):
    """Separate tables for Kappa, Viscosity and Brightness: {lab column: table}."""
    return {col: lab_table(df, lab, col, interval) for col in LAB_COLUMNS}


def assign_digester(table):
    """
    Add column 'digester' at each lab time:
    k when Dk_press1_status == k exactly and only one digester matches, otherwise blank.
    """
    matches = pd.DataFrame({k: table[f"D{k}_press1_status"] == k for k in (1, 2, 3, 4)})
    only_one = matches.sum(axis=1) == 1
    table = table.copy()
    table["digester"] = matches.idxmax(axis=1).where(only_one)
    return table


def link_to_batch(table, batches, columns, max_hours=12):
    """
    For each lab sample of digester k, take digester k's most recent batch that started
    discharging before the sample time (at most max_hours before). Adds that batch's `columns`.
    """
    lab = table.dropna(subset=["digester"]).reset_index()
    lab["digester"] = lab["digester"].astype(int)
    lab["timestamp"] = lab["timestamp"].astype("datetime64[ns]")
    lab = lab.sort_values("timestamp")

    b = batches.dropna(subset=["discharge_start"]).copy()
    b["digester"] = b["digester"].astype(int)
    b["discharge_start"] = b["discharge_start"].astype("datetime64[ns]")
    b = b.sort_values("discharge_start")[["digester", "batch_id", "discharge_start"] + columns]

    linked = pd.merge_asof(lab, b, left_on="timestamp", right_on="discharge_start",
                           by="digester", direction="backward",
                           tolerance=pd.Timedelta(hours=max_hours))
    return linked.set_index("timestamp")


def lab_per_batch(linked):
    """
    One row per batch with its lab values (from link_to_batch results):
    press1_kappa (mean if more than one sample), press1_kappa_samples (count),
    press1_kappa_first_time (time of the first sample), same for viscosity and brightness.
    """
    result = None
    for lab_col, table in linked.items():
        t = table.dropna(subset=["batch_id"]).reset_index()
        per_batch = t.groupby(["digester", "batch_id"]).agg(
            **{lab_col: (lab_col, "mean"),
               f"{lab_col}_samples": (lab_col, "count"),
               f"{lab_col}_first_time": ("timestamp", "min")})
        result = per_batch if result is None else result.join(per_batch, how="outer")
    result = result.reset_index()
    result["batch_id"] = result["batch_id"].astype(int)
    return result


def lab_long_table(linked):
    """
    All real lab samples in one table (1 row = 1 sample of 1 lab value):
    timestamp, parameter (press1_kappa / viscosity / brightness), value, digester, batch_id.
    Samples without a digester at Press 1 are not in `linked`, so they are not here either.
    """
    parts = []
    for lab_col, table in linked.items():
        t = table.reset_index()[["timestamp", "digester", "batch_id", lab_col]]
        parts.append(t.rename(columns={lab_col: "value"}).assign(parameter=lab_col))
    result = pd.concat(parts, ignore_index=True)
    return result[["timestamp", "parameter", "value", "digester", "batch_id"]]
