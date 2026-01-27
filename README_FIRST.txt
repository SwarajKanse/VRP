================================================================================
                    WELCOME TO VRP SOLVER!
================================================================================

Thank you for downloading VRP Solver - a high-performance Vehicle Routing
Problem solver with an interactive web dashboard.

================================================================================
                    QUICK START (3 STEPS)
================================================================================

STEP 1: Open the folder
------------------------
You're already here! This is the project root.

STEP 2: Run the setup
----------------------
Windows users:
  - Double-click: setup.bat
  - Or open Command Prompt here and run: setup.bat

Linux/macOS users:
  - Open terminal in this folder
  - Run: chmod +x setup.sh && ./setup.sh

The setup will install everything you need (takes 2-5 minutes).

STEP 3: Launch the dashboard
-----------------------------
Windows users:
  - Double-click: run_dashboard.bat

Linux/macOS users:
  - Run: chmod +x run_dashboard.sh && ./run_dashboard.sh

The dashboard will open in your browser!

================================================================================
                    WHAT YOU NEED
================================================================================

Before running setup, make sure you have:

1. Python 3.8 or higher
   Download: https://www.python.org/downloads/

2. CMake 3.15 or higher
   Download: https://cmake.org/download/

3. C++20 Compiler:
   - Windows: Visual Studio 2019+ or MinGW-w64
   - Linux: GCC 10+ (install: sudo apt install build-essential)
   - macOS: Xcode Command Line Tools (install: xcode-select --install)

The setup script will check if you have these and guide you if not.

================================================================================
                    DOCUMENTATION
================================================================================

- GETTING_STARTED.txt  - Detailed getting started guide
- QUICKSTART.md        - Step-by-step setup instructions
- README.md            - Complete documentation and API reference

Start with GETTING_STARTED.txt for a full walkthrough!

================================================================================
                    NEED HELP?
================================================================================

If setup fails:
  1. Check that you have Python, CMake, and a C++ compiler installed
  2. Read QUICKSTART.md for troubleshooting
  3. Run: python test_installation.py (after setup)

Common issues:
  - "CMake not found" → Install CMake and add to PATH
  - "Compiler not found" → Install Visual Studio, GCC, or Xcode
  - "Import error" → Run setup again: python setup.py

================================================================================

Ready? Run setup.bat (Windows) or ./setup.sh (Linux/macOS) to begin!

================================================================================
