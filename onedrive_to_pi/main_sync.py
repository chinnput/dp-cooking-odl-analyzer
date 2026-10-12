"""
Main Orchestrator: OneDrive / SharePoint to PI Sync Pipeline.
Executes Step 0 -> Step 1 -> Step 2 -> Step 3 sequentially.

Supported Execution Modes:
1. mode="hourly"        : Real-time automation mode. Checks for new hourly lab updates.
2. mode="new_tags_only" : Fast backfill for 6 NEW tags only (pH & Brightness D1/D2) across history.
3. mode="backfill"      : Complete historical backfill for ALL 19 tags across all files.

Dry-Run Toggle:
- dry_run=True  : Test Preview mode (prints log preview to terminal, NO live API requests).
- dry_run=False : Live Production mode (sends HTTP POST requests to write_old API endpoint).
"""

import time
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
        # headless=False so SSO/MFA login is visible; persistent profile reuses the session next time.
        download_latest_from_sharepoint(headless=False, login_wait_seconds=300)

    # Step 1: Fetch data from Excel Log Book files
    print("\n--- [Step 1] Reading and Extracting Excel Log Book Data ---")
    process_all = (mode in ("backfill", "new_tags_only"))
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

    # Display preview sample of new records found (5 to 10 rows)
    show_count = min(10, len(df_proc))
    print(f"\n🔍 [New Data Found] Sample preview of new lab record(s) ({show_count} of {len(df_proc)} rows):")
    show_cols = ["File_Name", "Date_Str", "Time_Str", "Timestamp", "Kappa_Press1", "Viscosity_Press1", "Brightness_Press1"]
    avail_cols = [c for c in show_cols if c in df_proc.columns]
    print(df_proc[avail_cols].head(show_count).to_string(index=False))

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


def run_continuous_loop(interval_seconds: int = 3600, dry_run: bool = False):
    """
    Runs the pipeline continuously in an infinite loop for CMD background automation.
    Waits interval_seconds (default 1 hour = 3600s) between execution cycles.
    """
    cycle = 1
    while True:
        print("\n" + "=" * 70)
        print(f" HOURLY SYNC CYCLE #{cycle} STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            run_pipeline(mode="hourly", dry_run=dry_run)
        except Exception as e:
            print(f"❌ Exception in cycle #{cycle}: {e}")

        print("\n" + "-" * 70)
        print(f" Cycle #{cycle} completed. Waiting {interval_seconds // 60} minutes ({interval_seconds}s) until next check...")
        print("   (Press Ctrl+C anytime in this window to stop the service)")
        print("-" * 70 + "\n")
        
        time.sleep(interval_seconds)
        cycle += 1


if __name__ == "__main__":
    import sys
    
    # If called with --loop argument from .bat file, run continuous hourly loop
    if "--loop" in sys.argv or "-l" in sys.argv:
        # Check if dry_run flag is passed
        is_dry = "--dry-run" in sys.argv
        run_continuous_loop(interval_seconds=3600, dry_run=is_dry)
    else:
        # Single execution run for testing / manual invocation
        run_pipeline(mode="hourly", dry_run=False)




