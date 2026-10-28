@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem =====================================================================
rem  afk-loop launcher           updated 2026-10-28 17:32
rem    nfsm_afk.py present -> run the source, edits take effect at once
rem    only afk-loop.exe    -> run the exe, no Python needed
rem    pass --no-admin to skip the UAC step (for testing)
rem =====================================================================

set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "NOADMIN="
if not "%~1"=="" for %%a in (%*) do if /i "%%~a"=="--no-admin" set "NOADMIN=1"

rem --- paths live in env vars: cmd -> powershell keeps them as Unicode,
rem     so a Chinese/space path cannot get mangled on the command line ---
set "AFK_DIR=%~dp0"
set "AFK_ARGS=%*"
set "AFK_PY="
set "AFK_SCRIPT=%~dp0nfsm_afk.py"
set "AFK_EXE=%~dp0afk-loop.exe"

if exist "%AFK_SCRIPT%" goto source_mode
if exist "%AFK_EXE%" goto exe_mode

echo [!] Neither nfsm_afk.py nor afk-loop.exe was found here.
echo     Run this bat from the folder that contains them.
pause
exit /b 1

rem ---------------- source mode ----------------
:source_mode
set "AFK_PY=C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe"
if exist "%AFK_PY%" goto havepy
set "AFK_PY="
for /f "delims=" %%i in ('where python 2^>nul') do if not defined AFK_PY set "AFK_PY=%%i"
if defined AFK_PY goto havepy
for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined AFK_PY set "AFK_PY=%%i"
:havepy
if not defined AFK_PY (
    echo [!] Python not found.
    echo     Option A: install Python 3.10+ and tick "Add Python to PATH"
    echo     Option B: edit this bat and point AFK_PY to your python.exe
    echo     Option C: drop afk-loop.exe next to this bat, then Python is not needed
    pause
    exit /b 1
)
"%AFK_PY%" -c "import cv2, numpy, win32gui, win32con, win32process, PIL" >nul 2>&1
if errorlevel 1 (
    echo [!] Python dependencies missing or broken for:
    echo     %AFK_PY%
    echo.
    echo     Run:  "%AFK_PY%" -m pip install opencv-python numpy pillow pywin32
    pause
    exit /b 1
)
if defined NOADMIN goto run_py
net session >nul 2>&1
if not errorlevel 1 goto run_py
echo Requesting administrator rights, click YES on the UAC popup...
powershell -NoProfile -Command "Start-Process -FilePath $env:AFK_PY -ArgumentList ([char]34 + $env:AFK_SCRIPT + [char]34 + ' ' + $env:AFK_ARGS) -WorkingDirectory $env:AFK_DIR -Verb RunAs"
if errorlevel 1 (
    echo [!] Elevation failed or was cancelled.
    echo     Right-click this bat and choose "Run as administrator".
    pause
)
exit /b
:run_py
"%AFK_PY%" "%AFK_SCRIPT%" %*
echo.
pause
exit /b

rem ---------------- exe mode ----------------
:exe_mode
if defined NOADMIN goto run_exe
net session >nul 2>&1
if not errorlevel 1 goto run_exe
echo Requesting administrator rights, click YES on the UAC popup...
if "%~1"=="" (
    powershell -NoProfile -Command "Start-Process -FilePath $env:AFK_EXE -WorkingDirectory $env:AFK_DIR -Verb RunAs"
) else (
    powershell -NoProfile -Command "Start-Process -FilePath $env:AFK_EXE -ArgumentList $env:AFK_ARGS -WorkingDirectory $env:AFK_DIR -Verb RunAs"
)
if errorlevel 1 (
    echo [!] Elevation failed or was cancelled.
    echo     Right-click this bat and choose "Run as administrator".
    pause
)
exit /b
:run_exe
"%AFK_EXE%" %*
echo.
pause
exit /b
