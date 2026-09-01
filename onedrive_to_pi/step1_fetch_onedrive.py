"""
Step 1: Fetch data from OneDrive / SharePoint Excel Log Book and load into pandas DataFrame.
Supports reading individual Excel files or scanning an entire directory of monthly Log books.
Includes state tracking to skip previously processed files.
"""

import os
import glob
import json
import re
import warnings
from datetime import datetime, date
import pandas as pd
import numpy as np
import config

# Suppress openpyxl UserWarnings regarding Data Validation extensions
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'march': 3, 'apr': 4, 'may': 5,
    'jun': 6, 'june': 6, 'jul': 7, 'july': 7, 'aug': 8, 'sep': 9,
    'oct': 10, 'nov': 11, 'dec': 12
}


def infer_year_month_from_fname(fname: str):
    """Infers (year, month) from file name, e.g. 'march 2026' -> (2026, 3)."""
    fname_lower = fname.lower()
    m_num = None
    for m_str, num in MONTH_MAP.items():
        if m_str in fname_lower:
            m_num = num
            break
    y_match = re.search(r'202\d', fname)
    y_num = int(y_match.group(0)) if y_match else 2026
    return y_num, m_num


def load_sync_state() -> dict:
    """Loads the sync state dictionary from sync_state.json."""
    if os.path.exists(config.SYNC_STATE_FILE):
        try:
            with open(config.SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[State] Warning: Failed to read sync_state.json ({e}). Starting fresh.")
    return {"processed_files": {}, "last_sync_timestamp": None}


def save_sync_state(state: dict):
    """Saves the sync state dictionary to sync_state.json."""
    try:
        with open(config.SYNC_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        print("[State] Sync state successfully saved.")
    except Exception as e:
        print(f"[State] Error saving sync_state.json: {e}")


def parse_sheet_data(df_sheet: pd.DataFrame, sheet_name: str, file_name: str = "") -> pd.DataFrame:
    """
    Parses a single day's sheet from Line 2 Log Book.
    Extracts Date, Time, Kappa, Viscosity, Brightness, and pH values.
    """
    # Check if sheet has enough columns (Col AD is index 29)
    max_required_col = max([
        config.COL_TIME, config.COL_KAPPA_PRESS1, config.COL_KAPPA_PRESS3, config.COL_KAPPA_EOP,
        config.COL_VISC_PRESS1, config.COL_VISC_PRESS3, config.COL_VISC_D0, config.COL_VISC_EOP,
        config.COL_VISC_D1, config.COL_VISC_D2, config.COL_BRIGHT_PRESS1, config.COL_BRIGHT_PRESS3,
        config.COL_BRIGHT_D0, config.COL_BRIGHT_EOP, config.COL_BRIGHT_D1, config.COL_BRIGHT_D2,
        config.COL_PH_D0, config.COL_PH_EOP, config.COL_PH_D1, config.COL_PH_D2
    ])

    if df_sheet.shape[1] <= max_required_col:
        return pd.DataFrame()

    records = []
    
    # 1. Extract Date from sheet_name + file_name to prevent copy-paste date errors in Cell B4
    date_str = None
    base_date = None

    y_fname, m_fname = infer_year_month_from_fname(file_name)
    if sheet_name.isdigit():
        day_num = int(sheet_name)
        if y_fname and m_fname:
            try:
                base_date = date(y_fname, m_fname, day_num)
            except ValueError:
                base_date = None

    # Fallback to header inspection if filename inference didn't work
    if not base_date:
        for r in range(1, 6):
            if r < len(df_sheet):
                val = df_sheet.iloc[r, config.COL_TIME]
                if pd.notna(val):
                    if isinstance(val, pd.Timestamp):
                        base_date = val.to_pydatetime().date()
                        break
                    elif isinstance(val, datetime):
                        base_date = val.date()
                        break
                    elif isinstance(val, date):
                        base_date = val
                        break
                    else:
                        sval = str(val).strip()
                        for dfmt in ['%d-%m-%y', '%d-%m-%Y', '%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                base_date = datetime.strptime(sval[:10], dfmt).date()
                                break
                            except ValueError:
                                pass
                        if base_date:
                            break

    # If base_date wasn't found or month mismatches file name, infer from sheet name and file name
    y_fname, m_fname = infer_year_month_from_fname(file_name)
    if sheet_name.isdigit():
        day_num = int(sheet_name)
        if base_date:
            # Check for copy-paste month mismatch in Excel
            if m_fname and base_date.month != m_fname:
                try:
                    base_date = date(y_fname or base_date.year, m_fname, day_num)
                except ValueError:
                    pass
        else:
            if y_fname and m_fname:
                try:
                    base_date = date(y_fname, m_fname, day_num)
                except ValueError:
                    base_date = None

    if base_date:
        date_str = base_date.strftime("%Y-%m-%d")

    # 2. Iterate through hourly rows starting from row 7 (index 6)
    start_idx = config.EXCEL_DATA_START_ROW - 1  # 6
    max_idx = min(len(df_sheet), config.EXCEL_DATA_END_ROW)

    for r in range(start_idx, max_idx):
        row = df_sheet.iloc[r]
        time_raw = row.iloc[config.COL_TIME]

        if pd.isna(time_raw):
            continue

        time_str = str(time_raw).strip()
        t_obj = None

        if isinstance(time_raw, (datetime, pd.Timestamp)):
            t_obj = time_raw.time()
            time_str = t_obj.strftime("%H:%M:%S")
        elif hasattr(time_raw, "hour"):  # datetime.time object
            t_obj = time_raw
            time_str = t_obj.strftime("%H:%M:%S")
        else:
            if not ("AM" in time_str.upper() or "PM" in time_str.upper() or ":" in time_str):
                continue
            for tfmt in ["%I:%M %p", "%H:%M", "%H:%M:%S", "%I:%M:%S %p"]:
                try:
                    t_obj = datetime.strptime(time_str, tfmt).time()
                    break
                except ValueError:
                    pass

        # Extract parameters
        kappa_press1 = pd.to_numeric(row.iloc[config.COL_KAPPA_PRESS1], errors='coerce')
        kappa_press3 = pd.to_numeric(row.iloc[config.COL_KAPPA_PRESS3], errors='coerce')
        kappa_eop = pd.to_numeric(row.iloc[config.COL_KAPPA_EOP], errors='coerce')

        visc_press1 = pd.to_numeric(row.iloc[config.COL_VISC_PRESS1], errors='coerce')
        visc_press3 = pd.to_numeric(row.iloc[config.COL_VISC_PRESS3], errors='coerce')
        visc_d0 = pd.to_numeric(row.iloc[config.COL_VISC_D0], errors='coerce')
        visc_eop = pd.to_numeric(row.iloc[config.COL_VISC_EOP], errors='coerce')
        visc_d1 = pd.to_numeric(row.iloc[config.COL_VISC_D1], errors='coerce')
        visc_d2 = pd.to_numeric(row.iloc[config.COL_VISC_D2], errors='coerce')

        bright_press1 = pd.to_numeric(row.iloc[config.COL_BRIGHT_PRESS1], errors='coerce')
        bright_press3 = pd.to_numeric(row.iloc[config.COL_BRIGHT_PRESS3], errors='coerce')
        bright_d0 = pd.to_numeric(row.iloc[config.COL_BRIGHT_D0], errors='coerce')
        bright_eop = pd.to_numeric(row.iloc[config.COL_BRIGHT_EOP], errors='coerce')
        bright_d1 = pd.to_numeric(row.iloc[config.COL_BRIGHT_D1], errors='coerce')
        bright_d2 = pd.to_numeric(row.iloc[config.COL_BRIGHT_D2], errors='coerce')

        ph_d0 = pd.to_numeric(row.iloc[config.COL_PH_D0], errors='coerce')
        ph_eop = pd.to_numeric(row.iloc[config.COL_PH_EOP], errors='coerce')
        ph_d1 = pd.to_numeric(row.iloc[config.COL_PH_D1], errors='coerce')
        ph_d2 = pd.to_numeric(row.iloc[config.COL_PH_D2], errors='coerce')

        # Construct Timestamp
        timestamp = None
        if base_date and t_obj:
            b_date_obj = base_date.date() if isinstance(base_date, datetime) else base_date
            timestamp = datetime.combine(b_date_obj, t_obj)
        elif date_str and t_obj:
            try:
                parsed_bdate = None
                for dfmt in ["%d-%m-%y", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        parsed_bdate = datetime.strptime(date_str[:10], dfmt)
                        break
                    except ValueError:
                        pass
                if parsed_bdate:
                    timestamp = datetime.combine(parsed_bdate.date(), t_obj)
            except Exception:
                timestamp = None

        record = {
            "File_Name": file_name,
            "Sheet_Name": sheet_name,
            "Date_Str": date_str,
            "Time_Str": time_str,
            "Timestamp": timestamp,
            "Kappa_Press1": kappa_press1,
            "Kappa_Press3": kappa_press3,
            "Kappa_Eop": kappa_eop,
            "Viscosity_Press1": visc_press1,
            "Viscosity_Press3": visc_press3,
            "Viscosity_D0": visc_d0,
            "Viscosity_Eop": visc_eop,
            "Viscosity_D1": visc_d1,
            "Viscosity_D2": visc_d2,
            "Brightness_Press1": bright_press1,
            "Brightness_Press3": bright_press3,
            "Brightness_D0": bright_d0,
            "Brightness_Eop": bright_eop,
            "Brightness_D1": bright_d1,
            "Brightness_D2": bright_d2,
            "pH_D0": ph_d0,
            "pH_Eop": ph_eop,
            "pH_D1": ph_d1,
            "pH_D2": ph_d2,
        }
        records.append(record)

    return pd.DataFrame(records)


def parse_single_excel_file(file_path: str, sheet_names: list = None) -> pd.DataFrame:
    """Parses all daily log sheets in a single Excel file."""
    fname = os.path.basename(file_path)
    print(f"[Step 1] Parsing file: {fname}")
    try:
        excel_file = pd.ExcelFile(file_path)
        if sheet_names:
            target_sheets = sheet_names
        else:
            digit_sheets = [s for s in excel_file.sheet_names if s.isdigit()]
            target_sheets = digit_sheets if digit_sheets else excel_file.sheet_names

        all_dfs = []
        for sname in target_sheets:
            df_sheet = excel_file.parse(sheet_name=sname, header=None)
            df_parsed = parse_sheet_data(df_sheet, sheet_name=sname, file_name=fname)
            if not df_parsed.empty:
                all_dfs.append(df_parsed)

        if not all_dfs:
            return pd.DataFrame()

        return pd.concat(all_dfs, ignore_index=True)
    except Exception as e:
        print(f"[Step 1] Error parsing {fname}: {e}")
        return pd.DataFrame()


def fetch_onedrive_data(target_path: str = None, sheet_names: list = None, process_all_files: bool = True) -> pd.DataFrame:
    """
    Reads Excel Log book files from OneDrive folder or single file.
    If process_all_files is True, parses all monthly files in the directory for historical backfilling.
    """
    path_to_use = target_path or config.ONEDRIVE_PATH

    if not path_to_use or not os.path.exists(path_to_use):
        print(f"[Step 1] File/Folder not found: '{path_to_use}'")
        return pd.DataFrame()

    # Gather list of Excel files
    if os.path.isdir(path_to_use):
        excel_files = sorted(
            glob.glob(os.path.join(path_to_use, "*.xlsx")) + glob.glob(os.path.join(path_to_use, "*.xls"))
        )
    else:
        excel_files = [path_to_use]

    if not excel_files:
        print("[Step 1] No Excel files found in target location.")
        return pd.DataFrame()

    files_to_process = excel_files if process_all_files else [excel_files[-1]]
    print(f"[Step 1] Found {len(excel_files)} Excel file(s). Processing {len(files_to_process)} file(s)...")

    all_dfs = []
    for fpath in files_to_process:
        fname = os.path.basename(fpath)
        print(f"[Step 1] Parsing file: {fname}")
        df_file = parse_single_excel_file(fpath, sheet_names=sheet_names)
        if not df_file.empty:
            all_dfs.append(df_file)

    if not all_dfs:
        print("[Step 1] No lab measurement records found.")
        return pd.DataFrame()

    df_concat = pd.concat(all_dfs, ignore_index=True)

    # Clean data: drop rows where all lab values are NaN
    lab_cols = [c for c in df_concat.columns if c.startswith(("Kappa_", "Viscosity_", "Brightness_", "pH_"))]
    df_clean = df_concat.dropna(subset=lab_cols, how="all").reset_index(drop=True)

    print(f"[Step 1] Successfully loaded {len(df_clean)} lab measurement rows across {len(files_to_process)} file(s).")
    return df_clean


def check_lab_data(df: pd.DataFrame, query: str = "08:00:00", max_rows: int = 10):
    """
    Simple helper to inspect and verify extracted lab data by date, time, or timestamp.
    Example queries: '08:00:00', '2026-08-01', or '2026-08-01 08:00'
    """
    if df.empty:
        print("[Check] DataFrame is empty.")
        return

    # Filter by Date_Str, Time_Str, or Timestamp matching query
    mask = (
        df["Date_Str"].astype(str).str.contains(query, case=False, na=False) |
        df["Time_Str"].astype(str).str.contains(query, case=False, na=False) |
        df["Timestamp"].astype(str).str.contains(query, case=False, na=False)
    )
    result = df[mask]

    print(f"\n🔍 [Check Result] Found {len(result)} record(s) matching '{query}':")
    show_cols = ["File_Name", "Date_Str", "Time_Str", "Timestamp", "Kappa_Press1", "Viscosity_Press1", "Brightness_Press1"]
    avail_cols = [c for c in show_cols if c in df.columns]
    
    if not result.empty:
        print(result[avail_cols].head(max_rows).to_string(index=False))
    else:
        print(f"No records found matching '{query}'.")


if __name__ == "__main__":
    # Test fetch on the entire directory in dry-run mode
    df_result = fetch_onedrive_data()
    if not df_result.empty:
        print("\n[Step 1] Summary Result:")
        print(f"Total rows extracted: {len(df_result)}")
        print("Files processed:", df_result['File_Name'].value_counts().to_dict())
        
        # Simple Verify data
        check_lab_data(df_result, query="2026-08-01", max_rows=5)
    else:
        print("[Step 1] No records extracted.")

