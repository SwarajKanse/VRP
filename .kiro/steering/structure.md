# Project Structure

## Directory Layout

```
cpp-vrp-solver-foundation/
├── .kiro/
│   ├── specs/                    # Feature specifications
│   │   └── cpp-vrp-solver-foundation/
│   │       ├── requirements.md   # Requirements document
│   │       ├── design.md         # Design document
│   │       └── tasks.md          # Implementation tasks
│   └── steering/                 # AI assistant guidance documents
├── include/
│   └── solver.h                  # Public API: VRPSolver, Location, Customer
├── src/
│   ├── solver.cpp                # VRPSolver implementation
│   ├── bindings.cpp              # Nanobind Python bindings
│   ├── main.cpp                  # Optional C++ entry point
│   └── test_*.cpp                # C++ test executables
├── tests/
│   ├── test_solver.py            # Python unit tests
│   ├── test_fixes.py             # Additional test cases
│   └── vrp_core.*.pyd            # Compiled Python extension (Windows)
├── build/                        # CMake build output (gitignored)
├── CMakeLists.txt                # Build configuration
└── *.md                          # Documentation and verification files
```

## Key Files

### Core Implementation

- **include/solver.h**: Header-only API definitions for Location, Customer, and VRPSolver classes
- **src/solver.cpp**: Implementation of VRPSolver including:
  - Distance matrix construction
  - Haversine distance calculation
  - Nearest Neighbor heuristic
  - Constraint validation (capacity, time windows)
- **src/bindings.cpp**: Nanobind module definition exposing C++ classes to Python

### Build System

- **CMakeLists.txt**: Defines build targets:
  - `vrp_solver_core`: Static library for C++ testing
  - `vrp_core`: Python extension module
  - `vrp_solver_exe`: Optional C++ executable
  - `test_*`: C++ test executables

### Testing

- **tests/test_solver.py**: Primary test suite with pytest
- **tests/test_fixes.py**: Additional regression tests
- **src/test_*.cpp**: Standalone C++ tests for specific functionality

## Architecture Layers

### Layer 1: Data Structures (include/solver.h)

- `Location`: Geographic coordinates (latitude, longitude)
- `Customer`: Delivery point with demand and time windows
- `Route`: Type alias for `std::vector<int>` (customer IDs)

### Layer 2: Core Solver (src/solver.cpp)

- `VRPSolver::solve()`: Main entry point
- `VRPSolver::buildDistanceMatrix()`: Precompute distances
- `VRPSolver::nearestNeighborHeuristic()`: Route construction
- `VRPSolver::canAddToRoute()`: Constraint validation
- `VRPSolver::haversineDistance()`: Geographic distance calculation

### Layer 3: Python Bindings (src/bindings.cpp)

- Exposes Location, Customer, VRPSolver to Python
- Handles type conversions via Nanobind
- Module name: `vrp_core`

## Code Organization Principles

1. **Separation of Concerns**: Data structures are separate from algorithms
2. **Header-Only API**: Public interface in single header file
3. **Implementation Isolation**: Private methods in .cpp file
4. **Binding Isolation**: Python bindings in separate compilation unit
5. **Test Separation**: C++ tests in src/, Python tests in tests/

## Future Refactoring Considerations

The current structure uses Array of Structs (AoS) layout. Future optimization may convert to Struct of Arrays (SoA) for SIMD operations:

- Current: `std::vector<Customer>` (AoS)
- Future: Parallel arrays for id[], lat[], lon[], demand[], etc. (SoA)

The public API can remain unchanged during this refactoring.
