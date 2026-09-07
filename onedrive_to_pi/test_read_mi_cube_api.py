"""
Diagnostic Script to Test Reading PI Data via MI Cube API
"""

import requests
import json

# Candidate Read Endpoints for MI Cube API
ENDPOINTS = [
    "https://micube.scg.com/v2/api/Datacenter/PIServer/GetInterpolatedData/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/ReadInterpolatedData/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/InterpolatedValues/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/GetRecordedData/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/GetValues/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/ReadValues/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/ReadValue/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/GetValue/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/GetInterpolated/",
    "https://micube.scg.com/v2/api/Datacenter/PIServer/ReadInterpolated/"
]

TOKEN = "76ED1A0F-7386-432B-B586-5A8304AE20FB"
SERVER = "VPKGDRBPPI01"

TAGS = [
    "PPPC_DP_Cooking.B1_Discharge_FinalTime_Press1_Status",
    "PPPC_DP_Cooking.B2_Discharge_FinalTime_Press1_Status",
    "PPPC_DP_Cooking.B3_Discharge_FinalTime_Press1_Status",
    "PPPC_DP_Cooking.B4_Discharge_FinalTime_Press1_Status"
]

payload = {
    "token": TOKEN,
    "server": SERVER,
    "tags": TAGS,
    "start_time": "2026-08-01 00:00:00",
    "end_time": "2026-08-02 00:00:00",
    "interval": "5m"
}

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

print("=" * 60)
print("      TESTING MI CUBE READ API ENDPOINTS")
print("=" * 60)
print("Payload:")
print(json.dumps(payload, indent=2))
print("-" * 60)

for url in ENDPOINTS:
    print(f"\nTrying Endpoint: {url}")
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            try:
                data = res.json()
                print("✅ SUCCESS Response Preview:")
                print(str(data)[:500])
                break
            except Exception as e:
                print("Text Response:", res.text[:300])
        else:
            print("Response:", res.text[:200])
    except Exception as err:
        print(f"❌ Exception: {err}")
