# Read the real Press 1 lab samples straight from the log book Excel files (read only).
# Own reader - Digester_Analysis does not import code from any other folder.
#
# File layout (Line 2 log book):
#   one file per month, the month/year is in the file name, e.g. "10. LINE NO.2_Log Sheet_ in Oct 2026.xlsx"
#   one sheet per day, named "1" .. "31"
#   hourly rows from Excel row 7; column B = time; lab columns in config.LOG_BOOK_LAB_COLUMNS
#   a sheet runs 08:00 -> 07:00 the next morning, so times before 08:00 belong to the next date

import glob
import os
import re
import warnings
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

import config

# The log book uses an Excel data-validation feature openpyxl cannot read; harmless, so hide the warning
warnings.filterwarnings("ignore", message="Data Validation extension", category=UserWarning)

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def year_month_from_name(file_name):
    """'10. LINE NO.2_Log Sheet_ in Oct 2026.xlsx' -> (2026, 10). None if no month name is found."""
    name = file_name.lower()
    for text, month in MONTHS.items():
        position = name.find(text)
        if position != -1:
            # the year right after the month name ("JAN 2026"), otherwise the last year in the name
            after = re.search(r"20\d\d", name[position:])
            years = re.findall(r"20\d\d", name)
            year = int(after.group(0)) if after else (int(years[-1]) if years else None)
            return (year, month) if year else None
    return None


def pick_files(folder):
    """One file per (year, month): if there are several copies of a month, take the newest one."""
    files = glob.glob(os.path.join(folder, "*.xlsx")) + glob.glob(os.path.join(folder, "*.tmp"))
    newest = {}
    for path in files:
        year_month = year_month_from_name(os.path.basename(path))
        if year_month is None:
            continue
        if year_month not in newest or os.path.getmtime(path) > os.path.getmtime(newest[year_month]):
            newest[year_month] = path
    return [(ym, newest[ym]) for ym in sorted(newest)]


def to_time(value):
    """Excel time cell -> datetime.time (accepts time objects and text like '8:00 AM', '13:00')."""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.time()
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S", "%I:%M:%S %p"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            pass
    return None


def read_sheet(sheet, sheet_date):
    """All hourly rows of one day sheet: timestamp + the lab columns."""
    rows = []
    last_row = min(config.LOG_BOOK_LAST_ROW, len(sheet))
    for r in range(config.LOG_BOOK_FIRST_ROW - 1, last_row):
        t = to_time(sheet.iat[r, config.LOG_BOOK_TIME_COLUMN])
        if t is None:
            continue
        day = sheet_date + timedelta(days=1) if t.hour < config.LOG_BOOK_DAY_STARTS_HOUR else sheet_date
        row = {"timestamp": datetime.combine(day, t)}
        for name, col in config.LOG_BOOK_LAB_COLUMNS.items():
            row[name] = pd.to_numeric(sheet.iat[r, col], errors="coerce") if col < sheet.shape[1] else np.nan
        rows.append(row)
    return rows


def read_log_books(folder=None):
    """
    Read every monthly log book in `folder` (default config.LOG_BOOK_DIR).
    Returns one row per sample time (index 'timestamp') with the lab columns; rows without any value are dropped.
    """
    folder = folder or config.LOG_BOOK_DIR
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Log book folder not found: {folder} (set LOG_BOOK_DIR in config.py)")

    rows = []
    for (year, month), path in pick_files(folder):
        print(f"Reading {os.path.basename(path)}")
        excel = pd.ExcelFile(path, engine="openpyxl")
        for sheet_name in excel.sheet_names:
            if not sheet_name.strip().isdigit():
                continue
            try:
                sheet_date = date(year, month, int(sheet_name))
            except ValueError:            # e.g. sheet "31" in a 30-day month
                continue
            rows += read_sheet(excel.parse(sheet_name, header=None), sheet_date)

    lab = pd.DataFrame(rows)
    lab = lab.dropna(subset=list(config.LOG_BOOK_LAB_COLUMNS), how="all")
    lab = lab.drop_duplicates("timestamp", keep="last").set_index("timestamp").sort_index()
    return lab
