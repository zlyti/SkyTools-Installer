@echo off
echo Building SkyTools Reboot...

if not exist dist mkdir dist

echo Building Installer...
pyinstaller --clean --onefile --name SkyTools --distpath dist --workpath build --specpath build_scripts src/installer.py

echo Building KeyAdmin...
pyinstaller --clean --onefile --name KeyAdmin --distpath dist --workpath build --specpath build_scripts src/key_admin.py

echo Done! stored in dist/
pause
