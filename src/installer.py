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
import platform

# Modules
try:
    import save_manager
except ImportError:
    save_manager = None

try:
    import license_manager
except ImportError:
    license_manager = None

# Configuration
PLUGIN_NAME = "skytools"  # Rebranding LuaTools
LUATOOLS_ZIP_URL = "https://github.com/madoiscool/ltsteamplugin/releases/latest/download/ltsteamplugin.zip"
HEADER_UA = {"User-Agent": "SkyTools-Installer/1.0"}

IS_WINDOWS = platform.system() == "Windows"

def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}")

def get_steam_path():
    if IS_WINDOWS:
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
    else:
        # Linux Paths
        possible_paths = [
            os.path.expanduser("~/.local/share/Steam"),
            os.path.expanduser("~/.steam/steam"),
            os.path.expanduser("~/.steam/root"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam") # Flatpak
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

def kill_steam():
    log("Fermeture de Steam...", "WARN")
    if IS_WINDOWS:
        subprocess.run("taskkill /F /IM steam.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    else:
        subprocess.run("pkill -9 steam", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    time.sleep(2)

def install_millennium(steam_path):
    log("Vérification de Millennium...", "INFO")
    
    # Check common Millennium files
    millennium_files = ["millennium.dll", "python311.dll", "winmm.dll"] if IS_WINDOWS else ["libmillennium.so"]
    
    is_installed = any(os.path.exists(os.path.join(steam_path, f)) for f in millennium_files)

    if is_installed:
        log("Millennium est déjà installé.", "OK")
        return

    log("Millennium introuvable. Installation...", "WARN")
    try:
        if IS_WINDOWS:
            # Use the official Millennium installer script securely
            cmd = "powershell -NoProfile -Command \"& { $(Invoke-RestMethod 'https://clemdotla.github.io/millennium-installer-ps1/millennium.ps1') } -NoLog -DontStart -SteamPath '" + steam_path + "'\""
            subprocess.run(cmd, shell=True, check=True)
        else:
            # Linux Install Script (User Provided)
            cmd = "curl -fsSL https://raw.githubusercontent.com/SteamClientHomebrew/Millennium/main/scripts/install.sh | bash"
            subprocess.run(cmd, shell=True, check=True)
            
        log("Millennium installé avec succès.", "OK")
    except Exception as e:
        log(f"Échec de l'installation de Millennium: {e}", "ERR")

def install_plugin(steam_path, license_key=None):
    log(f"Installation du plugin {PLUGIN_NAME}...", "INFO")
    
    plugins_dir = os.path.join(steam_path, "plugins")
    target_dir = os.path.join(plugins_dir, PLUGIN_NAME)
    
    os.makedirs(plugins_dir, exist_ok=True)
    
    # Download LuaTools zip
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, "plugin.zip")
    
    try:
        log("Téléchargement des ressources...", "INFO")
        resp = requests.get(LUATOOLS_ZIP_URL, headers=HEADER_UA)
        with open(zip_path, "wb") as f:
            f.write(resp.content)
            
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
            
        # Locate the extracted folder
        extracted_items = os.listdir(tmp_dir)
        source_plugin_dir = None
        for item in extracted_items:
            path = os.path.join(tmp_dir, item)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "plugin.json")):
                source_plugin_dir = path
                break
        
        if not source_plugin_dir:
            if os.path.exists(os.path.join(tmp_dir, "plugin.json")):
                source_plugin_dir = tmp_dir
        
        if source_plugin_dir:
            # Rebrand: Edit plugin.json
            json_path = os.path.join(source_plugin_dir, "plugin.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["name"] = PLUGIN_NAME
            data["common_name"] = "SkyTools"
            data["description"] = "SkyTools Plugin"
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            # Install to Steam/plugins/skytools
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            if source_plugin_dir != target_dir:
                if source_plugin_dir == tmp_dir:
                     shutil.copytree(source_plugin_dir, target_dir, dirs_exist_ok=True)
                else:
                    shutil.copytree(source_plugin_dir, target_dir)
            
            # --- LICENSE SYSTEM INTEGRATION ---
            if license_manager and license_key:
                log("Injection de la protection de licence...", "INFO")
                backend_dir = os.path.join(target_dir, "backend")
                os.makedirs(backend_dir, exist_ok=True)
                
                # 1. Save Key File
                with open(os.path.join(backend_dir, "license.key"), "w") as f:
                    f.write(license_key)
                
                # 2. Inject Check Script
                license_manager.create_license_check_script(backend_dir)
                
                # 3. Patch config.py to run check
                config_py = os.path.join(backend_dir, "config.py")
                if os.path.exists(config_py):
                    with open(config_py, "a") as f:
                        f.write("\n\ntry:\n    from . import license_check\nexcept:\n    pass\n")
            
            log(f"{PLUGIN_NAME} installé/mis à jour dans {target_dir}", "OK")
        else:
            log("Impossible de trouver la structure du plugin dans le téléchargement.", "ERR")

    except Exception as e:
        log(f"Erreur durant l'installation du plugin: {e}", "ERR")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def enable_plugin_in_millennium(steam_path):
    log("Activation du plugin dans Millennium...", "INFO")
    
    config_path = os.path.join(steam_path, "ext", "config.json")
    
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except:
                    pass 
        
        # Ensure structure
        if "plugins" not in config: config["plugins"] = {}
        if "enabledPlugins" not in config["plugins"]: config["plugins"]["enabledPlugins"] = []
        
        # Enable SkyTools
        if PLUGIN_NAME not in config["plugins"]["enabledPlugins"]:
            config["plugins"]["enabledPlugins"].append(PLUGIN_NAME)
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            log("Plugin activé dans la config.", "OK")
        else:
            log("Plugin déjà activé.", "OK")
            
    except Exception as e:
        log(f"Erreur mise à jour config Millennium: {e}", "WARN")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==========================================")
    print("      Installateur SkyTools (Universel)   ")
    print("==========================================")

    # --- LICENSE CHECK ---
    verified_key = None
    if license_manager:
        # Check if saved license exists
        steam_path_pre = get_steam_path()
        if steam_path_pre:
            license_file = os.path.join(steam_path_pre, "skytools_license.key")
            if os.path.exists(license_file):
                with open(license_file, "r") as f:
                    saved_key = f.read().strip()
                if saved_key:
                    print("Clé de licence sauvegardée trouvée.")
                    if license_manager.activate_license(saved_key):
                        verified_key = saved_key
        
        if not verified_key:
            # Display HWID for user confirmation
            my_hwid = license_manager.get_hwid()
            print(f"\n[Sécurité] Votre HWID est : {my_hwid}")
            print("[Sécurité] Cette clé sera liée à cet appareil.")
            
            while True:
                key = input("\nEntrez votre Clé de Licence SkyTools : ").strip()
                if not key:
                    print("La clé ne peut pas être vide.")
                    continue
                
                if license_manager.activate_license(key):
                    verified_key = key
                    print("Licence Vérifiée !")
                    # Save it
                    if steam_path_pre:
                        try:
                            with open(os.path.join(steam_path_pre, "skytools_license.key"), "w") as f:
                                f.write(key)
                        except: pass
                    time.sleep(1)
                    break
                else:
                    print("Clé Invalide. Veuillez réessayer.")
    else:
        log("Gestionnaire de Licence introuvable. Mode Dev.", "WARN")
    
    steam_path = get_steam_path()
    if not steam_path:
        log("Installation Steam introuvable !", "ERR")
        return
        
    log(f"Steam trouvé ici : {steam_path}", "INFO")
    
    kill_steam()
    install_millennium(steam_path)
    install_plugin(steam_path, license_key=verified_key)
    enable_plugin_in_millennium(steam_path)
    
    # Save Manager / Cloud Integration
    if save_manager:
        print("\n--- Configuration Cloud SkyTools ---")
        log("Installation des dépendances Cloud (Ludusavi + Rclone)...", "INFO")
        if save_manager.install_tools():
            log("Outils Cloud prêts.", "OK")
            
            is_configured = save_manager.is_cloud_configured()
            if is_configured:
                log("Cloud déjà configuré (Remote 'skytools' trouvé).", "OK")
                print("Voulez-vous RE-configurer le Cloud ?")
                print("1. Oui")
                print("2. Non (Garder la config actuelle)")
                choice = input("Choix : ")
                if choice == "1":
                    save_manager.setup_cloud()
            else:
                print("\nVoulez-vous connecter votre compte Google Drive maintenant ?")
                print("1. Oui (Lancer l'assistant simplifié)")
                print("2. Non (Configurer plus tard)")
                choice = input("Choix : ")
                if choice == "1":
                    save_manager.setup_cloud()
        else:
            log("Échec de l'installation des outils Cloud.", "ERR")

    # Service / Automation
    print("\n--- Automatisation (Sauvegarde & Temps de Jeu) ---")
    print("Voulez-vous activer le SERVICE D'ARRIÈRE-PLAN ?")
    print("Cela permet de :")
    print("1. Sauvegarder AUTOMATIQUEMENT quand vous fermez un jeu.")
    print("2. Compter votre temps de jeu.")
    print("1. Oui (Recommandé)")
    print("2. Non")
    choice = input("Choix : ")
    
    if choice == "1":
        log("Installation du service...", "INFO")
        
        # 1. Install psutil
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            log("Impossible d'installer psutil via pip.", "WARN")
        
        # 2. Copy files to AppData for persistence
        appdata = os.environ.get("APPDATA")
        install_dir = os.path.join(appdata, "SkyTools")
        os.makedirs(install_dir, exist_ok=True)
        
        files_to_copy = ["service.py", "save_manager.py", "license_manager.py"]
        for f in files_to_copy:
            if os.path.exists(f):
                shutil.copy2(f, os.path.join(install_dir, f))
        
        # Copy tools dir
        tools_src = "tools"
        tools_dst = os.path.join(install_dir, "tools")
        if os.path.exists(tools_src):
            if os.path.exists(tools_dst): shutil.rmtree(tools_dst)
            shutil.copytree(tools_src, tools_dst)
            
        log(f"Fichiers installés dans {install_dir}", "INFO")

        # 3. Add to Startup (Registry)
        try:
            service_path = os.path.join(install_dir, "service.py")
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            
            # Use pythonw.exe to run hidden
            python_exe = sys.executable
            pythonw = python_exe.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw): pythonw = python_exe # Fallback
            
            cmd = f'"{pythonw}" "{service_path}"'
            
            winreg.SetValueEx(key, "SkyToolsService", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            
            # 4. Start it now
            subprocess.Popen([pythonw, service_path], cwd=install_dir)
            log("Service Démarré et ajouté au démarrage Windows !", "OK")
            
        except Exception as e:
            log(f"Erreur installation service: {e}", "ERR")

    print("\nInstallation Terminée !")
    print("Veuillez redémarrer Steam manuellement pour appliquer les changements.")
    input("\nAppuyez sur Entrée pour quitter...")

if __name__ == "__main__":
    main()
