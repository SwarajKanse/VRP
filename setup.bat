@echo off
REM Windows setup script for VRP Solver

echo ============================================================
echo VRP Solver Setup (Windows)
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

REM Run setup
python setup.py
if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. Please check the error messages above.
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
pause
