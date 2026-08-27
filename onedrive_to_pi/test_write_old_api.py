"""
Test New Historical API Endpoint: http://10.28.58.72:8123/write_old
"""

import requests

url = "http://10.28.58.72:8123/write_old"
token = "A9r2T8#kZp2@Vxg9!QwLm4&FjN7Yc$HPs3B5eUaDS1G0oXmIQpqz0Oo8LI"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "tag": "PULP-LINE2-KAPPA-PRESS1",
    "value": "8.8",
    "timestamp": "2026-08-01 08:00:00"
}

import os
import requests

url = "http://10.28.58.72:8123/write_old"
token = "A9r2T8#kZp2@Vxg9!QwLm4&FjN7Yc$HPs3B5eUaDS1G0oXmIQpqz0Oo8LI"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "tag": "PULP-LINE2-KAPPA-PRESS1",
    "value": "8.8",
    "timestamp": "2026-08-01 08:00:00"
}

res_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "write_old_res.txt")

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    out = f"Status Code : {response.status_code}\nResponse Body: {response.text}"
    print(out)
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(out)
except Exception as e:
    out = f"Error: {e}"
    print(out)
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(out)
