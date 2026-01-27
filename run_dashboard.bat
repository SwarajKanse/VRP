@echo off
REM Quick launcher for VRP Solver Dashboard (Windows)

echo Starting VRP Solver Dashboard...
echo.
echo The dashboard will open in your browser at http://localhost:8501
echo Press Ctrl+C to stop the server
echo.

cd dashboard
streamlit run app.py
