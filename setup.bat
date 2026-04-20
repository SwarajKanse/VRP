@echo off
REM Windows setup script for VRP Solver (Pure Python)

echo ============================================================
echo VRP Solver Setup (Windows) - Pure Python
echo ============================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found

REM Install dependencies
echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Setup completed successfully!
echo ============================================================
echo.
echo To run the dashboard:
echo   cd dashboard
echo   streamlit run app.py
echo.
echo To run tests:
echo   python -m pytest tests/ -v
echo.
echo To verify installation:
echo   python test_installation.py
echo.
pause
