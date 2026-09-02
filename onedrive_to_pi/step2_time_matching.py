"""
Step 2: Processing and Filtering Lab Data.
Supports two clean execution modes:
1. mode="backfill": Returns ALL historical lab records sorted chronologically.
2. mode="hourly": Checks for the latest hourly lab entry and filters for new records (Timestamp > last_sync_timestamp).
"""

import pandas as pd
from datetime import datetime
import config
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

    # Hourly Mode (Real-Time Automation with 3-Day Lookback Window)
    state = load_sync_state()
    pushed_history = state.get("pushed_history_3days", [])
    
    # Create a fast lookup set of (timestamp, tag) pairs that were already pushed
    already_pushed_pairs = {
        (item.get("timestamp"), item.get("tag"))
        for item in pushed_history
        if item.get("timestamp") and item.get("tag")
    }

    current_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_excel_ts = df_sorted["Timestamp"].max()

    print(f"[Step 2] Checking Excel for new/backfilled hourly entries (Check Time: {current_check_time})...")
    print(f"[Step 2] Latest Timestamp in Excel : {latest_excel_ts}")
    print(f"[Step 2] Pushed history items count : {len(already_pushed_pairs)}")

    # Filter df_sorted to rows within 3-day lookback window
    cutoff_3days = datetime.now() - pd.Timedelta(days=3)
    df_recent = df_sorted[df_sorted["Timestamp"] >= cutoff_3days].copy().reset_index(drop=True)

    if df_recent.empty:
        df_recent = df_sorted.tail(24).copy().reset_index(drop=True)

    # Check for unpushed values even if their timestamp is earlier than max timestamp
    unpushed_rows = []
    for idx, row in df_recent.iterrows():
        ts_str = row["Timestamp"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(row["Timestamp"], "strftime") else str(row["Timestamp"])
        
        # Check if any mapped tag value in this row has not been pushed yet
        has_new_val = False
        for param_key, tag_name in config.PI_TAG_MAPPING.items():
            for col in df_recent.columns:
                if col == param_key or col.replace("_", "") == param_key.replace("_", ""):
                    if pd.notna(row[col]) and (ts_str, tag_name) not in already_pushed_pairs:
                        has_new_val = True
                        break
            if has_new_val:
                break

        if has_new_val:
            unpushed_rows.append(row)

    if unpushed_rows:
        df_new = pd.DataFrame(unpushed_rows).reset_index(drop=True)
        latest_ts = df_new.iloc[-1]["Timestamp"]
        print(f"[Step 2] ✅ Found {len(df_new)} row(s) with new/backfilled lab values up to {latest_ts}.")
        return df_new
    else:
        print("[Step 2] ℹ️ All recent lab values have already been pushed to PI Server. Waiting for next hourly trigger.")
        return pd.DataFrame()


# Backward compatibility alias
match_lab_time_to_batches = process_lab_data


if __name__ == "__main__":
    print("[Step 2] Standalone test placeholder")


