
import requests
import sys

API_URL = "https://skytools-license.skytoolskey.workers.dev"

endpoints = [
    "/verify",
    "/check",
    "/activate",
    "/license",
    "/api/verify",
    "/public/verify"
]

print(f"Probing {API_URL}...")

for ep in endpoints:
    url = f"{API_URL}{ep}"
    try:
        # Try GET
        r = requests.get(url, timeout=5)
        print(f"GET {ep}: {r.status_code}")
        
        # Try POST with dummy data
        r = requests.post(url, json={"key": "TEST", "hwid": "TEST"}, timeout=5)
        print(f"POST {ep}: {r.status_code} - {r.text[:50]}")
    except Exception as e:
        print(f"Error {ep}: {e}")
