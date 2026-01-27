# Quick Start Guide

This guide will help you set up and run the VRP Solver in minutes.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8 or higher**
   - Windows: Download from [python.org](https://www.python.org/downloads/)
   - Linux: `sudo apt install python3 python3-pip` (Ubuntu/Debian)
   - macOS: `brew install python3`

2. **CMake 3.15 or higher**
   - Windows: Download from [cmake.org](https://cmake.org/download/)
   - Linux: `sudo apt install cmake` (Ubuntu/Debian)
   - macOS: `brew install cmake`

3. **C++20 Compatible Compiler**
   - Windows: Visual Studio 2019+ or MinGW-w64
   - Linux: GCC 10+ (`sudo apt install g++`)
   - macOS: Xcode Command Line Tools (`xcode-select --install`)

## Installation

### Option 1: Automated Setup (Recommended)

#### Windows
```bash
# Double-click setup.bat or run in Command Prompt:
setup.bat
```

#### Linux/macOS
```bash
# Make the script executable and run:
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Build the C++ extension:**
```bash
mkdir build
cd build
cmake ..
cmake --build . --config Release
cd ..
```

## Running the Application

### 1. Run the Dashboard (Recommended for first-time users)

```bash
cd dashboard
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### 2. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_solver.py -v
```

### 3. Use Python API

```python
import os
os.add_dll_directory(r"C:\mingw64\bin")  # Windows only
os.add_dll_directory(os.path.abspath("build"))  # Windows only

import vrp_core

# Create depot
depot = vrp_core.Customer(
    id=0,
    location=vrp_core.Location(19.065, 72.835),
    demand=0.0,
    start_window=0.0,
    end_window=600.0,
    service_time=0.0
)

# Create customers
customer1 = vrp_core.Customer(
    id=1,
    location=vrp_core.Location(19.070, 72.840),
    demand=10.0,
    start_window=0.0,
    end_window=600.0,
    service_time=10.0
)

# Solve
solver = vrp_core.VRPSolver()
vehicle_capacities = [50.0, 50.0]
routes = solver.solve([depot, customer1], vehicle_capacities)

print(f"Routes: {routes}")
```

## Dashboard Features

The Streamlit dashboard provides:

1. **CSV Upload**: Upload order manifests with package details
2. **Fleet Configuration**: Define vehicle types with capacities and fuel efficiency
3. **Route Optimization**: Solve VRP with heterogeneous fleet
4. **3D Packing Visualization**: See how packages are loaded
5. **Cost Analysis**: View fuel consumption and labor costs
6. **Manifest Export**: Download driver instructions (CSV/PDF)

## Troubleshooting

### Build Errors

**Error: CMake not found**
- Install CMake from [cmake.org](https://cmake.org/download/)
- Add CMake to your system PATH

**Error: Compiler not found**
- Windows: Install Visual Studio 2019+ or MinGW-w64
- Linux: `sudo apt install build-essential`
- macOS: `xcode-select --install`

**Error: nanobind not found**
- Run: `pip install nanobind`

### Runtime Errors

**ImportError: DLL load failed (Windows)**
- Ensure MinGW is installed and in PATH
- Update the DLL paths in your Python script:
  ```python
  import os
  os.add_dll_directory(r"C:\mingw64\bin")
  os.add_dll_directory(os.path.abspath("build"))
  ```

**ModuleNotFoundError: No module named 'vrp_core'**
- Rebuild the C++ extension: `python setup.py`
- Check that `vrp_core.*.pyd` (Windows) or `vrp_core.*.so` (Linux/macOS) exists in the project root

### Dashboard Issues

**Streamlit not found**
- Run: `pip install streamlit`

**Dashboard won't start**
- Check that you're in the `dashboard` directory
- Verify all dependencies are installed: `pip install -r requirements.txt`

## Project Structure

```
vrp-solver/
├── src/                    # C++ source files
├── include/                # C++ headers
├── dashboard/              # Streamlit dashboard
├── tests/                  # Test suite
├── build/                  # Build output (generated)
├── CMakeLists.txt          # Build configuration
├── requirements.txt        # Python dependencies
├── setup.py                # Setup script
├── setup.bat               # Windows setup
├── setup.sh                # Linux/macOS setup
└── README.md               # Full documentation
```

## Next Steps

1. **Explore the Dashboard**: Upload `sample_manifest.csv` to see the solver in action
2. **Read the Documentation**: Check `README.md` for detailed API reference
3. **Run the Tests**: Verify everything works with `pytest tests/ -v`
4. **Customize**: Modify fleet configurations and packing constraints

## Getting Help

- Check `README.md` for detailed documentation
- Review test files in `tests/` for usage examples
- Examine `dashboard/app.py` for integration examples

## License

[Add your license information here]
