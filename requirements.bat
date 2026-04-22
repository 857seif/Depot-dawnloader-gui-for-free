@echo off
title Depot Downloader GUI - Setup
color 0b
cls

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found!
    pause
    exit /b
)

python -m pip install --upgrade pip

pip install customtkinter httpx aiofiles ujson vdf pycryptodome pillow pygob

echo [*] Downloading .NET 9...
powershell -Command "Invoke-WebRequest -Uri 'https://download.visualstudio.microsoft.com/download/pr/49e917d5-d09b-432d-9477-7431e3b6a95e/64f02829a27c0065095066925183389a/dotnet-sdk-9.0.100-win-x64.exe' -OutFile 'dotnet_installer.exe'"

echo [*] Installing .NET 9...
start /wait dotnet_installer.exe /passive /norestart

del dotnet_installer.exe

cls
echo ===================================
echo        SETUP COMPLETE
echo ===================================
echo.
pause
