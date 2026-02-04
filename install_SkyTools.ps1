$Host.UI.RawUI.WindowTitle = "SkyTools plugin installer | .gg/skytools"
$name = "luatools" 
$displayName = "SkyTools"
$link = "https://github.com/madoiscool/ltsteamplugin/releases/latest/download/ltsteamplugin.zip"
$milleniumTimer = 5 

# Hidden defines
$steam = (Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam").InstallPath
if (-not $steam) {
    $steam = (Get-ItemProperty "HKCU:\Software\Valve\Steam").SteamPath
}
$upperName = "SkyTools"
$isForced = $args -contains "-f"

#### Helper Functions ####
function Get-MillenniumPython {
    param($SteamPath)
    $candidates = @(
        "$SteamPath\steamui\millennium\python\python.exe",
        "$SteamPath\steamui\resources\millennium\python\python.exe",
        "$SteamPath\millennium\python\python.exe",
        "$SteamPath\steamapps\common\Millennium\python\python.exe",
        "$env:APPDATA\Millennium\python\python.exe",
        "$env:LOCALAPPDATA\Millennium\python\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    
    # Try to find via registry if possible, or fallback to standard python if added to PATH
    try {
        $sysPython = (Get-Command python -ErrorAction SilentlyContinue).Source
        # FIX: Explicitly ignore WindowsApps shim which causes errors
        if ($sysPython -and $sysPython -notlike "*WindowsApps*") { 
            # Double check with version command
            try {
                $verification = & $sysPython --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $verification -match "^Python \d") {
                    return $sysPython 
                }
            }
            catch {}
        }
    }
    catch {}

    # Recursive search as last resort (depth limited to avoid long waits)
    $exe = Get-ChildItem -Path $SteamPath -Recurse -Depth 3 -Filter "python.exe" -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -like "*millennium*" -and $_.FullName -notlike "*cache*" } | 
    Select-Object -First 1
    
    if ($exe) { return $exe.FullName }
    return $null
}


#### Logging defines ####
function Log {
    param ([string]$Type, [string]$Message, [boolean]$NoNewline = $false)

    $Type = $Type.ToUpper()
    switch ($Type) {
        "OK" { $foreground = "Green" }
        "INFO" { $foreground = "Cyan" }
        "ERR" { $foreground = "Red" }
        "WARN" { $foreground = "Yellow" }
        "LOG" { $foreground = "Magenta" }
        "AUX" { $foreground = "DarkGray" }
        default { $foreground = "White" }
    }

    $date = Get-Date -Format "HH:mm:ss"
    $prefix = if ($NoNewline) { "`r[$date] " } else { "[$date] " }
    Write-Host $prefix -ForegroundColor "Cyan" -NoNewline

    Write-Host [$Type] $Message -ForegroundColor $foreground -NoNewline:$NoNewline
}

#### License System ####
function Get-HWID {
    return (Get-WmiObject Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID).Trim()
}

function Activate-License {
    param($Key)
    $hwid = Get-HWID
    # Obfuscated API URL to hide admin info
    $b64Url = "aHR0cHM6Ly9za3l0b29scy1saWNlbnNlLm1tb2hhZWxhbXJpLndvcmtlcnMuZGV2"
    $baseUrl = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b64Url))
    $apiUrl = "$baseUrl/activate"
    
    Log "INFO" "Verifying license with server..."
    try {
        $body = @{ key = $Key; hwid = $hwid } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri $apiUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10
        
        if ($response.success) {
            Log "OK" "License Active: $($response.message)"
            return $true
        }
        else {
            Log "ERR" "License Error: $($response.message)"
            return $false
        }
    }
    catch {
        Log "ERR" "Server connection failed: $($_.Exception.Message)"
        return $false
    }
}

Log "WARN" "Installing SkyTools (Safe Version)"
Write-Host

# LICENSE CHECK (Stored in Steam folder to avoid permission issues in System32)
$licenseFile = Join-Path $steam "skytools_license.key"
$validLicense = $false

