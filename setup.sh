#!/bin/bash
# Linux/macOS setup script for VRP Solver (Pure Python)

echo "============================================================"
echo "VRP Solver Setup (Linux/macOS) - Pure Python"
echo "============================================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to install dependencies."
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
echo "To verify installation:"
echo "  python3 test_installation.py"
echo ""
