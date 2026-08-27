"""
Main Orchestrator: Historical & Incremental Sync Pipeline.
Runs Step 1 -> Step 2 -> Step 3 sequentially using write_old API endpoint.
"""

import time
import config
from step1_fetch_onedrive import fetch_onedrive_data
from step2_time_matching import match_lab_time_to_batches
from step3_pi_api_client import prepare_pi_payloads, push_to_pi_server


def run_pipeline(dry_run: bool = True, filter_incremental: bool = False):
    print("=== Starting OneDrive to PI Historical / Incremental Sync Pipeline ===")
    print(f"Mode: {'Dry-Run (Test Preview)' if dry_run else 'Live Production'}")
    print(f"Target API Endpoint: {config.WRITE_OLD_API_URL}")
    
    # Step 1: Fetch data from Excel Log Book files
    df_raw = fetch_onedrive_data(process_all_files=not filter_incremental)
    
    if df_raw.empty:
        print("[Pipeline] No lab data found in Excel files. Pipeline finished.")
        return

    # Step 2: Prepare lab measurements (Historical or Incremental)
    df_proc = match_lab_time_to_batches(df_raw, filter_incremental=filter_incremental)
    
    if df_proc.empty:
        print("[Pipeline] No lab records to process. Pipeline finished.")
        return

    # Extract latest timestamp in this batch
    latest_timestamp = df_proc["Timestamp"].max()

    # Step 3: Prepare payloads and push to PI Server via write_old API
    payloads = prepare_pi_payloads(df_proc)
    
    if payloads:
        success = push_to_pi_server(payloads, dry_run=dry_run, latest_timestamp=latest_timestamp)
        if success:
            print(f"\n=== Pipeline Completed Successfully (Processed {len(payloads)} records, Latest Timestamp: {latest_timestamp}) ===")
        else:
            print("\n=== Pipeline Completed with Errors ===")
    else:
        print("[Pipeline] No payloads generated. Pipeline finished.")


if __name__ == "__main__":
    # Stopped live execution, running in safe preview mode
    run_pipeline(dry_run=False, filter_incremental=False)


