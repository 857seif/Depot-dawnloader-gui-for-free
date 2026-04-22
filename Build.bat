@echo off
cls
echo Starting PyInstaller build for depot_dawnloader...

pyinstaller --onefile --windowed --name "luncher" --icon="unnamed.ico" --add-data "unnamed.ico;." luncher.py

echo.
echo ----------------------------------------------------------------------
echo Build attempt complete. Check the "dist" folder for luncher.exe
echo ----------------------------------------------------------------------
pause