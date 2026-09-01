"""
Step 2: Processing and Filtering Lab Data.
Supports two clean execution modes:
1. mode="backfill": Returns ALL historical lab records sorted chronologically.
2. mode="hourly": Checks for the latest hourly lab entry and filters for new records (Timestamp > last_sync_timestamp).
"""

import pandas as pd
from datetime import datetime
from step1_fetch_onedrive import load_sync_state


def process_lab_data(df_lab: pd.DataFrame, mode: str = "hourly") -> pd.DataFrame:
    """
    Filters and prepares lab measurements based on selected mode ("hourly", "backfill", or "new_tags_only").
    """
    print(f"[Step 2] Processing lab measurements (Mode: '{mode}')...")

    if df_lab.empty:
        print("[Step 2] Warning: Input DataFrame is empty.")
        return pd.DataFrame()

    # Drop rows without valid Timestamp and sort chronologically
    df_sorted = df_lab.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)

    if mode == "backfill":
        print(f"[Step 2] Backfill Mode: Prepared all {len(df_sorted)} historical records sorted chronologically.")
        return df_sorted

    if mode == "new_tags_only":
        print(f"[Step 2] New Tags Only Mode: Filtering historical records for 6 new tags (pH & Brightness D1/D2)...")
        # Keep only columns matching new tags: pH_D0, pH_Eop, pH_D1, pH_D2, Brightness_D1, Brightness_D2
        new_tag_cols = ["File_Name", "Sheet_Name", "Date_Str", "Time_Str", "Timestamp",
                        "pH_D0", "pH_Eop", "pH_D1", "pH_D2", "Brightness_D1", "Brightness_D2"]
        avail = [c for c in new_tag_cols if c in df_sorted.columns]
        df_new_tags = df_sorted[avail].dropna(subset=[c for c in avail if c.startswith(("pH_", "Brightness_"))], how="all").reset_index(drop=True)
        print(f"[Step 2] Found {len(df_new_tags)} historical record(s) containing new tag values.")
        return df_new_tags

    # Hourly Mode (Real-Time Automation)
    state = load_sync_state()
    last_sync_str = state.get("last_sync_timestamp")
    current_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_excel_ts = df_sorted["Timestamp"].max()

    print(f"[Step 2] Checking Excel for new hourly entries (Current Check Time: {current_check_time})...")
    print(f"[Step 2] Latest Timestamp available in Excel: {latest_excel_ts}")

    if last_sync_str:
        try:
            last_sync_dt = datetime.fromisoformat(last_sync_str)
            print(f"[Step 2] Last synced timestamp in state : {last_sync_dt}")

            df_new = df_sorted[df_sorted["Timestamp"] > last_sync_dt].copy().reset_index(drop=True)
            
            if not df_new.empty:
                latest_ts = df_new.iloc[-1]["Timestamp"]
                print(f"[Step 2] Found {len(df_new)} new hourly lab update(s) up to {latest_ts}.")
                return df_new
            else:
                print(f"[Step 2]  No new lab entries found newer than {last_sync_dt}. Waiting for next hourly trigger.")
                return pd.DataFrame()
        except Exception as e:
            print(f"[Step 2] Warning parsing last_sync_timestamp ({e}). Defaulting to latest entry.")

    # First-time run in hourly mode: Return only the most recent 1 record to avoid accidental backfill dump
    if not df_sorted.empty:
        latest_row = df_sorted.tail(1).copy().reset_index(drop=True)
        latest_ts = latest_row.iloc[0]["Timestamp"]
        print(f"[Step 2] First-time hourly run: Selected latest single entry at {latest_ts}.")
        return latest_row

    return pd.DataFrame()


# Backward compatibility alias
match_lab_time_to_batches = process_lab_data


if __name__ == "__main__":
    print("[Step 2] Standalone test placeholder")


