"""
Step 0: Automated Download of Excel Log Books from SCG SharePoint Online using Playwright.
Saves downloaded files directly into ONEDRIVE_PATH before Step 1 processing.
"""

import sys
import os
import re
import time
import glob
from playwright.sync_api import sync_playwright

# Force UTF-8 stdout so emoji/unicode logs don't crash on Windows cp874/charmap consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

SHAREPOINT_URL = "https://scgo365.sharepoint.com/:f:/s/QAPPPC/IgBrfoSASApZTplEVNS_z03OAUdx-NJOVzDLDCYtPfJjB4I"


def _safe_save_download(download, dest_dir: str, retries: int = 5, delay: float = 1.5) -> str:
    """
    Saves a Playwright download robustly even if the target file is locked by
    Excel/OneDrive. Uses a unique temp name, then retries os.replace().
    Returns the final saved path (main file, or the unique temp file as fallback).
    """
    suggested = download.suggested_filename
    final_path = os.path.join(dest_dir, suggested)
    # Unique temp name avoids clashing with a locked leftover .tmp from a prior run.
    unique_tmp = os.path.join(dest_dir, f"{suggested}.{os.getpid()}.{int(time.time())}.tmp")

    download.save_as(unique_tmp)

    for attempt in range(1, retries + 1):
        try:
            if os.path.exists(final_path):
                try:
                    os.remove(final_path)
                except PermissionError:
                    # Main file is locked (likely open in Excel / syncing). Wait and retry.
                    print(f"[Step 0] Target file locked, retry {attempt}/{retries} in {delay}s... "
                          f"(close '{suggested}' in Excel/OneDrive if open)")
                    time.sleep(delay)
                    continue
            os.replace(unique_tmp, final_path)
            return final_path
        except PermissionError:
            print(f"[Step 0] Replace failed (locked), retry {attempt}/{retries} in {delay}s...")
            time.sleep(delay)

    # All retries failed: keep the unique temp file so data isn't lost; Step 1 can still read .tmp.
    print(f"[Step 0] Could not replace locked main file. Keeping fresh copy: '{os.path.basename(unique_tmp)}'")
    return unique_tmp


def _is_login_page(page) -> bool:
    """Returns True if the current page looks like a Microsoft sign-in page."""
    try:
        url = (page.url or "").lower()
        title = (page.title() or "").lower()
    except Exception:
        return False

    login_url_markers = ("login.microsoftonline.com", "login.live.com", "/login", "signin", "adfs", "sts")
    if any(m in url for m in login_url_markers):
        return True
    if "sign in" in title:
        return True

    # Presence of typical sign-in fields
    try:
        if page.query_selector("input[type='email'], input[name='loginfmt'], input[type='password']"):
            return True
    except Exception:
        pass
    return False


