"""
Step 0: Automated Download of Excel Log Books from SCG SharePoint Online using Playwright.
Saves downloaded files directly into ONEDRIVE_PATH before Step 1 processing.
"""

import sys
import os
import time
import glob
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

SHAREPOINT_URL = "https://scgo365.sharepoint.com/:f:/s/QAPPPC/IgBrfoSASApZTplEVNS_z03OAUdx-NJOVzDLDCYtPfJjB4I"


def download_latest_from_sharepoint(target_dir: str = None, headless: bool = False) -> bool:
    """
    Automates opening SCG SharePoint folder and downloading latest Excel logbook files.
    """
    dest_dir = target_dir or config.ONEDRIVE_PATH
    os.makedirs(dest_dir, exist_ok=True)

    print("[Step 0] Connecting to SCG SharePoint Online via Playwright...")
    print(f"[Step 0] Target Destination Folder: {dest_dir}")

    profile_dir = os.path.join(config.BASE_DIR, "temp_downloads", "scg_browser_profile")

    try:
        with sync_playwright() as p:
            # Launch persistent context
            # Use channel="chrome" or realistic user agent to pass SSO seamlessly
            browser_context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                accept_downloads=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ]
            )

            page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
            
            print("[Step 0] Navigating to SharePoint Log Book Folder...")
            page.goto(SHAREPOINT_URL, wait_until="networkidle", timeout=45000)
            time.sleep(3)

            # Check if redirected to login page
            if "login" in page.url.lower() or "signin" in page.url.lower() or "Sign in" in page.title():
                print("\n⚠️ SCG Microsoft Login required in browser window!")
                print("   Please complete login in the opened browser window within 25 seconds...")
                time.sleep(25)

            time.sleep(3)

            # Look for Excel file rows or download options
            # Strategy: Click 'Download' for the latest file or select all files to download
            download_count = 0
            
            # STRICT READ-ONLY DIRECT FILE DOWNLOAD:
            # Download file from folder view directly without opening Excel Online editor/viewer
            try:
                download_triggered = False
                time.sleep(3)
                
                # Locate file rows in SharePoint list
                rows = page.query_selector_all("div[role='row']")
                print(f"[Step 0] Found {len(rows)} row(s) on SharePoint folder page.")

                for row in rows:
                    txt = row.inner_text()
                    if "Aug 2026" in txt or "8.LINE" in txt:
                        print(f"[Step 0] Found target file row: '{txt[:50].strip()}...'")
                        
                        # Strategy A: Right-click row to open context menu and click Download
                        try:
                            row.click(button="right")
                            time.sleep(1)
                            context_dl = page.query_selector("button[name='Download'], button[aria-label*='Download'], span:has-text('Download')")
                            if context_dl:
                                print("[Step 0] Clicking 'Download' from context menu...")
                                with page.expect_download(timeout=35000) as download_info:
                                    context_dl.click()
                                download = download_info.value
                                save_file_path = os.path.join(dest_dir, download.suggested_filename)
                                download.save_as(save_file_path)
                                print(f"[Step 0] ✅ READ-ONLY DOWNLOAD SUCCESS: Saved '{download.suggested_filename}' ({os.path.getsize(save_file_path)} bytes)")
                                download_triggered = True
                                break
                        except Exception as e_ctx:
                            print(f"[Step 0] Context menu trigger note: {e_ctx}")

                        # Strategy B: Select row checkbox and click top bar Download button
                        if not download_triggered:
                            checkbox = row.query_selector("div[role='checkbox'], i[data-icon-name='CheckMark']")
                            if checkbox:
                                checkbox.click()
                            else:
                                row.click()
                            time.sleep(1.5)

                            dl_btn = page.query_selector("button[data-automation-id='downloadCommand']")
                            if dl_btn:
                                print("[Step 0] Clicking 'Download' from command bar...")
                                with page.expect_download(timeout=35000) as download_info:
                                    dl_btn.click()
                                download = download_info.value
                                save_file_path = os.path.join(dest_dir, download.suggested_filename)
                                download.save_as(save_file_path)
print(f"[Step 0] [SUCCESS] Saved '{download.suggested_filename}' ({os.path.getsize(save_file_path)} bytes)")
                            download_triggered = True
                            break

                if not download_triggered:
                    print("[Step 0] Retrying folder command bar download...")
                    dl_top = page.query_selector("button[data-automation-id='downloadCommand']")
                    if dl_top:
                        with page.expect_download(timeout=35000) as download_info:
                            dl_top.click()
                        download = download_info.value
                        save_file_path = os.path.join(dest_dir, download.suggested_filename)
                        download.save_as(save_file_path)
                        print(f"[Step 0] [SUCCESS] Saved '{download.suggested_filename}' ({os.path.getsize(save_file_path)} bytes)")

            except Exception as e_dl:
                print(f"[Step 0] Note during automatic download trigger: {e_dl}")

            browser_context.close()

            # Verify downloaded files in destination
            files_in_dest = glob.glob(os.path.join(dest_dir, "*.xlsx")) + glob.glob(os.path.join(dest_dir, "*.xls"))
            if files_in_dest:
                print(f"[Step 0] Total {len(files_in_dest)} Excel file(s) available in '{dest_dir}'.")
                return True
            else:
                print("[Step 0] Warning: No Excel files in destination directory.")
                return False

    except Exception as e:
        print(f"[Step 0] Exception during SharePoint fetch: {e}")
        return False


if __name__ == "__main__":
    download_latest_from_sharepoint(headless=False)
