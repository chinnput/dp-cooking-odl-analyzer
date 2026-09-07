import sys
import os
import time
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

url = "https://scgo365.sharepoint.com/:f:/s/QAPPPC/IgBrfoSASApZTplEVNS_z03OAUdx-NJOVzDLDCYtPfJjB4I"
profile_dir = os.path.join(config.BASE_DIR, "temp_downloads", "scg_browser_profile")
lock_file = os.path.join(profile_dir, "SingletonLock")
if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
    except Exception:
        pass

"""
Standalone Test Script: Download Latest Excel File from SCG SharePoint Online.
Opens a visible Chrome browser window (headless=False) using Playwright.
"""

import sys
import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

SHAREPOINT_URL = "https://scgo365.sharepoint.com/:f:/s/QAPPPC/IgBrfoSASApZTplEVNS_z03OAUdx-NJOVzDLDCYtPfJjB4I"

def test_sharepoint_download():
    print("=" * 70)
    print("      TESTING SHAREPOINT FILE DOWNLOAD (VISIBLE BROWSER)")
    print("=" * 70)
    print(f"Target Directory: {config.ONEDRIVE_PATH}")
    print(f"SharePoint URL  : {SHAREPOINT_URL}")
    print("-" * 70)

    profile_dir = os.path.join(config.BASE_DIR, "temp_downloads", "scg_browser_profile")
    
    # Clean lock file if leftover from previous run
    lock_file = os.path.join(profile_dir, "SingletonLock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except Exception:
            pass

    with sync_playwright() as p:
        print("[1/4] Opening Chrome browser window...")
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # Visible browser
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        
        print("[2/4] Navigating to SharePoint folder...")
        page.goto(SHAREPOINT_URL, wait_until="networkidle", timeout=45000)
        time.sleep(4)

        print(f"Page Title: {page.title()}")

        # Check for login prompt
        if "login" in page.url.lower() or "signin" in page.url.lower() or "Sign in" in page.title():
            print("\n⚠️ Login Required: Please sign in to SCG account in the opened browser window...")
            time.sleep(20)

        print("[3/4] Locating August 2026 Log Book file row...")
        time.sleep(3)

        # Locate file rows
        download_success = False
        rows = page.query_selector_all("div[role='row']")
        
        for row in rows:
            txt = row.inner_text()
            if "Aug 2026" in txt or "8.LINE" in txt:
                print(f"Found row: '{txt[:60]}...'")
                
                # Step A: Click on the row text / checkbox to highlight it
                row.click()
                time.sleep(2)

                # Step B: Look for Download button on top bar or context menu
                dl_btn = page.query_selector("button[data-automation-id='downloadCommand'], button[aria-label*='Download'], button[title*='Download']")
                
                if dl_btn:
                    print("Found 'Download' button! Clicking to trigger browser download...")
                    try:
                        with page.expect_download(timeout=35000) as download_info:
                            dl_btn.click()
                        download = download_info.value
                        dest_file = os.path.join(config.ONEDRIVE_PATH, download.suggested_filename)
                        download.save_as(dest_file)
                        print(f"\n🎉 ✅ DOWNLOAD SUCCESSFUL!")
                        print(f"File Saved To : {dest_file}")
                        print(f"Downloaded Size: {os.path.getsize(dest_file)} bytes")
                        download_success = True
                        break
                    except Exception as e_dl:
                        print(f"Download trigger error: {e_dl}")
                else:
                    print("⚠️ Top Download button not visible. Trying right click context menu...")
                    row.click(button="right")
                    time.sleep(1)
                    ctx_dl = page.query_selector("button[name='Download'], span:has-text('Download')")
                    if ctx_dl:
                        print("Clicking Download in context menu...")
                        with page.expect_download(timeout=35000) as download_info:
                            ctx_dl.click()
                        download = download_info.value
                        dest_file = os.path.join(config.ONEDRIVE_PATH, download.suggested_filename)
                        download.save_as(dest_file)
                        print(f"\n🎉 ✅ DOWNLOAD SUCCESSFUL!")
                        print(f"File Saved To : {dest_file}")
                        print(f"Downloaded Size: {os.path.getsize(dest_file)} bytes")
                        download_success = True
                        break

        if not download_success:
            print("⚠️ Could not trigger automatic click. Opening file viewer or waiting for manual click...")
            print("You can manually click Download in the opened Chrome window if needed.")
            time.sleep(10)

        browser_context.close()

    print("\n[4/4] Verifying downloaded Excel file contents...")
    aug_file = os.path.join(config.ONEDRIVE_PATH, "8.LINE NO.2_Log Sheet_ in Aug 2026.xlsx")
    if os.path.exists(aug_file):
        xl = pd.ExcelFile(aug_file)
        print(f"Excel file size : {os.path.getsize(aug_file)} bytes")
        print(f"Total Sheets    : {len(xl.sheet_names)}")
        # Check sheet 28 / 29 / 30 / 31
        import step1_fetch_onedrive
        for s in ["28", "29", "30", "31"]:
            if s in xl.sheet_names:
                df_s = xl.parse(s, header=None)
                df_p = step1_fetch_onedrive.parse_sheet_data(df_s, s, "8.LINE NO.2_Log Sheet_ in Aug 2026.xlsx")
                print(f"Sheet '{s}' non-empty rows: {len(df_p)}")
                if not df_p.empty:
                    print(df_p[["Date_Str", "Time_Str", "Kappa_Press1", "Viscosity_Press1"]].dropna(how="all").head(3))
    print("=" * 70)


if __name__ == "__main__":
    test_sharepoint_download()

