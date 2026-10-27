"""
Load batch_master.csv, apply the filters, and build X / y for the models.

Pure logic, no plotting. Everything it uses comes from config.py.
A feature listed in config.FEATURES that is missing or empty is skipped with a
warning instead of crashing, so you can add tags freely.
"""
import pandas as pd

import config


def load_master():
    """Raw master table sorted by batch_start (all batches, no filter)."""
    m = pd.read_csv(config.MASTER_CSV, parse_dates=["batch_start"])
    return m.sort_values("batch_start").reset_index(drop=True)


def list_columns(contains=""):
    """Print every master column you can put into config.FEATURES (optionally filtered by text)."""
    m = add_derived(load_master())
    cols = [c for c in m.columns if contains.lower() in c.lower()]
    for c in cols:
        print(f"{c:60s} non-null {m[c].notna().sum():5d}")
    return cols


def add_derived(m):
    """Features computed from master columns. Add one line per new derived feature."""
    m = m.copy()
    # Alkali sent with the white liquor per ton of wet chips (g/l x m3 / t = kg/t)
    m["alkali_charge_per_ton_chip"] = (
        m["alkali_accumulator1_conc_mean_hot_liquor_filling"] * m["white_liquor_m3"]
        / m["chip_weight_max_chip_filling"].where(m["chip_weight_max_chip_filling"] > 0)
    )
    return m


def filter_rows(m):
    """Apply quality flag, target spike filter and date range from config."""
    n0 = len(m)
    if config.QUALITY_FLAG_OK and "quality_flag" in m:
        m = m[m["quality_flag"] == "ok"]
    lo, hi = config.TARGET_RANGE
    m = m[m[config.TARGET].between(lo, hi)]
    if config.DATE_FROM:
        m = m[m["batch_start"] >= config.DATE_FROM]
    if config.DATE_TO:
        m = m[m["batch_start"] < config.DATE_TO]
    print(f"rows: {n0} batches -> {len(m)} with a {config.TARGET_LABEL} result after filters")
    return m


def usable_features(m):
    """Features from config that exist and have data. Prints a warning for the rest."""
    out = []
    for col in config.FEATURES:
        if col not in m.columns:
            print(f"  WARNING skip '{col}': not a column (check the name with data.list_columns())")
        elif m[col].notna().sum() == 0:
            print(f"  WARNING skip '{col}': column is empty")
        else:
            out.append(col)
    return out


def digester_columns(m):
    """D2..D4 dummy columns (D1 = reference). Added to m in place."""
    cols = []
    for k in (2, 3, 4):
        m[f"is_D{k}"] = (m["digester"] == k).astype(int)
        cols.append(f"is_D{k}")
    return cols


def build_xy():
    """
    Return (df, features) where df holds digester, batch_start, every feature and the target,
    with rows that have all of them. Rows stay in time order (needed for TimeSeriesSplit).
    """
    m = filter_rows(add_derived(load_master()))
    feats = usable_features(m)
    if config.USE_DIGESTER_ID:
        feats = feats + digester_columns(m)
    df = m[["digester", "batch_id", "batch_start"] + feats + [config.TARGET]].dropna().reset_index(drop=True)
    print(f"rows with all {len(feats)} features: {len(df)}  "
          f"({df['batch_start'].min():%Y-%m-%d} .. {df['batch_start'].max():%Y-%m-%d})")
    return df, feats


def coverage(m=None):
    """Per-feature table: non-null count per digester and % NaN, after the row filters."""
    if m is None:
        m = filter_rows(add_derived(load_master()))
    rows = []
    for col in config.FEATURES:
        if col not in m.columns:
            rows.append({"feature": col, "label": config.FEATURES[col], "status": "missing column"})
            continue
        r = {"feature": col, "label": config.FEATURES[col], "status": "ok",
             "pct_nan": round(100 * m[col].isna().mean(), 1)}
        for k, g in m.groupby("digester"):
            r[f"n_D{k}"] = int(g[col].notna().sum())
        rows.append(r)
    return pd.DataFrame(rows)


def label(col):
    """Short label for plots (falls back to the column name)."""
    if col.startswith("is_D"):
        return col.replace("is_", "")
    return config.FEATURES.get(col, col)
