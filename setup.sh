#!/bin/bash
# Linux/macOS setup script for VRP Solver

echo "============================================================"
echo "VRP Solver Setup (Linux/macOS)"
echo "============================================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"

# Run setup
python3 setup.py
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Setup failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "============================================================"
echo "Setup completed successfully!"
echo "============================================================"
echo ""
echo "To run the dashboard:"
echo "  cd dashboard"
echo "  streamlit run app.py"
echo ""
echo "To run tests:"
echo "  python3 -m pytest tests/ -v"
echo ""
