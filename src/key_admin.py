"""
SkyTools - Outil d'Administration des Licences (Refactored)
"""
import requests
import secrets
import hashlib
import time
import sys
import os
from .config import API_URL

# SECURITY NOTE: In a real production env, these should be env vars!
ADMIN_PASSWORD = "SkyT00ls_Adm1n_2025_Zlyti!"
SECRET_KEY = "SKYTOOLS_2025_ZLYTI_SECRET"

KEYS_FOLDER = os.path.join(os.path.expanduser("~"), "SkyTools_Keys")
os.makedirs(KEYS_FOLDER, exist_ok=True)

def generate_key():
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    random_part = "".join(parts)
    data = f"{random_part}{SECRET_KEY}"
    hash_part = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
    return f"SKY-{parts[0]}-{parts[1]}-{parts[2]}-{hash_part}"

def add_key_to_server(key: str) -> bool:
    try:
        response = requests.post(
            f"{API_URL}/admin/add-key",
            headers={"Authorization": f"Bearer {ADMIN_PASSWORD}"},
            json={"key": key},
            timeout=15
        )
        return response.json().get("success", False)
    except Exception as e:
        print(f"Erreur connexion: {e}")
        return False

def main():
    print(f"SkyTools Admin v2.0 - API: {API_URL}")
    while True:
        print("\n1. Générer clé\n2. Quitter")
        choice = input("Choix: ")
        if choice == "1":
            key = generate_key()
            if add_key_to_server(key):
                print(f"Clé générée et ajoutée: {key}")
            else:
                print("Erreur ajout serveur")
        elif choice == "2":
            break

if __name__ == "__main__":
    main()
