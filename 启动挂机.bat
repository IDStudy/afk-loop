@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" (
    echo [!] Python not found:
    echo     %PY%
    echo     Edit this bat and point PY to your python.exe
    pause
    exit /b 1
)
if not exist "nfsm_afk.py" (
    echo [!] nfsm_afk.py not found in this folder.
    pause
    exit /b 1
)

rem --- admin check: game runs elevated, UIPI blocks input injection otherwise
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