if (Test-Path $licenseFile) {
    $savedKey = Get-Content $licenseFile -Raw
    $savedKey = $savedKey.Trim()
    if ($savedKey.Length -gt 5) {
        Log "INFO" "Found saved license key."
        if (Activate-License -Key $savedKey) {
            $validLicense = $true
        }
    }
}

while (-not $validLicense) {
    Write-Host "Please enter your SkyTools License Key:" -ForegroundColor Yellow
    $inputKey = Read-Host
    $inputKey = $inputKey.Trim()
    
    if ($inputKey -eq "") {
        Log "ERR" "Key cannot be empty."
        continue
    }

    if (Activate-License -Key $inputKey) {
        $inputKey | Out-File $licenseFile -Encoding ASCII
        $validLicense = $true
    }
    else {
        Log "WARN" "Invalid Key. Please try again or contact support."
    }
}

Write-Host "License Verified. Starting installation..." -ForegroundColor Green
Start-Sleep -Seconds 1
Write-Host

# To hide IEX blue box thing
$ProgressPreference = 'SilentlyContinue'

Get-Process steam -ErrorAction SilentlyContinue | Stop-Process -Force

#### Requirements part (SteamTools) ####
$path = Join-Path $steam "xinput1_4.dll"
if ( Test-Path $path ) {
    Log "INFO" "Steamtools already installed"
}
else {
    if (($isForced)) {
        Log "AUX" "-f argument detected, skipping installation."
        exit
    }

    # Filtering the installation script (Safe Mode)
    # Uses steam.run but filters out malicious commands
    try {
        $script = Invoke-RestMethod "https://steam.run" -ErrorAction Stop
        $keptLines = @()

        foreach ($line in $script -split "`n") {
            $conditions = @( 
                ($line -imatch "Start-Process" -and $line -imatch "steam"),
                ($line -imatch "steam\.exe"),
                ($line -imatch "Start-Sleep" -or $line -imatch "Write-Host"),
                ($line -imatch "cls" -or $line -imatch "exit"),
                ($line -imatch "Stop-Process" -and -not ($line -imatch "Get-Process"))
            )

            if (-not($conditions -contains $true)) {
                $keptLines += $line
            }
        }

        $SteamtoolsScript = $keptLines -join "`n"
        Log "ERR" "Steamtools not found. Installing safely..."

        Invoke-Expression $SteamtoolsScript *> $null

    }
    catch {
        Log "ERR" "Could not fetch SteamTools script. Skipping."
    }
}



# Remove legacy LuaTools folder if it exists to prevent duplicates
$legacyPaths = @(
    (Join-Path $steam "plugins\luatools"),
    (Join-Path $steam "plugins\LuaTools")
)
foreach ($lp in $legacyPaths) {
    if (Test-Path $lp) {
        Log "INFO" "Cleaning up previous version..."
        try { Remove-Item $lp -Recurse -Force -ErrorAction SilentlyContinue } catch {}
    }
}

# Millenium check
$milleniumInstalling = $false
foreach ($file in @("millennium.dll", "python311.dll")) {
    if (!( Test-Path (Join-Path $steam $file) )) {
        Log "INFO" "Installing Millennium..."
        Invoke-Expression "& { $(Invoke-RestMethod 'https://clemdotla.github.io/millennium-installer-ps1/millennium.ps1') } -NoLog -DontStart -SteamPath '$steam'"
        Log "OK" "Millennium installed"
        $milleniumInstalling = $true
        break
    }
}
if ($milleniumInstalling -eq $false) { Log "INFO" "Millennium already installed" }


#### Plugin part ####

# Ensuring \Steam\plugins
if (!( Test-Path (Join-Path $steam "plugins") )) {
    New-Item -Path (Join-Path $steam "plugins") -ItemType Directory *> $null
}

$Path = Join-Path $steam "plugins\$name" 

