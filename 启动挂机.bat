@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ---- locate python: absolute path first, then PATH ----
set "PY=C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe"
if exist "%PY%" goto havepy
for /f "delims=" %%i in ('where python 2^>nul') do if not defined FOUND set "FOUND=%%i"
if defined FOUND set "PY=%FOUND%"
:havepy
if not exist "%PY%" (
    echo [!] Python not found.
    echo     Install Python 3.10+ and tick "Add Python to PATH",
    echo     or edit this bat and point PY to your python.exe
    pause
    exit /b 1
)
"%PY%" -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo [!] This Python has no dependencies:
    echo     %PY%
    echo     Run:  pip install -r requirements.txt
    pause
    exit /b 1
)
if not exist "nfsm_afk.py" (
    echo [!] nfsm_afk.py not found in this folder.
    pause
    exit /b 1
)

rem ---- admin check: game runs elevated, UIPI blocks input injection otherwise ----
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator rights, click YES on the UAC popup...
    powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList 'nfsm_afk.py %*' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

set PYTHONIOENCODING=utf-8
"%PY%" nfsm_afk.py %*
echo.
pause
