@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem =====================================================================
rem  afk-loop launcher           updated 2026-10-28 16:55
rem    nfsm_afk.py present -> run the source, edits take effect at once
rem    only afk-loop.exe    -> run the exe, no Python needed
rem    pass --no-admin to skip the UAC step (for testing)
rem =====================================================================

set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "NOADMIN="
if not "%~1"=="" for %%a in (%*) do if /i "%%~a"=="--no-admin" set "NOADMIN=1"

set "SCRIPT=%~dp0nfsm_afk.py"
set "EXE=%~dp0afk-loop.exe"
if exist "%SCRIPT%" goto source_mode
if exist "%EXE%" goto exe_mode

echo [!] Neither nfsm_afk.py nor afk-loop.exe was found here.
echo     Run this bat from the folder that contains them.
pause
exit /b 1

rem ---------------- source mode ----------------
:source_mode
set "PY=C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe"
if exist "%PY%" goto havepy
set "PY="
for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if defined PY goto havepy
for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PY set "PY=%%i"
:havepy
if not defined PY (
    echo [!] Python not found.
    echo     Option A: install Python 3.10+ and tick "Add Python to PATH"
    echo     Option B: edit this bat and point PY to your python.exe
    echo     Option C: drop afk-loop.exe next to this bat, then Python is not needed
    pause
    exit /b 1
)
"%PY%" -c "import cv2, numpy, win32gui" >nul 2>&1
if errorlevel 1 (
    echo [!] Dependencies missing for:
    echo     %PY%
    echo     Run:  pip install -r requirements.txt
    pause
    exit /b 1
)
if defined NOADMIN goto run_py
net session >nul 2>&1
if not errorlevel 1 goto run_py
echo Requesting administrator rights, click YES on the UAC popup...
powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList '\"%~dp0nfsm_afk.py\" %*' -WorkingDirectory '%~dp0' -Verb RunAs"
exit /b
:run_py
"%PY%" "%~dp0nfsm_afk.py" %*
echo.
pause
exit /b

rem ---------------- exe mode ----------------
:exe_mode
if defined NOADMIN goto run_exe
net session >nul 2>&1
if not errorlevel 1 goto run_exe
echo Requesting administrator rights, click YES on the UAC popup...
powershell -NoProfile -Command "Start-Process -FilePath '%EXE%' -ArgumentList '%*' -WorkingDirectory '%~dp0' -Verb RunAs"
exit /b
:run_exe
"%EXE%" %*
echo.
pause
exit /b