def _wait_for_login(page, timeout_seconds: int = 300, poll_seconds: int = 3) -> bool:
    """Polls until the page is no longer a login page (login completed) or timeout."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _is_login_page(page):
            # Give SharePoint a moment to finish loading the folder view
            time.sleep(3)
            if not _is_login_page(page):
                return True
        remaining = int(deadline - time.time())
        print(f"[Step 0] Waiting for login to complete... ({remaining}s left)")
        time.sleep(poll_seconds)
    return False


def download_latest_from_sharepoint(target_dir: str = None, headless: bool = False, login_wait_seconds: int = 300) -> bool:
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

            # Wait until the user completes SSO/MFA login instead of a fixed short sleep.
            if _is_login_page(page):
                if headless:
                    print("[Step 0] Login required but browser is headless. Re-run with headless=False to sign in.")
                    browser_context.close()
                    return False

                print("=" * 60)
                print("[Step 0] SCG Microsoft Login required in the opened browser window.")
                print(f"[Step 0] Please complete sign-in (including MFA). Waiting up to {login_wait_seconds}s...")
                print("=" * 60)

                if not _wait_for_login(page, timeout_seconds=login_wait_seconds):
                    print("[Step 0] Login not detected within the allotted time. Aborting.")
                    browser_context.close()
                    return False

                print("[Step 0] Login detected. Continuing to folder view...")

            time.sleep(3)

            # Look for Excel file rows or download options
            # Strategy: Click 'Download' for the latest file or select all files to download
            download_count = 0
            
            # STRICT READ-ONLY DIRECT FILE DOWNLOAD:
            # Download file from folder view directly without opening Excel Online editor/viewer
            try:
                download_triggered = False
                time.sleep(3)
                
                # Locate file rows in SharePoint list (.xlsx / .xls files)
                rows = page.query_selector_all("div[role='row']")
                print(f"[Step 0] Found {len(rows)} row(s) on SharePoint folder page.")

                # Filter rows that represent Excel logbook files
                excel_rows = []
                for row in rows:
                    txt = row.inner_text()
                    if (".xlsx" in txt or ".xls" in txt or "Log Sheet" in txt) and "LINE" in txt:
                        excel_rows.append((row, txt))

                if excel_rows:
                    # Pick the latest logbook file row (highest month number / newest file)
                    # Score by the leading file-number prefix (e.g. "9." = September) to avoid
                    # matching month words inside notes/comments in the row text.
                    def get_row_month_score(row_tuple):
                        row_txt = row_tuple[1]
                        m = re.search(r'(\d{1,2})\s*\.?\s*LINE', row_txt, re.IGNORECASE)
                        if m:
                            return int(m.group(1))
                        # Fallback: match month keyword only in the filename part (before ".xlsx")
                        fname_part = row_txt.split(".xlsx")[0].lower()
                        for m_str, m_num in [
                            ('dec', 12), ('nov', 11), ('oct', 10), ('sep', 9), ('aug', 8),
                            ('jul', 7), ('jun', 6), ('may', 5), ('apr', 4), ('mar', 3), ('feb', 2), ('jan', 1)
                        ]:
                            if m_str in fname_part:
                                return m_num
                        return 0

                    excel_rows.sort(key=get_row_month_score, reverse=True)
                    target_row, target_txt = excel_rows[0]
                    print(f"[Step 0] Selected latest logbook row: '{target_txt[:50].strip()}...'")

                    # Strategy A: Right-click row to open context menu and click Download
                    try:
                        target_row.click(button="right")
                        time.sleep(1)
                        context_dl = page.query_selector("button[name='Download'], button[aria-label*='Download'], span:has-text('Download')")
                        if context_dl:
                            print("[Step 0] Clicking 'Download' from context menu...")
                            with page.expect_download(timeout=35000) as download_info:
                                context_dl.click()
                            download = download_info.value
                            final_path = _safe_save_download(download, dest_dir)
                            print(f"[Step 0] READ-ONLY DOWNLOAD SUCCESS: Saved '{os.path.basename(final_path)}' ({os.path.getsize(final_path)} bytes)")
                            download_triggered = True
                    except Exception as e_ctx:
                        print(f"[Step 0] Context menu trigger note: {e_ctx}")

                    # Strategy B: Select row checkbox and click top bar Download button
                    if not download_triggered:
                        checkbox = target_row.query_selector("div[role='checkbox'], i[data-icon-name='CheckMark']")
                        if checkbox:
                            checkbox.click()
                        else:
                            target_row.click()
                        time.sleep(1.5)

                        dl_btn = page.query_selector("button[data-automation-id='downloadCommand']")
                        if dl_btn:
                            print("[Step 0] Clicking 'Download' from command bar...")
                            with page.expect_download(timeout=35000) as download_info:
                                dl_btn.click()
                            download = download_info.value
                            final_path = _safe_save_download(download, dest_dir)
                            print(f"[Step 0] READ-ONLY DOWNLOAD SUCCESS: Saved '{os.path.basename(final_path)}' ({os.path.getsize(final_path)} bytes)")
                            download_triggered = True

                if not download_triggered:
                    print("[Step 0] Retrying folder command bar download...")
                    dl_top = page.query_selector("button[data-automation-id='downloadCommand']")
                    if dl_top:
                        with page.expect_download(timeout=35000) as download_info:
                            dl_top.click()
                        download = download_info.value
                        final_path = _safe_save_download(download, dest_dir)
                        print(f"[Step 0] [SUCCESS] Saved '{os.path.basename(final_path)}' ({os.path.getsize(final_path)} bytes)")

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
