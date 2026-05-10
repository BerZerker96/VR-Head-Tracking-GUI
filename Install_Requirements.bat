@echo off
SETLOCAL EnableDelayedExpansion

:: --- SECTION 1: ELEVATION ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title VR Head Tracking GUI - Requirements Installer
echo ====================================================
echo      VR Head Tracking GUI Requirements Installer
echo ====================================================

:: --- SECTION 2: CHECK/INSTALL PYTHON ---
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python not found. Attempting to install via Winget...
    winget install -e --id Python.Python.3.12 --scope machine --accept-package-agreements --accept-source-agreements
    
    if %errorLevel% neq 0 (
        echo Winget failed. Trying PowerShell fallback...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -OutFile 'python_installer.exe'"
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del python_installer.exe
    )
    
    :: Refresh environment variables for this session
    call :RefreshPath
) else (
    echo Python is already installed.
)

:: --- SECTION 3: REPAIR PIP & INSTALL LIBRARIES ---
echo.
echo Installing/Updating required libraries...
echo ----------------------------------------------------

:: We use 'python -m' to ensure we are installing to the active interpreter
python -m pip install --upgrade pip
python -m pip install pystray Pillow

if %errorLevel% neq 0 (
    echo [ERROR] Pip failed to install requirements. 
    echo Trying to force install for current user...
    python -m pip install --user pystray Pillow
)

:: --- SECTION 4: VERIFICATION ---
echo.
echo Verifying installation...
python -c "import pystray; import PIL; print('Success: Libraries are accessible.')" >nul 2>&1

if %errorLevel% eq 0 (
    echo [OK] All requirements installed successfully.
) else (
    echo [FAIL] Verification failed. You may need to restart your PC.
)

echo.
echo Press any key to exit...
pause >nul
exit /b

:: --- HELPER: REFRESH PATH ---
:RefreshPath
for /f "tokens=2*" %%A in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
exit /b

