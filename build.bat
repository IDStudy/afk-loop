@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found in PATH.
    echo     Install Python 3.10+ and tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "nfsm_afk.py" (
    echo [!] nfsm_afk.py not found in this folder.
    pause
    exit /b 1
)

echo [1/3] install dependencies + pyinstaller...
python -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
    echo [!] pip install failed.
    pause
    exit /b 1
)

echo [2/3] build with PyInstaller...
python -m PyInstaller --noconfirm --clean --onedir --console --name afk-loop --hidden-import win32gui --hidden-import win32ui --hidden-import win32con --hidden-import win32process --exclude-module tkinter --exclude-module matplotlib --exclude-module pandas --exclude-module scipy --exclude-module PyQt5 --exclude-module PySide6 nfsm_afk.py
if errorlevel 1 goto fail

echo [3/3] copy config example...
copy /y afk_config.example.json "dist\afk-loop\afk_config.json" >nul

echo.
echo Done:  dist\afk-loop\afk-loop.exe
echo Run it as ADMINISTRATOR, and set the game to borderless window.
pause
exit /b 0

:fail
echo.
echo [!] build failed, see the messages above.
pause
exit /b 1
