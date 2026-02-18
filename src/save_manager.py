import os
import sys
import platform
import subprocess
import requests
import zipfile
import shutil
import json
import time

# Configuration
LUDUSAVI_VERSION = "v0.22.0" 
LUDUSAVI_WIN_URL = f"https://github.com/mtkennerly/ludusavi/releases/download/{LUDUSAVI_VERSION}/ludusavi-{LUDUSAVI_VERSION}-win64.zip"
LUDUSAVI_LINUX_URL = f"https://github.com/mtkennerly/ludusavi/releases/download/{LUDUSAVI_VERSION}/ludusavi-{LUDUSAVI_VERSION}-linux64.tar.gz"

RCLONE_VERSION = "v1.66.0"
RCLONE_WIN_URL = f"https://github.com/rclone/rclone/releases/download/{RCLONE_VERSION}/rclone-{RCLONE_VERSION}-windows-amd64.zip"
RCLONE_LINUX_URL = f"https://github.com/rclone/rclone/releases/download/{RCLONE_VERSION}/rclone-{RCLONE_VERSION}-linux-amd64.zip" # Rclone uses zip for linux too usually

IS_WINDOWS = platform.system() == "Windows"
LUDUSAVI_EXE = "ludusavi.exe" if IS_WINDOWS else "ludusavi"
RCLONE_EXE = "rclone.exe" if IS_WINDOWS else "rclone"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
LUDUSAVI_PATH = os.path.join(TOOLS_DIR, LUDUSAVI_EXE)
RCLONE_PATH = os.path.join(TOOLS_DIR, RCLONE_EXE)
TEMP_BACKUP_DIR = os.path.join(TOOLS_DIR, "temp_backup")

def log(msg):
    print(f"[SkyTools Cloud] {msg}")

def ensure_tools_dir():
    if not os.path.exists(TOOLS_DIR):
        os.makedirs(TOOLS_DIR)

