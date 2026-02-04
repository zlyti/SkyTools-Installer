
import requests
import secrets
import hashlib
import json

# CONFIG
API_URL = "https://skytools-license.mmohaelamri.workers.dev/admin/add"
ADMIN_SECRET = "SkyTools_Secret_2025_Auto!" 

def generate_key_format():
    """Generates a random key format: SKY-XXXX-XXXX-XXXX-HASH"""
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    random_part = "".join(parts)
    # Simple hash to make it look cool/valid
    hash_part = hashlib.sha256(random_part.encode()).hexdigest()[:8].upper()
    return f"SKY-{parts[0]}-{parts[1]}-{parts[2]}-{hash_part}"

def add_key_to_worker(key):
    try:
        response = requests.post(
            API_URL,
            json={"key": key, "secret": ADMIN_SECRET},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return True, "Success"
            else:
                return False, data.get("message", "Unknown Error")
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def main():
    print("=== SkyTools Key Generator ===")
    print(f"Target API: {API_URL}")
    print("Make sure you updated ADMIN_SECRET in this script matches your Worker Variable!\n")

    while True:
        print("1. Generate New Key")
        print("2. Exit")
        choice = input("Choice: ")

        if choice == "1":
            key = generate_key_format()
            print(f"Generated Key: {key}")
            if input("Add to server? (y/n): ").lower() == 'y':
                success, msg = add_key_to_worker(key)
                if success:
                    print(f"[SUCCESS] Key Active: {key}")
                else:
                    print(f"[ERROR] Failed: {msg}")
        elif choice == "2":
            break

if __name__ == "__main__":
    main()
