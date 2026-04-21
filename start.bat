@echo off
setlocal EnableDelayedExpansion
REM =====================================================================
REM  ETH Trading Bot - Setup and Run (Windows)
REM  Hyperliquid DEX -- No KYC -- Paper/Live Trading
REM =====================================================================

set "PROJECT_DIR=%~dp0"
set "BOT_DIR=%PROJECT_DIR%bot"
set "VENV_DIR=%BOT_DIR%\venv"
set "PYTHON=python"
set "NODE=npm"
set "ENV_FILE=%BOT_DIR%\.env"
set "ENV_EXAMPLE=%BOT_DIR%\.env.example"

title ETH Trading Bot v2.4.1

echo.
echo  ========================================================
echo            ETH Trading Bot - Setup and Run
echo       Hyperliquid DEX -- No KYC -- AI Optimized
echo  ========================================================
echo.

REM ==================== CHECK PREREQUISITES ====================

echo [1/7] Checking prerequisites...
echo.

REM Check Python
where %PYTHON% >nul 2>&1
if errorlevel 1 (
    echo  [FAIL] Python is not installed or not in PATH.
    echo         Download from: https://www.python.org/downloads/
    echo         IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    goto :error
) else (
    for /f "tokens=2 delims= " %%v in ('%PYTHON% --version 2^>^&1') do set PYVER=%%v
    echo  [OK]   Python !PYVER!
)

REM Check Node.js
set "DASHBOARD_OK=0"
where %NODE% >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Node.js is not installed. Dashboard will not be available.
    echo         Download from: https://nodejs.org/  ^(choose 22.x LTS^)
    echo         Bot will still work - API at http://localhost:3003
) else (
    for /f "tokens=1" %%v in ('node --version 2^>^&1') do set NODEVER=%%v
    echo  [OK]   Node.js !NODEVER!
    REM Check if Node version is high enough for Prisma
    for /f "tokens=1 delims=v" %%v in ('node --version 2^>^&1') do set NODEVER_NUM=%%v
    REM Simple version check: if major version is 20, check minor
    echo !NODEVER_NUM! | findstr /r "^22\." >nul && set "DASHBOARD_OK=1"
    echo !NODEVER_NUM! | findstr /r "^24\." >nul && set "DASHBOARD_OK=1"
    echo !NODEVER_NUM! | findstr /r "^2[5-9]\." >nul && set "DASHBOARD_OK=1"
    echo !NODEVER_NUM! | findstr /r "^[3-9][0-9]" >nul && set "DASHBOARD_OK=1"
    if "!DASHBOARD_OK!"=="0" (
        echo  [WARN] Node.js !NODEVER_NUM! is too old for Prisma ^(needs 20.19+ / 22.12+ / 24+^).
        echo         Dashboard will be skipped. Upgrade Node.js from:
        echo         https://nodejs.org/
        echo         Bot will still work - API at http://localhost:3003
    )
)

REM Check Git
where git >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Git not found - version updates will need manual install.
) else (
    echo  [OK]   Git installed.
)

echo.

REM ==================== PYTHON VIRTUAL ENVIRONMENT ====================

echo [2/7] Setting up Python virtual environment...
echo.

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  Creating virtual environment in: bot\venv
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [FAIL] Failed to create virtual environment.
        echo         Try running: python -m pip install --upgrade setuptools wheel
        echo         Then re-run this script.
        echo.
        goto :error
    )
    echo  [OK]   Virtual environment created.
) else (
    echo  [OK]   Virtual environment already exists.
)

REM Activate venv
echo  Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo  [FAIL] Failed to activate virtual environment.
    echo.
    goto :error
)
echo  [OK]   Virtual environment activated.
echo.

REM ==================== PYTHON DEPENDENCIES ====================

echo [3/7] Installing Python packages...
echo.

echo  Upgrading pip...
python -m pip install --upgrade pip -q 2>nul
echo  [OK]   pip upgraded.

