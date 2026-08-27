"""
Test & Diagnostic Utility for MI Cube API Connection and Authentication.
Uses the exact MI Cube API payload format where token, server, tag, and value are passed in the JSON body.
"""

import sys
import os
import json
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config


def callAPI(end_point: str, payload: dict | list):
    """
    Function to call MI Cube API with JSON payload.
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.post(end_point, json=payload, headers=headers, timeout=15)

    if response.status_code == 200:
        if response.content:
            try:
                results = response.json().get('results', {})
                print("✅ API Success (200 OK):", results)
                return results
            except Exception:
                print("✅ API Success (200 OK), Response:", response.text)
                return response.text
        else:
            print("✅ API Success (200 OK) - Empty content")
            return []
    else:
        print('❌ Failed:', response.status_code, response.text)
        return []


def test_mi_cube_connection():
    print("=" * 60)
    print("      MI CUBE API CONNECTION & AUTHENTICATION DIAGNOSTIC")
    print("=" * 60)

    url = config.MI_CUBE_API_URL
    test_tag = list(config.PI_TAG_MAPPING.values())[0] if config.PI_TAG_MAPPING else "PULP-LINE2-KAPPA-PRESS1"

    # Single payload structure following MI Cube schema
    payload_single = {
        "token": config.API_TOKEN,
        "server": config.PI_SERVER_NAME,
        "tag": test_tag,
        "value": 8.8,
        "timestamp": "2026-08-25T08:00:00"
    }

    print(f"Target URL : {url}")
    print("Payload Sample:")
    print(json.dumps(payload_single, indent=2))
    print("-" * 60)

    results = callAPI(url, payload_single)
    return results


if __name__ == "__main__":
    test_mi_cube_connection()

