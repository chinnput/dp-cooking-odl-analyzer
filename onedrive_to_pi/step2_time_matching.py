"""
Step 2: Real-time Incremental Filtering for Lab Data.
Filters out historical rows and selects only new lab entries (Timestamp > last_sync_timestamp).
"""

import pandas as pd
from datetime import datetime
from step1_fetch_onedrive import load_sync_state


def match_lab_time_to_batches(df_lab: pd.DataFrame, df_batches: pd.DataFrame = None, filter_incremental: bool = False) -> pd.DataFrame:
    """
    Sorts and prepares lab measurements.
    If filter_incremental is True, returns only records newer than last_sync_timestamp.
    If filter_incremental is False, returns all historical records sorted chronologically for backfill.
    """
    print("[Step 2] Processing lab measurements...")

    if df_lab.empty:
        return pd.DataFrame()

    df_sorted = df_lab.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)

    if not filter_incremental:
        print(f"[Step 2] Historical Mode: Returning all {len(df_sorted)} historical records sorted chronologically.")
        return df_sorted

    # Incremental Mode
    state = load_sync_state()
    last_sync_str = state.get("last_sync_timestamp")

    if last_sync_str:
        try:
            last_sync_dt = datetime.fromisoformat(last_sync_str)
            print(f"[Step 2] Filtering records newer than last sync timestamp: {last_sync_dt}")

            df_new = df_sorted[df_sorted["Timestamp"] > last_sync_dt].copy()
            print(f"[Step 2] Found {len(df_new)} new lab record(s) to send.")
            return df_new
        except Exception as e:
            print(f"[Step 2] Warning parsing last_sync_timestamp ({e}).")

    return df_sorted


if __name__ == "__main__":
    print("[Step 2] Standalone test placeholder")