if not exist "%BOT_DIR%\requirements.txt" (
    echo  [FAIL] requirements.txt not found in bot\ directory.
    echo         Make sure you cloned the repo correctly.
    echo.
    goto :error
)

echo  Installing packages from requirements.txt ^(this may take a minute^)...
pip install -r "%BOT_DIR%\requirements.txt" -q 2>nul
if errorlevel 1 (
    echo.
    echo  [WARN] Some packages failed to install. Retrying with default pip...
    pip install -r "%BOT_DIR%\requirements.txt"
    if errorlevel 1 (
        echo  [FAIL] Failed to install Python packages.
        echo         Try manually: cd bot ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
        echo.
        goto :error
    )
)
echo  [OK]   All Python packages installed.
echo.

REM ==================== .ENV CONFIGURATION ====================

echo [4/7] Configuring environment...
echo.

if not exist "%ENV_FILE%" (
    if exist "%ENV_EXAMPLE%" (
        copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
        echo  [OK]   Created .env from .env.example
        echo.
        echo  ========================================================
        echo   IMPORTANT: Edit bot\.env before going live!
        echo.
        echo   - Set TRADING_MODE=paper for testnet ^(safe^)
        echo   - Set TRADING_MODE=live for real money
        echo   - Add WALLET_ADDRESS for account tracking
        echo   - Add WALLET_PRIVATE_KEY only for live trading
        echo.
        echo   The file will open now for you to edit.
        echo  ========================================================
        echo.
        timeout /t 3 >nul
        notepad "%ENV_FILE%"
    ) else (
        echo  [WARN] Neither .env nor .env.example found.
        echo         Creating a default .env file...
        (
            echo # ETH Trading Bot Configuration
            echo TRADING_MODE=paper
            echo WALLET_PRIVATE_KEY=
            echo WALLET_ADDRESS=
            echo MAX_RISK_PER_TRADE_PCT=1.5
            echo MAX_DAILY_RISK_PCT=7.0
            echo MAX_CONCURRENT_POSITIONS=5
            echo DEFAULT_TIMEFRAME=1h
            echo LOG_LEVEL=INFO
            echo LOG_FILE=logs\bot.log
        ) > "%ENV_FILE%"
        echo  [OK]   Default .env created. Edit bot\.env to configure.
        notepad "%ENV_FILE%"
    )
) else (
    echo  [OK]   .env file found.
)
echo.

REM Create required directories
if not exist "%BOT_DIR%\data" mkdir "%BOT_DIR%\data"
if not exist "%BOT_DIR%\logs" mkdir "%BOT_DIR%\logs"
echo  [OK]   Data and logs directories ready.
echo.

REM ==================== NODE.JS DEPENDENCIES ====================

echo [5/7] Setting up Next.js dashboard...
echo.

if "!DASHBOARD_OK!"=="0" (
    echo  [SKIP] Dashboard skipped - Node.js needs upgrade to v22+ LTS.
    echo         Bot API will still be available at http://localhost:3003
    goto :skip_dashboard
)

if not exist "%PROJECT_DIR%package.json" (
    echo  [WARN] package.json not found. Skipping dashboard setup.
    echo         The bot will still work without the dashboard.
    echo         Dashboard API available at: http://localhost:3003
    goto :skip_dashboard
)

if not exist "%PROJECT_DIR%\node_modules" (
    echo  Installing Node.js packages ^(this may take a few minutes^)...
    cd /d "%PROJECT_DIR%"
    call %NODE% install
    if errorlevel 1 (
        echo  [WARN] npm install had issues. Retrying with --force...
        call %NODE% install --force
    )
    echo  [OK]   Node.js packages installed.
) else (
    echo  [OK]   node_modules already exists.
)

REM Build Next.js (always rebuild to get latest changes)
echo  Building Next.js dashboard...
cd /d "%PROJECT_DIR%"
call %NODE% run build
if errorlevel 1 (
    echo  [WARN] Build failed. Dashboard will use dev mode.
) else (
    echo  [OK]   Dashboard build complete.
)
echo.

