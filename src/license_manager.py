import os
import sys
import platform
import subprocess
import requests
import json
import base64

# Configuration
# Obfuscated API URL from PS1
B64_URL = "aHR0cHM6Ly9za3l0b29scy1saWNlbnNlLm1tb2hhZWxhbXJpLndvcmtlcnMuZGV2"
API_URL = base64.b64decode(B64_URL).decode("utf-8") + "/activate"

def get_hwid():
    """Generates a hardware ID (UUID) cross-platform."""
    system = platform.system()
    try:
        if system == "Windows":
            try:
                # Try wmic first (legacy)
                cmd = "wmic csproduct get uuid"
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
            except:
                pass
            
            # Fallback to PowerShell (Modern Windows)
            try:
                cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"]
                output = subprocess.check_output(cmd, creationflags=0x08000000 if os.name == 'nt' else 0).decode()
                return output.strip()
            except Exception as e:
                print(f"[License] Detailed HWID Error: {e}")
        elif system == "Linux":
            # Try getting machine-id
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
            # Fallback to dbus machine-id
            elif os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r") as f:
                    return f.read().strip()
    except Exception as e:
        print(f"[License] Error getting HWID: {e}")
    
    return "UNKNOWN_HWID"

def activate_license(key):
    """Verifies the license key with the server."""
    hwid = get_hwid()
    print(f"[License] Verifying key for HWID: {hwid}")
    
    try:
        response = requests.post(
            API_URL, 
            json={"key": key, "hwid": hwid}, 
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"[License] Active: {data.get('message')}")
                return True
            else:
                print(f"[License] Failed: {data.get('message')}")
                return False
        else:
            print(f"[License] Server Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[License] Connection Error: {e}")
        return False

def create_license_check_script(plugin_backend_dir):
    """Injects the license check script into the plugin."""
    script_path = os.path.join(plugin_backend_dir, "license_check.py")
    
    # We embed the script content exactly as in PS1
    content = '''import sys
import os
import subprocess
import requests
import base64

# Obfuscated API URL
B64_URL = "aHR0cHM6Ly9za3l0b29scy1saWNlbnNlLm1tb2hhZWxhbXJpLndvcmtlcnMuZGV2"
API_URL = base64.b64decode(B64_URL).decode("utf-8") + "/verify"
LICENSE_FILE = os.path.join(os.path.dirname(__file__), "license.key")

def get_hwid():
    try:
        if os.name == 'nt':
            return subprocess.check_output('wmic csproduct get uuid', shell=True).decode().split('\\n')[1].strip()
        else:
            with open("/etc/machine-id", "r") as f: return f.read().strip()
    except:
        return "UNKNOWN"

def verify():
    if not os.path.exists(LICENSE_FILE):
        sys.exit(1)
        
    try:
        with open(LICENSE_FILE, "r") as f:
            key = f.read().strip()
            
        hwid = get_hwid()
        r = requests.post(API_URL, json={"key": key, "hwid": hwid}, timeout=5)
        if r.status_code != 200:
            sys.exit(1)
            
    except:
        # Fail safe
        sys.exit(1)

# Run on import
verify()
'''
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Also ensure __init__.py imports it if needed, but config.py patch handles import
        print("[License] Protection script installed.")
    except Exception as e:
        print(f"[License] Failed to install protection: {e}")
