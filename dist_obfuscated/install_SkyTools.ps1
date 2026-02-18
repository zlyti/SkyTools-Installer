$Host.UI.RawUI.WindowTitle = "SkyTools Installer | .gg/skytools"

# 1. Configuration
$repo = "zlyti/SkyTools-Installer"
$zipName = "SkyTools_Protected.zip"
$releaseUrl = "https://github.com/$repo/releases/latest/download/$zipName"
$installPath = "$env:APPDATA\SkyTools_Setup"

# 2. Helper Functions
function Log {
    param ([string]$Type, [string]$Message)
    $color = switch ($Type) { "OK" {"Green"} "ERR" {"Red"} "INFO" {"Cyan"} "WARN" {"Yellow"} default {"White"} }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

# 3. Clean Setup Directory
if (Test-Path $installPath) {
    Remove-Item $installPath -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -Path $installPath -ItemType Directory -Force | Out-Null

# 4. Download SkyTools
Log "INFO" "Downloading SkyTools..."
try {
    $zipPath = "$installPath\$zipName"
    Invoke-WebRequest -Uri $releaseUrl -OutFile $zipPath
}
catch {
    Log "ERR" "Failed to download SkyTools. Check your internet or if the Release exists."
    exit
}

# 5. Extract
Log "INFO" "Extracting files..."
Expand-Archive -Path $zipPath -DestinationPath $installPath -Force
Remove-Item $zipPath

# 6. Check for Python (Required)
Log "INFO" "Checking for Python..."
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Log "WARN" "Python not found. Attempting to install..."
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# 7. Run Python Installer
$installerScript = "$installPath\src\installer.py"
if (Test-Path $installerScript) {
    Log "OK" "Running SkyTools Installer..."
    Start-Process "python" -ArgumentList "`"$installerScript`"" -Wait -NoNewWindow
}
else {
    Log "ERR" "Installer script not found at $installerScript"
    # Fallback search
    $installerScript = Get-ChildItem $installPath -Recurse -Filter "installer.py" | Select-Object -ExpandProperty FullName -First 1
    if ($installerScript) {
         Log "INFO" "Found at $installerScript, running..."
         Start-Process "python" -ArgumentList "`"$installerScript`"" -Wait -NoNewWindow
    } else {
         Log "ERR" "Fatal: Could not find installer.py"
    }
}

Log "OK" "Installation process finished."
Start-Sleep -Seconds 3
