import os
import sys
import time
import subprocess
import json
import psutil
import vdf # We might need a vdf parser, or use a simple regex approach if dep is issue
from datetime import datetime

# Configuration
CHECK_INTERVAL = 30 # Seconds
STEAM_CONFIG_PATH = None # Will safely locate
IGNORED_PROCESSES = ["steam.exe", "discord.exe", "explorer.exe", "chrome.exe", "skytools_service.exe"]

# State
active_games = {} # {pid: {name, start_time}}
playtime_cache = {} # {game_name: total_minutes}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Service] {msg}")

# --- VDF HELPER (Simple Parser to avoid dependencies) ---
def parse_vdf(content):
    """
    Very basic VDF parser. 
    Returns a nested dict. 
    Note: reliable VDF parsing is complex, this is a simplified version for localconfig.
    """
    # For robust modification, we might want to use a regex replacement 
    # instead of full parsing/dumping to preserve comments/formatting.
    # Given the complexity, we will use a REGEX-based updater for specific keys.
    pass

def update_steam_config(appid, duration_minutes):
    """
    Updates localconfig.vdf:
    "Software" -> "Valve" -> "Steam" -> "apps" -> [AppID] -> "PlayTime" (add minutes)
    """
    steam_path = get_steam_path()
    if not steam_path: return
    
    userdata = os.path.join(steam_path, "userdata")
    if not os.path.exists(userdata): return
    
    # Iterate users (usually only one active, or we update all)
    for user_id in os.listdir(userdata):
        config_path = os.path.join(userdata, user_id, "config", "localconfig.vdf")
        if os.path.exists(config_path):
            try:
                # We use a safe read/write approach
                with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # We need to find the AppID section
                # Structure: "apps" { ... "123456" { ... "PlayTime" "100" ... } ... }
                
                # Improved Regex strategy:
                # 1. Find "apps" section (simplified)
                # 2. Inside, find or create "AppID" section
                # 3. Inside, update "PlayTime"
                
                # Since implementing a full VDF parser in one file is risky, 
                # we will log the intent for now and focus on the Backup Trigger which is critical.
                # If the user insists on visual playtime, we can add a proper library later.
                
                log(f"[SIMULATION] Injection PlayTime (+{int(duration_minutes)}min) pour {appid} dans {config_path}")
                
            except Exception as e:
                log(f"Erreur update VDF: {e}")

def get_steam_path():
    # Reuse logic from installer or safe import
    # Hardcoded fallback for now or use registry check from before
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return path
    except:
        return r"C:\Program Files (x86)\Steam"

def trigger_backup():
    log("🎮 Jeu fermé ! Lancement de la sauvegarde automatique...")
    try:
        # Run save_manager.py backup in a separate process
        subprocess.Popen([sys.executable, "save_manager.py", "backup"], 
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except Exception as e:
        log(f"Erreur lancement backup: {e}")

def scan_processes():
    current_pids = []
    
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            exe_path = proc.info['exe']
            if not exe_path: continue
            
            # Detect Steam Games via path
            if "steamapps\\common" in exe_path.lower():
                name = proc.info['name']
                if name.lower() in IGNORED_PROCESSES: continue
                
                pid = proc.info['pid']
                current_pids.append(pid)
                
                if pid not in active_games:
                    log(f"🟢 Jeu détecté : {name} (PID: {pid})")
                    active_games[pid] = {
                        "name": name,
                        "start_time": time.time(),
                        "exe_path": exe_path
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return current_pids

def main():
    log("🚀 Service SkyTools Démarré.")
    log("👀 Surveillance des jeux en cours...")
    
    while True:
        try:
            current_pids = scan_processes()
            
            # Check for closed games
            ended_games = []
            for pid, game_data in active_games.items():
                if pid not in current_pids:
                    # Game closed
                    duration = (time.time() - game_data["start_time"]) / 60
                    log(f"🔴 Fin de session : {game_data['name']} ({duration:.1f} minutes)")
                    
                    # 1. Update Playtime (Mockup/Placeholder for safety first)
                    # We need AppID to do this really well. 
                    # For now, we focus on the backup.
                    
                    # 2. Trigger Auto Backup
                    trigger_backup()
                    
                    ended_games.append(pid)
            
            for pid in ended_games:
                del active_games[pid]
                
        except Exception as e:
            log(f"Erreur boucle: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Ensure psutil is installed or try to restart with it?
    # For standalone, we might need to bundle it or assume it's there.
    # We'll add a check.
    try:
        import psutil
    except ImportError:
        print("Installation de psutil...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        
    main()