def download_and_extract(url, target_exe_name, target_path):
    log(f"Downloading {target_exe_name} from {url}...")
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        
        archive_name = "temp_tool.zip"
        if url.endswith(".tar.gz"): archive_name = "temp_tool.tar.gz"
        
        archive_path = os.path.join(TOOLS_DIR, archive_name)
        
        with open(archive_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log(f"Extracting {target_exe_name}...")
        
        found = False
        if archive_name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(target_exe_name):
                        # Extract
                        source = zip_ref.open(file)
                        with open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        found = True
                        break
        elif archive_name.endswith(".tar.gz"):
            # Python tarfile handling
            import tarfile
            with tarfile.open(archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(target_exe_name):
                        f = tar.extractfile(member)
                        with open(target_path, "wb") as target:
                            shutil.copyfileobj(f, target)
                        found = True
                        break

        # Cleanup
        time.sleep(1) # Wait for file handles to close
        try:
            if os.path.exists(archive_path):
                os.remove(archive_path)
        except Exception as e:
            log(f"Warning: Could not remove temp file {archive_path}: {e}")
        
        if found:
            if not IS_WINDOWS:
                subprocess.run(["chmod", "+x", target_path])
            return True
        else:
            log(f"Failed to find {target_exe_name} in archive.")
            return False
            
    except Exception as e:
        log(f"Download error: {e}")
        return False

def install_tools():
    ensure_tools_dir()
    
    # Install Ludusavi
    if not os.path.exists(LUDUSAVI_PATH):
        url = LUDUSAVI_WIN_URL if IS_WINDOWS else LUDUSAVI_LINUX_URL
        if not download_and_extract(url, LUDUSAVI_EXE, LUDUSAVI_PATH):
            return False
            
    # Install Rclone
    if not os.path.exists(RCLONE_PATH):
        url = RCLONE_WIN_URL if IS_WINDOWS else RCLONE_LINUX_URL
        if not download_and_extract(url, RCLONE_EXE, RCLONE_PATH):
            return False
            
    return True

def setup_cloud():
    if not install_tools():
        return False

    print("\n--- Configuration Cloud (Google Drive) ---")
    print("SkyTools va ouvrir votre navigateur pour se connecter à Google Drive.")
    print("1. Connectez-vous à votre compte Google.")
    print("2. Autorisez l'accès.")
    print("3. Revenez ici quand c'est fini.")
    print("------------------------------------------------------\n")
    
    try:
        # "config create" skips the menu and goes straight to auth with defaults
        # We delete existing remote first to avoid conflict error
        subprocess.run([RCLONE_PATH, "config", "delete", "skytools"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        # Create 'skytools' remote of type 'drive' using defaults (skip client_id, etc)
        # This will trigger the browser auth automatically
        subprocess.run([RCLONE_PATH, "config", "create", "skytools", "drive"])
        
        print("\n[SkyTools] Configuration Cloud terminée ! ✅")
    except Exception as e:
        log(f"Erreur configuration: {e}")

def is_cloud_configured():
    # Check if 'skytools' remote exists
    if not os.path.exists(RCLONE_PATH): return False
    try:
        res = subprocess.run([RCLONE_PATH, "listremotes"], capture_output=True, text=True)
        return "skytools:" in res.stdout
    except:
        return False

def backup_all():
    if not install_tools(): return False

    log("Préparation de la sauvegarde...")
    # 1. Clean temp dir
    if os.path.exists(TEMP_BACKUP_DIR):
        shutil.rmtree(TEMP_BACKUP_DIR)
    os.makedirs(TEMP_BACKUP_DIR)

    # 2. Ludusavi Backup to Temp
    log("Sauvegarde locale des jeux en cours...")
    cmd = [LUDUSAVI_PATH, "backup", "--force", "--path", TEMP_BACKUP_DIR]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    # Ludusavi might return non-zero on partial failures (e.g. one file locked)
    # We check if anything was actually backed up.
    if not os.listdir(TEMP_BACKUP_DIR):
        log(f"Erreur Backup Ludusavi (Aucun fichier): {res.stderr}")
        return False
    elif res.returncode != 0:
        log("Attention : Certains fichiers n'ont pas pu être sauvegardés (probablement ouverts). On continue quand même.")

    # 3. Rclone Sync to Cloud
    log("Envoi vers le Cloud (Google Drive)...")
    
    rclone_cmd = [RCLONE_PATH, "sync", TEMP_BACKUP_DIR, "skytools:SkyTools_Backups", "--progress"]
    
    try:
        res = subprocess.run(rclone_cmd)
        if res.returncode == 0:
            log("Synchronisation Cloud Terminée ! ✅")
            return True
        else:
            log("Échec de l'envoi Cloud. Avez-vous fait la configuration ?")
            return False
    except Exception as e:
        log(f"Erreur Rclone: {e}")
        return False
    finally:
        pass

def restore_all():
    if not install_tools(): return False

    log("Téléchargement depuis le Cloud...")
    # 1. Clean temp dir
    if os.path.exists(TEMP_BACKUP_DIR):
        shutil.rmtree(TEMP_BACKUP_DIR)
    os.makedirs(TEMP_BACKUP_DIR)
    
    # 2. Rclone Sync Down
    rclone_cmd = [RCLONE_PATH, "sync", "skytools:SkyTools_Backups", TEMP_BACKUP_DIR, "--progress"]
    
    try:
        res = subprocess.run(rclone_cmd)
        if res.returncode != 0:
            log("Échec du téléchargement.")
            return False
    except Exception as e:
        log(f"Erreur Rclone: {e}")
        return False
        
    # 3. Ludusavi Restore
    log("Restauration des fichiers de jeu...")
    cmd = [LUDUSAVI_PATH, "restore", "--force", "--path", TEMP_BACKUP_DIR]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode == 0:
        log("Restauration Terminée ! ✅")
        return True
    else:
        log(f"Erreur Restauration: {res.stderr}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "install": install_tools()
        elif sys.argv[1] == "setup": setup_cloud()
        elif sys.argv[1] == "backup": backup_all()
        elif sys.argv[1] == "restore": restore_all()
    else:
        print("Usage: save_manager.py [install|setup|backup|restore]")
