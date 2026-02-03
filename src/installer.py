import os
import sys
import time
import subprocess
import requests
import json
from .config import API_URL, LICENSE_FILE

def get_hardware_id():
    # Simplified HWID for demo/reboot
    try:
        import uuid
        return str(uuid.getnode())
    except:
        return "UNKNOWN"

def check_license():
    if os.path.exists(LICENSE_FILE):
        print("Licence trouvée...")
        # Add online validation logic here if needed
        return True
    
    print("Entrez votre clé SkyTools:")
    key = input("> ").strip()
    
    # Real validation would go here
    try:
        hwid = get_hardware_id()
        resp = requests.post(f"{API_URL}/validate", json={"key": key, "hwid": hwid})
        if resp.json().get("valid"):
            with open(LICENSE_FILE, "w") as f:
                json.dump({"key": key, "hwid": hwid}, f)
            print("Licence activée !")
            return True
    except Exception as e:
        print(f"Erreur validation: {e}")
    
    return False

def install_millennium():
    print("Installation de Millennium...")
    cmd = "powershell -NoProfile -Command \"Invoke-Expression (Invoke-WebRequest -UseBasicParsing -Uri 'https://steambrew.app/install.ps1').Content\""
    subprocess.run(cmd, shell=True)

def main():
    print("Installation de SkyTools...")
    if not check_license():
        print("Licence invalide.")
        return

    # Install Millennium logic
    install_millennium()
    print("Installation terminée.")

if __name__ == "__main__":
    main()
