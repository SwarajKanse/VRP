# Technology Stack

## Core Technologies

- **Language**: C++20 (required standard)
- **Build System**: CMake 3.15+
- **Python Bindings**: Nanobind (modern, lightweight binding library)
- **Testing Framework**: pytest (Python) with hypothesis for property-based testing

## Build System

The project uses CMake with the following key configurations:

- C++20 standard enforcement (`CMAKE_CXX_STANDARD 20`)
- Nanobind integration via `nanobind_add_module`
- Static core library (`vrp_solver_core`) for C++ testing
- Python extension module (`vrp_core`) for Python integration
- Release mode optimizations: `-O3 -march=native`

## Common Commands

### Building the Project

```bash
# Configure and build
mkdir build && cd build
cmake ..
cmake --build .

# Build with Release optimizations
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build .
```

### Running Tests

```bash
# Run Python tests
python -m pytest tests/ -v

# Run property-based tests with more iterations
python -m pytest tests/ -v --hypothesis-profile=thorough

# Run specific test file
python -m pytest tests/test_solver.py -v
```

### Running C++ Test Executables

```bash
# From build directory
./test_distance
./test_nearest_neighbor
./test_multiple_routes
./test_infinite_loop
```

### Cleaning Build Artifacts

```bash
# Remove build directory
rm -rf build/

# Remove Python compiled modules
rm -f *.pyd *.so
```

## Dependencies

### Required

- CMake 3.15 or higher
- C++20 compatible compiler (GCC 10+, Clang 10+, MSVC 19.29+)
- Python 3.8+ with development headers
- Nanobind (installed via pip: `pip install nanobind`)

### Testing

- pytest: `pip install pytest`
- hypothesis: `pip install hypothesis` (for property-based testing)

## Platform Notes

### Windows

- The Python extension is built as `.pyd` file
- May require Visual C++ Redistributable for runtime
- CMake outputs to `build/Release/` by default on Windows
- Use `os.add_dll_directory()` in Python to load the module correctly

### Linux/macOS

- The Python extension is built as `.so` file
- Standard CMake output to `build/` directory
- May need to set `LD_LIBRARY_PATH` or `DYLD_LIBRARY_PATH` for dynamic linking
