"""
Playwright Chrome Automation Test Script for SCG SharePoint File Download.
Uses Chrome user profile to reuse active SCG SSO login session.
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

# SCG SharePoint Target URL
SHAREPOINT_URL = "https://scgo365.sharepoint.com/:f:/s/QAPPPC/IgBrfoSASApZTplEVNS_z03OAUdx-NJOVzDLDCYtPfJjB4I"

# Output download directory
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# User's Chrome Profile directory
USER_HOME = os.path.expanduser("~")
CHROME_USER_DATA_DIR = os.path.join(USER_HOME, "AppData", "Local", "Google", "Chrome", "User Data")


def test_playwright_sharepoint_download():
    print("=" * 70)
    print("      PLAYWRIGHT CHROME AUTOMATION SHAREPOINT DOWNLOAD TEST")
    print("=" * 70)
    print(f"SharePoint URL  : {SHAREPOINT_URL}")
    print(f"Download Dir    : {DOWNLOAD_DIR}")
    print("-" * 70)

    # Use a dedicated profile directory so it doesn't conflict with open Chrome windows
    profile_dir = os.path.join(DOWNLOAD_DIR, "scg_browser_profile")

    with sync_playwright() as p:
        print("[1/3] Launching Browser for SCG SharePoint...")
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # Headless=False allows user to complete SSO login if required
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        
        print("[2/3] Navigating to SCG SharePoint Log Book Folder...")
        page.goto(SHAREPOINT_URL, wait_until="networkidle", timeout=45000)
        
        time.sleep(3)
        print(f"Current Page Title : {page.title()}")

        # Check if redirected to login page
        if "login" in page.url.lower() or "signin" in page.url.lower() or "Sign in" in page.title():
            print("\n⚠️ SCG Microsoft Login required in open browser window!")
            print("   Please complete login in the opened browser window within 30 seconds...")
            time.sleep(25)

        print("\n[3/3] Scanning folder items on SharePoint page...")
        time.sleep(5)
        
        elements = page.query_selector_all("span[data-automation-id='name'], button[data-automation-id='name'], div[role='row']")
        found_names = []
        for e in elements:
            txt = e.inner_text().strip()
            if txt and (txt.endswith((".xlsx", ".xls")) or "Log Sheet" in txt or "Log book" in txt):
                found_names.append(txt)

        if found_names:
            print(f"✅ SUCCESS! Discovered {len(found_names)} item(s) on SharePoint page:")
            for fn in set(found_names):
                print(f"  📄 {fn}")
        else:
            print(f"ℹ️ Page loaded (Title: '{page.title()}'). Check browser window to verify folder view.")

        print("=" * 70)
        browser_context.close()


if __name__ == "__main__":
    test_playwright_sharepoint_download()
