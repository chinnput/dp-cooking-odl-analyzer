"""
Main Orchestrator: OneDrive / SharePoint to PI Sync Pipeline.
Executes Step 0 -> Step 1 -> Step 2 -> Step 3 sequentially.

Supported Execution Modes:
1. mode="hourly"   : Real-time automation mode. Fetches latest logbook from SharePoint & checks for new hourly lab updates.
2. mode="backfill" : Historical mode. Parses all monthly Excel files and pushes historical records.

Dry-Run Toggle:
- dry_run=True  : Test Preview mode (prints log preview to terminal, NO live API requests).
- dry_run=False : Live Production mode (sends HTTP POST requests to write_old API endpoint).
"""

import config
from step0_download_sharepoint import download_latest_from_sharepoint
from step1_fetch_onedrive import fetch_onedrive_data
from step2_time_matching import process_lab_data
from step3_pi_api_client import prepare_pi_payloads, push_to_pi_server


def run_pipeline(mode: str = "hourly", dry_run: bool = True, auto_download_sharepoint: bool = True):
    print("=" * 70)
    print(f"=== Starting OneDrive / SharePoint to PI Sync Pipeline (Mode: '{mode.upper()}') ===")
    print(f"Execution Type : {'Dry-Run (Test Preview)' if dry_run else 'Live Production'}")
    print(f"Target API     : {config.WRITE_OLD_API_URL}")
    print("=" * 70)

    # Step 0: Auto-Download latest logbook from SharePoint Online if enabled
    if auto_download_sharepoint:
        print("\n--- [Step 0] Auto-Fetching Latest Logbook from SCG SharePoint Online ---")
        download_latest_from_sharepoint(headless=True)

    # Step 1: Fetch data from Excel Log Book files
    print("\n--- [Step 1] Reading and Extracting Excel Log Book Data ---")
    process_all = (mode == "backfill")
    df_raw = fetch_onedrive_data(process_all_files=process_all)

    if df_raw.empty:
        print("[Pipeline] No lab data found in Excel files. Pipeline finished.")
        return

    # Step 2: Filter and process lab measurements based on mode
    print("\n--- [Step 2] Filtering and Sorting Lab Measurements ---")
    df_proc = process_lab_data(df_raw, mode=mode)

    if df_proc.empty:
        print("[Pipeline] No lab records to send in this cycle. Pipeline finished.")
        return

    # Extract latest timestamp in this processed batch
    latest_timestamp = df_proc["Timestamp"].max()

    # Step 3: Prepare payloads and push to PI Server via write_old API
    print("\n--- [Step 3] Formatting Payloads and Pushing to PI Server Gateway ---")
    payloads = prepare_pi_payloads(df_proc)

    if payloads:
        success = push_to_pi_server(payloads, dry_run=dry_run, latest_timestamp=latest_timestamp)
        if success:
            print(f"\n=== Pipeline Completed Successfully (Processed {len(payloads)} records, Latest TS: {latest_timestamp}) ===")
        else:
            print("\n=== Pipeline Completed with Errors ===")
    else:
        print("[Pipeline] No payloads generated. Pipeline finished.")


if __name__ == "__main__":
    # EASY TOGGLE FOR TESTING & RUNNING:
    # -----------------------------------------------------------------------------------
    # Option A (Test Hourly Preview)    : run_pipeline(mode="hourly", dry_run=True)
    # Option B (Test Backfill Preview)  : run_pipeline(mode="backfill", dry_run=True)
    # Option C (Live Hourly Automation) : run_pipeline(mode="hourly", dry_run=False)
    # Option D (Live Backfill Run)     : run_pipeline(mode="backfill", dry_run=False)
    # -----------------------------------------------------------------------------------

    run_pipeline(mode="hourly", dry_run=False)




