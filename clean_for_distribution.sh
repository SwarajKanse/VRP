#!/bin/bash
# Clean build artifacts before creating distribution ZIP

echo "Cleaning build artifacts for distribution..."
echo ""

# Remove build directory
if [ -d "build" ]; then
    rm -rf build
    echo "[OK] Removed build/"
else
    echo "[SKIP] build/ not found"
fi

# Remove Python cache
if [ -d "__pycache__" ]; then
    rm -rf __pycache__
    echo "[OK] Removed __pycache__/"
else
    echo "[SKIP] __pycache__/ not found"
fi

if [ -d "dashboard/__pycache__" ]; then
    rm -rf dashboard/__pycache__
    echo "[OK] Removed dashboard/__pycache__/"
else
    echo "[SKIP] dashboard/__pycache__/ not found"
fi

if [ -d "tests/__pycache__" ]; then
    rm -rf tests/__pycache__
    echo "[OK] Removed tests/__pycache__/"
else
    echo "[SKIP] tests/__pycache__/ not found"
fi

# Remove pytest cache
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
    echo "[OK] Removed .pytest_cache/"
else
    echo "[SKIP] .pytest_cache/ not found"
fi

# Remove hypothesis cache
if [ -d ".hypothesis" ]; then
    rm -rf .hypothesis
    echo "[OK] Removed .hypothesis/"
else
    echo "[SKIP] .hypothesis/ not found"
fi

# Remove compiled Python files
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null

# Remove compiled extensions (users will build these)
rm -f vrp_core.*.pyd vrp_core.*.so 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[OK] Removed compiled extensions"
fi

echo ""
echo "============================================================"
echo "Cleanup complete!"
echo "============================================================"
echo ""
echo "The project is now ready for distribution."
echo "Create a ZIP file of this folder and share it."
echo ""
echo "Users will run setup.sh to build everything."
echo ""
