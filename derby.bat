@echo off
cd /d "%~dp0"

echo.
echo ===============================
echo   DERBY DASHBOARD LAUNCHER
echo ===============================
echo.

REM --- Step 1: Create venv if missing ---
IF NOT EXIST venv (
    echo [1/6] Creating virtual environment...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) ELSE (
    echo [1/6] Virtual environment already exists.
)

REM --- Step 2: Activate venv ---
echo [2/6] Activating virtual environment...
call "%~dp0venv\Scripts\activate.bat"

IF ERRORLEVEL 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo Active Python:
where python
python --version
echo.

REM --- Step 3: Upgrade pip ---
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip

REM --- Step 4: Install dependencies ---
echo [4/6] Installing dependencies...

IF EXIST requirements.txt (
    pip install -r requirements.txt
) ELSE (
    echo No requirements.txt found, installing defaults...
    pip install streamlit pandas numpy plotly
)

REM --- Step 5: Check for main app ---
IF NOT EXIST streamlit_derby.py (
    echo ERROR: streamlit_derby.py not found.
    echo Current directory:
    cd
    pause
    exit /b 1
)

echo.
echo [5/6] Starting Derby dashboard...
echo.

REM --- Launch Streamlit ---
start "Derby Dashboard Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m streamlit run streamlit_derby.py --server.headless false --server.port 8502"

REM --- Wait for server ---
echo Waiting for Streamlit to start...
timeout /t 5 /nobreak >nul

REM --- Open browser ---
echo Opening browser...
start "" http://localhost:8502

echo.
echo If browser did not open, go to:
echo http://localhost:8502
echo.
pause