"""
Safe Read-Only Test Script: Querying SCG SharePoint REST API for Log Book Files.
Target Folder: /sites/QAPPPC/Shared Documents/QA PPPC/QA Pulp/Log book Pulp/2026/Log book Pulp Line 2 - 2026
This script is completely read-only and does NOT mutate or overwrite any files.
"""

import os
import sys
import requests
import json

SITE_URL = "https://scgo365.sharepoint.com/sites/QAPPPC"
FOLDER_RELATIVE_PATH = "/sites/QAPPPC/Shared Documents/QA PPPC/QA Pulp/Log book Pulp/2026/Log book Pulp Line 2 - 2026"

# SharePoint REST API Endpoint for listing files in a folder
API_ENDPOINT = f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('{FOLDER_RELATIVE_PATH}')/Files"


def test_fetch_sharepoint_folder():
    print("=" * 70)
    print("      READ-ONLY SHAREPOINT DIRECT FETCH TEST")
    print("=" * 70)
    print(f"Site URL    : {SITE_URL}")
    print(f"Folder Path : {FOLDER_RELATIVE_PATH}")
    print(f"API Endpoint: {API_ENDPOINT}")
    print("-" * 70)

    headers = {
        "Accept": "application/json;odata=verbose",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("[1/2] Sending GET request to SharePoint REST API...")
        response = requests.get(API_ENDPOINT, headers=headers, timeout=15, allow_redirects=True)
        
        print(f"HTTP Status Code : {response.status_code}")
        print(f"Content Type     : {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("d", {}).get("results", [])
            print(f"\n✅ SUCCESS! Found {len(results)} file(s) in folder:")
            print("-" * 70)
            for f in results:
                name = f.get("Name")
                size_mb = round(int(f.get("Length", 0)) / (1024 * 1024), 2)
                time_mod = f.get("TimeLastModified")
                print(f"  📄 File: {name:<50} | Size: {size_mb:>5} MB | Modified: {time_mod}")
            print("=" * 70)
            return True
        elif response.status_code == 401:
            print("\n❌ ACCESS DENIED (401 Unauthorized / SSO Redirect):")
            print("   SharePoint requires authenticated login session or Azure App Access Token.")
            print("   (Direct unauthenticated REST API requests are blocked by SCG security policy).")
            print("=" * 70)
            return False
        else:
            print(f"\n⚠️ Response Status {response.status_code}:")
            print(response.text[:300])
            print("=" * 70)
            return False

    except Exception as e:
        print("=" * 70)
        print(f"❌ EXCEPTION: {e}")
        return False


if __name__ == "__main__":
    test_fetch_sharepoint_folder()