:skip_dashboard

REM ==================== CHOOSE RUN MODE ====================

echo [6/7] Select run mode...
echo.
echo  -------------------------------------------------------
echo   1. Bot + API Server + Dashboard  ^(Recommended^)
echo   2. Bot + API Server only    ^(No dashboard^)
echo   3. API Server only           ^(No trading^)
echo   4. Dashboard only            ^(No bot^)
echo  -------------------------------------------------------
echo.

if "!DASHBOARD_OK!"=="0" (
    echo  [NOTE] Dashboard unavailable. Auto-selecting mode 2...
    set "MODE=2"
    echo.
    goto :skip_mode_select
)

set /p MODE="  Enter choice [1-4]: "
if "%MODE%"=="" set MODE=1

:skip_mode_select
echo.

REM ==================== LAUNCH ====================

echo [7/7] Launching...
echo.

REM Kill any existing processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3003 " ^| findstr "LISTENING"') do (
    echo  Stopping existing API server on port 3003 ^(PID: %%a^)...
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    echo  Stopping existing dashboard on port 3000 ^(PID: %%a^)...
    taskkill /PID %%a /F >nul 2>&1
)

REM Read TRADING_MODE from .env for display
set TRADING_DISPLAY=paper
if exist "%ENV_FILE%" (
    for /f "tokens=2 delims==" %%m in ('findstr /i "TRADING_MODE" "%ENV_FILE%"') do (
        set TRADING_DISPLAY=%%m
    )
)

if "%MODE%"=="1" goto :run_all
if "%MODE%"=="2" goto :run_bot_only
if "%MODE%"=="3" goto :run_api_only
if "%MODE%"=="4" goto :run_dashboard_only
echo  Invalid choice. Starting Bot + API Server + Dashboard...
goto :run_all

:run_all
echo  ========================================================
echo   Starting: Bot + API Server + Dashboard
echo   Mode:     !TRADING_DISPLAY!
echo   API:      http://localhost:3003
echo   Dashboard: http://localhost:3000
echo  ========================================================
echo.
echo  Close this window to stop the bot.
echo  Dashboard runs in a separate window.
echo.
REM Launch dashboard in new window
start "ETH Dashboard - http://localhost:3000" cmd /c "cd /d %PROJECT_DIR% && %NODE% start"
REM Auto-open browser when dashboard is ready (runs minimized, exits after opening)
start /min "" "%PROJECT_DIR%open-browser.bat"
REM Launch bot in this window
cd /d "%BOT_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
python main.py --api --port 3003
goto :done

:run_bot_only
echo  ========================================================
echo   Starting: Bot + API Server
echo   Mode:     !TRADING_DISPLAY!
echo   API:      http://localhost:3003
echo  ========================================================
echo.
echo  Close this window to stop the bot.
echo.
cd /d "%BOT_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
python main.py --api --port 3003
goto :done

:run_api_only
echo  ========================================================
echo   Starting: API Server only ^(no trading, dashboard only^)
echo   API:      http://localhost:3003
echo  ========================================================
echo.
echo  Close this window to stop the API server.
echo.
cd /d "%BOT_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
python main.py --api-only --port 3003
goto :done

:run_dashboard_only
echo  ========================================================
echo   Starting: Dashboard only ^(bot API must run separately^)
echo   Dashboard: http://localhost:3000
echo  ========================================================
echo.
echo  Close this window to stop the dashboard.
echo.
cd /d "%PROJECT_DIR%"
REM Auto-open browser when dashboard is ready (runs minimized, exits after opening)
start /min "" "%PROJECT_DIR%open-browser.bat"
%NODE% start
goto :done

:done
echo.
echo  ========================================================
echo   Bot has stopped.
echo   To run again, just double-click this file.
echo  ========================================================
echo.
pause
exit /b 0

:error
echo.
echo  ========================================================
echo   SETUP FAILED
echo   Please fix the errors above and try again.
echo  ========================================================
echo.
pause
exit /b 1