# Clean install
if (Test-Path $Path) {
    Remove-Item $Path -Recurse -Force
}

# Installation
$subPath = Join-Path $env:TEMP "$name.zip"

Log "LOG" "Downloading $displayName"
try {
    Invoke-WebRequest -Uri $link -OutFile $subPath *> $null
    Log "LOG" "Unzipping $displayName"

    Expand-Archive -Path $subPath -DestinationPath $Path *> $null
    Remove-Item $subPath -ErrorAction SilentlyContinue

    # REBRANDING LOGIC: Find plugin.json and rename to skytools
    $jsonPath = Join-Path $Path "plugin.json"
    
    # If not at root, look inside subfolders
    if (-not (Test-Path $jsonPath)) {
        $subItems = Get-ChildItem $Path -Directory
        foreach ($item in $subItems) {
            $check = Join-Path $item.FullName "plugin.json"
            if (Test-Path $check) {
                # Move content up if nested? Or just edit
                $jsonPath = $check
                break
            }
        }
    }

    if (Test-Path $jsonPath) {
        $json = Get-Content $jsonPath -Raw | ConvertFrom-Json
        $json.name = $name
        # FIX: Update common_name for UI display
        if (-not $json.PSObject.Properties['common_name']) {
            $json | Add-Member -Name "common_name" -Value "SkyTools" -MemberType NoteProperty
        }
        $json.common_name = "SkyTools"

        # Ensure description exists or update it
        if (-not $json.PSObject.Properties['description']) {
            $json | Add-Member -Name "description" -Value "SkyTools Plugin" -MemberType NoteProperty
        }
        $json.description = "SkyTools Plugin"
        
        # Write clean JSON (ASCII to avoid BOM issues)
        $json | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonPath -Encoding ASCII

        Log "OK" "Metadata updated"

        # LICENSE PROTECTION: Save Key
        $licensePath = Join-Path $Path "backend\license.key"
        $inputKey | Out-File $licensePath -Encoding ASCII
        
        # LICENSE PROTECTION: Create Check Script
        $utf8NoBom = New-Object System.Text.UTF8Encoding $False
        $checkScriptPath = Join-Path $Path "backend\license_check.py"
        $checkScriptContent = @'
import sys
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
        return subprocess.check_output('wmic csproduct get uuid', shell=True).decode().split('\n')[1].strip()
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
        # Fallback: if offline, maybe allow? For now, Fail Safe -> Exit
        sys.exit(1)

# Run on import
verify()
'@
        [System.IO.File]::WriteAllText($checkScriptPath, $checkScriptContent, $utf8NoBom)
        Log "OK" "License protection installed"
    }

    # ADVANCED REBRANDING: Recursive text replacement
    Log "INFO" "Applying visuals patch (This may take a moment)..."
    
    # 1. Text Replacement in Files
    # Include .py files to rebrand logging and messages, BUT must protect USER_AGENT below!
    $filesToPatch = Get-ChildItem -Path $Path -Recurse -Include *.py, *.js, *.html, *.css, *.json

    foreach ($file in $filesToPatch) {
        try {
            if ($file.Name -eq "plugin.json") { continue } # handled above
            
            # FIX: Force UTF-8 Reading to prevent mojibake (garbled characters)
            $utf8 = [System.Text.Encoding]::UTF8
            $content = [System.IO.File]::ReadAllText($file.FullName, $utf8)
            
            if ($content -match "LuaTools") {
                # Replace but restore specific GitHub URL if needed
                $newContent = $content -replace "LuaTools", "SkyTools"
                if ($newContent -match "github.com/madoiscool") {
                    # Restore the URL if it was broken (the URL is usually lower case luatools but just in case)
                    $newContent = $newContent -replace "SkyTools/ltsteamplugin", "madoiscool/ltsteamplugin"
                }

                # CRITICAL FIX: Restore User-Agent in config.py to prevent 403 Forbidden
                if ($file.Name -eq "config.py") {
                    $newContent = $newContent -replace 'USER_AGENT = "SkyTools', 'USER_AGENT = "luatools'
                }

                # FIX: Restore internal plugin name in plugin.json (User requirement)
                if ($file.Name -eq "plugin.json") {
                    $newContent = $newContent -replace '"name":\s*"SkyTools"', '"name": "luatools"'
                }
                
                # FIX: Restore JS IPC calls to use 'luatools' as the plugin name
                if ($file.Extension -eq ".js") {
                    $newContent = $newContent -replace "Millennium.callServerMethod\(\s*'SkyTools'", "Millennium.callServerMethod('luatools'"
                }

                # FIX: Write UTF-8 WITHOUT BOM to prevent JSON parsing errors in python
                $utf8NoBom = New-Object System.Text.UTF8Encoding $False
                [System.IO.File]::WriteAllText($file.FullName, $newContent, $utf8NoBom)
            }
            
            # UI CUSTOMIZATION: Remove Discord, Credits, Donate Keys
            if ($file.FullName -match "\.js$") {
                $jsContent = [System.IO.File]::ReadAllText($file.FullName, $utf8)
                $jsModified = $false
                
                # 1. Remove Discord Buttons
                if ($jsContent -match "createIconButton\('lt-settings-discord'") {
                    $jsContent = $jsContent -replace "const discordBtn = createIconButton\('lt-settings-discord'.*?\);", "const discordBtn = null;"
                    $jsModified = $true
                }
                if ($jsContent -match "createIconButton\('lt-fixes-discord'") {
                    $jsContent = $jsContent -replace "const discordBtn = createIconButton\('lt-fixes-discord'.*?\);", "const discordBtn = null;"
                    $jsModified = $true
                }
                if ($jsContent -match "iconButtons.appendChild\(discordIconBtn\);") {
                    $jsContent = $jsContent -replace "iconButtons.appendChild\(discordIconBtn\);", "// iconButtons.appendChild(discordIconBtn);"
                    $jsModified = $true
                }

                # FIX: Prevent crash when assigning onclick to null discordBtn
                if ($jsContent -match "discordBtn.onclick = function") {
                    $jsContent = $jsContent -replace "discordBtn.onclick = function", "if (discordBtn) discordBtn.onclick = function"
                    $jsModified = $true
                }

                # 2. Hide Credit Text
                if ($jsContent -match "const creditTemplate = lt\('Only possible thanks to") {
                    $jsContent = $jsContent -replace "const creditTemplate = lt\('Only possible thanks to .*?'\);", "const creditTemplate = '';"
                    $jsModified = $true
                }
                if ($jsContent -match "creditMsg.style.cssText = 'margin-top:16px;") {
                    $jsContent = $jsContent -replace "creditMsg.style.cssText = 'margin-top:16px;.*?;';", "creditMsg.style.cssText = 'display:none;';"
                    $jsModified = $true
                }

                # 3. Hide Donate Keys
                # We inject a continue statement in the settings loop
                if ($jsContent -match "if \(!option \|\| !option.key\) continue;") {
                    # Avoid double patching
                    if ($jsContent -notmatch "if \(option.key === 'donateKeys'\) continue;") {
                        $jsContent = $jsContent -replace "if \(!option \|\| !option.key\) continue;", "if (!option || !option.key) continue; if (option.key === 'donateKeys') continue;"
                        $jsModified = $true
                    }
                }

                # 4. FIX: Remove dead 'files.luatools.work' URL and use GitHub mirror
                # This fixes the [Errno 11001] getaddrinfo failed error
                # APPLIES TO BOTH JS (Frontend) AND PY (Backend fixes.py)
                if ($jsContent -match "files.luatools.work" -or $jsContent -match "files.SkyTools.work") {
                    $jsContent = $jsContent -replace "https://files.luatools.work/GameBypasses/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    $jsContent = $jsContent -replace "https://files.luatools.work/OnlineFix1/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    
                    # Catch rebranded versions
                    $jsContent = $jsContent -replace "https://files.SkyTools.work/GameBypasses/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    $jsContent = $jsContent -replace "https://files.SkyTools.work/OnlineFix1/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    $jsModified = $true
                }

                if ($jsModified) {
                    $utf8NoBom = New-Object System.Text.UTF8Encoding $False
                    [System.IO.File]::WriteAllText($file.FullName, $jsContent, $utf8NoBom)
                }
            } 
            # BACKEND PATCHING (files.luatools.work -> GitHub) for .py files
            elseif ($file.FullName -match "\.py$") {
                $pyContent = [System.IO.File]::ReadAllText($file.FullName, $utf8)
                if ($pyContent -match "files.luatools.work") {
                    $pyContent = $pyContent -replace "https://files.luatools.work/GameBypasses/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    $pyContent = $pyContent -replace "https://files.luatools.work/OnlineFix1/", "https://github.com/madoiscool/lt_api_links/releases/download/unsteam/"
                    
                    $utf8NoBom = New-Object System.Text.UTF8Encoding $False
                    [System.IO.File]::WriteAllText($file.FullName, $pyContent, $utf8NoBom)
                }
            }
        }
        catch {}
    }

    # 2. ROBUST BACKEND PATCHING: Use Python to patch fixes.py
    # This avoids PowerShell regex issues with file encoding and complex strings
    Log "INFO" "Patching backend DNS settings..."
    
    # Create the python patch script on the fly to avoid path issues with ieX
    $pyPatchCode = @"
import os
import sys

def patch_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content.replace('https://files.luatools.work/GameBypasses/', 'https://github.com/madoiscool/lt_api_links/releases/download/unsteam/')
        new_content = new_content.replace('https://files.luatools.work/OnlineFix1/', 'https://github.com/madoiscool/lt_api_links/releases/download/unsteam/')
        
        # Also catch the rebranded version if the installer's global replace ran first
        new_content = new_content.replace('https://files.SkyTools.work/GameBypasses/', 'https://github.com/madoiscool/lt_api_links/releases/download/unsteam/')
        new_content = new_content.replace('https://files.SkyTools.work/OnlineFix1/', 'https://github.com/madoiscool/lt_api_links/releases/download/unsteam/')

        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Patched: {file_path}')
        else:
            print(f'Skipped (already patched or not found): {file_path}')

    except Exception as e:
        print(f'Error patching {file_path}: {e}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith('fixes.py'):
                    patch_file(os.path.join(root, file))
"@
    
    $tempPyScript = Join-Path $env:TEMP "skytools_patch.py"
    $pyPatchCode | Out-File -FilePath $tempPyScript -Encoding UTF8
    
    if (Test-Path $tempPyScript) {
        python $tempPyScript "$Path\backend"
        Remove-Item $tempPyScript -ErrorAction SilentlyContinue
    }
    else {
        Log "WARN" "Could not create temp patch script, backend DNS issues may persist."
    }

    # 2. File/Folder Renaming
    $items = Get-ChildItem -Path $Path -Recurse | Sort-Object FullName -Descending
    foreach ($item in $items) {
        if ($item.Name -match "LuaTools") {
            $newName = $item.Name -replace "LuaTools", "SkyTools"
            try { Rename-Item -Path $item.FullName -NewName $newName -ErrorAction SilentlyContinue } catch {}
        }
        elseif ($item.Name -match "luatools") {
            $newName = $item.Name -replace "luatools", "skytools"
            try { Rename-Item -Path $item.FullName -NewName $newName -ErrorAction SilentlyContinue } catch {}
        }
    }

    # 3. CRITICAL: Patch backend/config.py to match new filenames
    # This aligns the Python backend with our renamed files
    $configPyPath = Join-Path $Path "backend\config.py"
    if (Test-Path $configPyPath) {
        try {
            Log "INFO" "Patching backend configuration..."
            $utf8 = [System.Text.Encoding]::UTF8
            $pyContent = [System.IO.File]::ReadAllText($configPyPath, $utf8)
            
            # Update constants to point to SkyTools files
            # WEBKIT_DIR_NAME = "LuaTools" -> "SkyTools"
            $pyContent = $pyContent -replace 'WEBKIT_DIR_NAME = "LuaTools"', 'WEBKIT_DIR_NAME = "SkyTools"'
            $pyContent = $pyContent -replace 'WEB_UI_JS_FILE = "luatools.js"', 'WEB_UI_JS_FILE = "SkyTools.js"'
            $pyContent = $pyContent -replace 'WEB_UI_ICON_FILE = "luatools-icon.png"', 'WEB_UI_ICON_FILE = "SkyTools-icon.png"'
            
            # LICENSE PROTECTION: Hook into config.py
            if ($pyContent -notmatch "license_check") {
                $pyContent = $pyContent + "`n`ntry:`n    from . import license_check`nexcept:`n    pass`n"
            }
            
            # Write back
            $utf8NoBom = New-Object System.Text.UTF8Encoding $False
            [System.IO.File]::WriteAllText($configPyPath, $pyContent, $utf8NoBom)
            Log "OK" "Backend config patched"
        }
        catch {
            Log "WARN" "Failed to patch config.py: $_"
        }
    }


    Log "OK" "Visuals patched"



    # FIX: Install Dependencies (httpx, requests)
    Log "INFO" "Checking Python dependencies..."
    $pyPath = Get-MillenniumPython -SteamPath $steam
    if (-not $pyPath) {
        Log "WARN" "Python not found. SkyTools requires Python."
        Log "INFO" "Attempting to install Python via Winget..."
        try {
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            # Refresh path
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            $pyPath = Get-MillenniumPython -SteamPath $steam
        }
        catch {
            Log "ERR" "Winget failed. Please install Python manually from python.org"
        }
    }

    if ($pyPath) {
        Log "INFO" "Found Python at: $pyPath"
        try {
            $proc = Start-Process -FilePath $pyPath -ArgumentList "-m pip install httpx requests" -Wait -PassThru -NoNewWindow
            if ($proc.ExitCode -eq 0) {
                Log "OK" "Dependencies installed (httpx, requests)"
            }
            else {
                Log "WARN" "Pip install returned error code $($proc.ExitCode)"
            }
        }
        catch {
            Log "ERR" "Failed to install dependencies: $_"
        }
    }
    else {
        Log "ERR" "Could not find Millennium Python to install dependencies!"
        Write-Host "Please install Python 3.11 from python.org and check 'Add to PATH' during installation." -ForegroundColor Red
    }

    # 4. FINAL ENFORCEMENT: Robustly fix plugin.json and JS IPC calls
    # This ensures internal name is 'luatools' even if regexes failed previously
    Log "INFO" "Finalizing configuration..."

    $pluginJsonPath = "$Path\plugin.json"
    $correctJsonContent = @'
{
  "$schema": "https://raw.githubusercontent.com/SteamClientHomebrew/Millennium/main/src/sys/plugin-schema.json",
  "name": "luatools",
  "common_name": "SkyTools",
  "description": "SkyTools Steam Plugin!",
  "version": "6.4.1",
  "include": [
    "public"
  ]
}
'@
    [System.IO.File]::WriteAllText($pluginJsonPath, $correctJsonContent, $utf8NoBom)
    Log "OK" "Configuration applied"

    # Force patch JS files again to be absolutely sure
    $jsFiles = Get-ChildItem -Path "$Path\public" -Filter "*.js" -Recurse
    foreach ($jsFile in $jsFiles) {
        $txt = [System.IO.File]::ReadAllText($jsFile.FullName, $utf8)
        # Force any variation of SkyTools/LuaTools in callServerMethod to be 'luatools'
        # Matches: Millennium.callServerMethod('SkyTools' OR 'LuaTools' ...)
        $txtFixed = $txt -replace "Millennium.callServerMethod\(\s*['`"](SkyTools|LuaTools)['`"]", "Millennium.callServerMethod('luatools'"
        
        # DEBUG FIX: Inject better error handling in JS to see WHY it fails
        # Finds the .catch block for CheckForFixes and adds the error message to the alert
        # (Keeping this safety patch in place as it is good practice, but not emphasizing error)
        $txtFixed = $txtFixed -replace "\.catch\(function\(\) \{\s*const msg = lt\('Error checking for fixes'\);", ".catch(function(e) { const msg = lt('Error checking for fixes') + ' (' + String(e) + ')';"

        if ($txt -ne $txtFixed) {
            [System.IO.File]::WriteAllText($jsFile.FullName, $txtFixed, $utf8NoBom)
            # Log "OK" "Fixed IPC call in $($jsFile.Name)" # Silencing detailed log
        }
    }

    Log "OK" "$upperName installed"
}
catch {
    Log "ERR" "Failed to download/install plugin: $_"
}


# Removing beta
$betaPath = Join-Path $steam "package\beta"
if ( Test-Path $betaPath ) {
    Remove-Item $betaPath -Recurse -Force
}

# Removing potential x32 
$cfgPath = Join-Path $steam "steam.cfg"
if ( Test-Path $cfgPath ) {
    Remove-Item $cfgPath -Recurse -Force
}
Remove-ItemProperty -Path "HKCU:\Software\Valve\Steam" -Name "SteamCmdForceX86" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Valve\Steam" -Name "SteamCmdForceX86" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam" -Name "SteamCmdForceX86" -ErrorAction SilentlyContinue

# Toggling the plugin on
$configPath = Join-Path $steam "ext\config.json"
$updateStatus = $true

if (-not (Test-Path $configPath)) {
    $config = @{
        general = @{
            checkForMillenniumUpdates = $false
        }
        plugins = @{
            enabledPlugins = @($name)
        }
    }
    New-Item -Path (Split-Path $configPath) -ItemType Directory -Force | Out-Null
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
}
else {
    $rawJson = Get-Content $configPath -Raw -Encoding UTF8
    $config = $rawJson | ConvertFrom-Json

    if (-not $config.general) {
        $config | Add-Member -MemberType NoteProperty -Name "general" -Value ([PSCustomObject]@{}) -Force
    }
    # Disable updates temporarily
    if ($config.general.checkForMillenniumUpdates -ne $false) {
        $config.general | Add-Member -MemberType NoteProperty -Name "checkForMillenniumUpdates" -Value $false -Force
    }
    else {
        $updateStatus = $false
    }

    if (-not $config.plugins) {
        $config | Add-Member -MemberType NoteProperty -Name "plugins" -Value ([PSCustomObject]@{}) -Force
    }
    if (-not $config.plugins.enabledPlugins) {
        $config.plugins | Add-Member -MemberType NoteProperty -Name "enabledPlugins" -Value @() -Force
    }

    $pluginsList = @($config.plugins.enabledPlugins)
    if ($pluginsList -notcontains $name) {
        $pluginsList += $name
        $config.plugins.enabledPlugins = $pluginsList
    }

    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
}
Log "OK" "Plugin enabled"

# Result showing
Write-Host
if ($milleniumInstalling) { Log "WARN" "Steam startup will be longer, don't panic and don't touch anything in steam!" }

# Start Steam with -clearbeta
$exe = Join-Path $steam "steam.exe"
Start-Process $exe -ArgumentList "-clearbeta"

Log "INFO" "Starting steam"

# Turning back on updates
if ($updateStatus -eq $true) {
    Log "WARN" "Don't close the script yet (Restoring settings...)"
    Start-Sleep -Seconds 20

    $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $config.general.checkForMillenniumUpdates = $true
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8

    Log "OK" "Job done, you can close this."
}
