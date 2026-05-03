@echo off
REM ============================================================
REM  VR Head Tracking GUI - Requirements Installer
REM
REM  Installs everything needed to run the GUI with full features:
REM    1) Python 3 (if not already installed)
REM    2) pystray  -> minimize-to-tray icon
REM    3) Pillow   -> tray icon image generation
REM
REM  All other modules used by the GUI (tkinter, ctypes, winsound,
REM  subprocess, threading, json, wave) ship with Python's standard
REM  library and don't need separate installs.
REM
REM  IMPORTANT: This installer must run with the SAME elevation level
REM  the GUI runs at. The GUI auto-elevates to admin, so packages must
REM  be installed for admin too. This script auto-elevates itself.
REM ============================================================

REM --- Self-elevate to administrator ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title VR Head Tracking GUI - Install Requirements
color 0B
echo.
echo  ============================================================
echo    VR Head Tracking GUI - Requirements Installer
echo  ============================================================
echo.

REM ============================================================
REM  STEP 1: Check for / install Python
REM ============================================================
echo  [1/5] Checking for Python...
where python >nul 2>&1
if %errorLevel% equ 0 goto :python_ok

echo        Python not found - attempting to install it.
echo.

REM --- Try winget first (built into Win 10 1809+ and Win 11) ---
where winget >nul 2>&1
if %errorLevel% equ 0 (
    echo        Installing Python via winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
    if %errorLevel% equ 0 goto :python_installed
    echo        winget install failed, falling back to direct download...
)

REM --- Fallback: download the official installer ---
set "PY_VER=3.12.7"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe"
set "PY_EXE=%TEMP%\python-installer.exe"

echo        Downloading Python %PY_VER% from python.org...
powershell -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PY_URL%','%PY_EXE%') } catch { exit 1 }"
if not exist "%PY_EXE%" (
    color 0C
    echo.
    echo  ERROR: Failed to download Python installer.
    echo  Please install Python manually from:
    echo      https://www.python.org/downloads/
    echo  During install, check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo        Running Python installer (silent, with PATH and pip)...
"%PY_EXE%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_test=0
set "INSTALL_RC=%errorLevel%"
del "%PY_EXE%" >nul 2>&1
if %INSTALL_RC% neq 0 (
    color 0C
    echo.
    echo  ERROR: Python installer exited with code %INSTALL_RC%.
    echo  Please install Python manually from python.org.
    echo.
    pause
    exit /b 1
)

:python_installed
REM --- Refresh PATH for this session so 'python' is found right away ---
for /f "usebackq tokens=2,*" %%A in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul`) do set "SYS_PATH=%%B"
for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do set "USER_PATH=%%B"
set "PATH=%SYS_PATH%;%USER_PATH%;%PATH%"

REM --- Verify python is now reachable ---
where python >nul 2>&1
if %errorLevel% neq 0 (
    color 0E
    echo.
    echo  Python was installed but isn't on PATH for this session.
    echo  Please CLOSE this window and run this installer again -
    echo  the second run will pick up the new PATH and continue.
    echo.
    pause
    exit /b 0
)
echo        Python installed successfully.

:python_ok
for /f "tokens=*" %%i in ('where python') do (
    set "PYTHON_EXE=%%i"
    goto :found_python
)
:found_python
echo        Using: %PYTHON_EXE%
python --version
echo.

REM ============================================================
REM  STEP 2: Upgrade pip
REM ============================================================
echo  [2/5] Upgrading pip...
python -m pip install --upgrade pip
if %errorLevel% neq 0 (
    echo        WARNING: pip upgrade failed, continuing anyway...
)
echo.

REM ============================================================
REM  STEP 3: Install pystray
REM ============================================================
echo  [3/5] Installing pystray (system tray support)...
python -m pip install --upgrade pystray
if %errorLevel% neq 0 (
    color 0C
    echo.
    echo  ERROR: Failed to install pystray.
    echo.
    pause
    exit /b 1
)
echo.

REM ============================================================
REM  STEP 4: Install Pillow
REM ============================================================
echo  [4/5] Installing Pillow (tray icon image)...
python -m pip install --upgrade Pillow
if %errorLevel% neq 0 (
    color 0C
    echo.
    echo  ERROR: Failed to install Pillow.
    echo.
    pause
    exit /b 1
)
echo.

REM ============================================================
REM  STEP 5: Verify imports
REM ============================================================
echo  [5/5] Verifying installation...
python -c "import tkinter, pystray, PIL; print('  tkinter OK'); print('  pystray', pystray.__version__); print('  Pillow ', PIL.__version__)"
if %errorLevel% neq 0 (
    color 0C
    echo.
    echo  WARNING: Packages installed but failed to import.
    echo  Try running this installer again, or install manually:
    echo      pip install pystray Pillow
    echo.
    pause
    exit /b 1
)

color 0A
echo.
echo  ============================================================
echo    Installation complete!
echo.
echo    You can now run VR_Head-Tracking_GUI.pyw with full features:
echo      - System tray icon
echo      - Minimize to tray
echo      - Global hotkeys (start / stop tracking)
echo      - USB-style sound feedback
echo  ============================================================
echo.
pause
