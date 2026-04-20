@echo off
REM Quick launcher for VRP Platform (Windows)

echo Starting VRP Platform...
echo.
echo The control tower will open in your browser at http://localhost:8080
echo Press Ctrl+C to stop the server
echo.

python -m vrp_platform.ui.app
