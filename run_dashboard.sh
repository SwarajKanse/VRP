#!/bin/bash
# Quick launcher for VRP Platform (Linux/macOS)

echo "Starting VRP Platform..."
echo ""
echo "The control tower will open in your browser at http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m vrp_platform.ui.app
