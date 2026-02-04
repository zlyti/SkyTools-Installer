import os
import sys
import time
import subprocess
import requests
import json
import zipfile
import shutil
import tempfile
import winreg

# Configuration
PLUGIN_NAME = "skytools"  # Rebranding LuaTools
# Original LuaTools release (we will rebrand it)
LUATOOLS_ZIP_URL = "https://github.com/madoiscool/ltsteamplugin/releases/latest/download/ltsteamplugin.zip"
HEADER_UA = {"User-Agent": "SkyTools-Installer/1.0"}

def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}")

def get_steam_path():
    try:
        # Try getting path from Registry
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return path
    except:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            path, _ = winreg.QueryValueEx(key, "SteamPath")
            return path
        except:
            return None

def kill_steam():
    log("Closing Steam...", "WARN")
    subprocess.run("taskkill /F /IM steam.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    time.sleep(2)

def install_millennium(steam_path):
    log("Checking Millennium...", "INFO")
    # Check common Millennium files
    if os.path.exists(os.path.join(steam_path, "millennium.dll")) or \
       os.path.exists(os.path.join(steam_path, "python311.dll")) or \
       os.path.exists(os.path.join(steam_path, "winmm.dll")):
        log("Millennium is already installed.", "OK")
        return

    log("Millennium not found. Installing...", "WARN")
    try:
        # Use the official Millennium installer script securely
        cmd = "powershell -NoProfile -Command \"& { $(Invoke-RestMethod 'https://clemdotla.github.io/millennium-installer-ps1/millennium.ps1') } -NoLog -DontStart -SteamPath '" + steam_path + "'\""
        subprocess.run(cmd, shell=True, check=True)
        log("Millennium installed successfully.", "OK")
    except Exception as e:
        log(f"Failed to install Millennium: {e}", "ERR")

def install_plugin(steam_path):
    log(f"Installing {PLUGIN_NAME} plugin...", "INFO")
    
    plugins_dir = os.path.join(steam_path, "plugins")
    target_dir = os.path.join(plugins_dir, PLUGIN_NAME)
    
    os.makedirs(plugins_dir, exist_ok=True)
    
    # Download LuaTools zip
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, "plugin.zip")
    
    try:
        log("Downloading resources...", "INFO")
        resp = requests.get(LUATOOLS_ZIP_URL, headers=HEADER_UA)
        with open(zip_path, "wb") as f:
            f.write(resp.content)
            
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
            
        # Locate the extracted folder (usually "luatools" or similar)
        extracted_items = os.listdir(tmp_dir)
        source_plugin_dir = None
        for item in extracted_items:
            path = os.path.join(tmp_dir, item)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "plugin.json")):
                source_plugin_dir = path
                break
        
        if not source_plugin_dir:
            # Maybe files are at root?
            if os.path.exists(os.path.join(tmp_dir, "plugin.json")):
                source_plugin_dir = tmp_dir
        
        if source_plugin_dir:
            # Rebrand: Edit plugin.json
            json_path = os.path.join(source_plugin_dir, "plugin.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["name"] = PLUGIN_NAME
            # data["description"] = "SkyTools Plugin" # Optional rebranding
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            # Install to Steam/plugins/skytools
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # Use shutil.copytree if different paths, else verify
            if source_plugin_dir != target_dir:
                if source_plugin_dir == tmp_dir:
                     # Copy content manually if root
                     shutil.copytree(source_plugin_dir, target_dir, dirs_exist_ok=True)
                else:
                    shutil.copytree(source_plugin_dir, target_dir)
            
            log(f"{PLUGIN_NAME} installed/updated at {target_dir}", "OK")
        else:
            log("Failed to find valid plugin structure in download.", "ERR")

    except Exception as e:
        log(f"Error during plugin installation: {e}", "ERR")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def enable_plugin_in_millennium(steam_path):
    log("Enabling plugin in Millennium config...", "INFO")
    config_path = os.path.join(steam_path, "ext", "config.json")
    
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except:
                    pass # Corrupt or empty
        
        # Ensure structure
        if "plugins" not in config: config["plugins"] = {}
        if "enabledPlugins" not in config["plugins"]: config["plugins"]["enabledPlugins"] = []
        
        # Enable SkyTools
        if PLUGIN_NAME not in config["plugins"]["enabledPlugins"]:
            config["plugins"]["enabledPlugins"].append(PLUGIN_NAME)
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            log("Plugin enabled in config.", "OK")
        else:
            log("Plugin already enabled.", "OK")
            
    except Exception as e:
        log(f"Error updating Millennium config: {e}", "WARN")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==========================================")
    print("      SkyTools Installer (Safe Mode)      ")
    print("==========================================")
    
    steam_path = get_steam_path()
    if not steam_path:
        log("Steam installation not found!", "ERR")
        return
        
    log(f"Steam found at: {steam_path}", "INFO")
    
    kill_steam()
    install_millennium(steam_path)
    install_plugin(steam_path)
    enable_plugin_in_millennium(steam_path)
    
    print("\nInstallation Complete!")
    print("Please restart Steam manually to apply changes.")
    print("If Steam is already open, it was closed to allow installation.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
