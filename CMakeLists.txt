cmake_minimum_required(VERSION 3.15)
project(vrp_solver CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and Nanobind
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Add nanobind cmake directory to prefix path
execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import nanobind; print(nanobind.cmake_dir())"
    OUTPUT_VARIABLE NANOBIND_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
list(APPEND CMAKE_PREFIX_PATH "${NANOBIND_CMAKE_DIR}")

find_package(nanobind CONFIG REQUIRED)

# Core library (optional, for testing C++ directly)
add_library(vrp_solver_core STATIC
    src/solver.cpp
)
target_include_directories(vrp_solver_core PUBLIC include)

# Python extension module
nanobind_add_module(vrp_core
    src/bindings.cpp
    src/solver.cpp
)
target_include_directories(vrp_core PRIVATE include)

# Output the Python module to the project root for easier testing
set_target_properties(vrp_core PROPERTIES 
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
)

# Enable optimizations for Release builds
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_options(vrp_core PRIVATE -O3 -march=native)
endif()

# Optional C++ executable
add_executable(vrp_solver_exe src/main.cpp)
target_link_libraries(vrp_solver_exe PRIVATE vrp_solver_core)

# Test executable for distance calculations
add_executable(test_distance src/test_distance.cpp)
target_link_libraries(test_distance PRIVATE vrp_solver_core)

# Test executable for nearest neighbor heuristic
add_executable(test_nearest_neighbor src/test_nearest_neighbor.cpp)
target_link_libraries(test_nearest_neighbor PRIVATE vrp_solver_core)

# Test executable for multiple routes
add_executable(test_multiple_routes src/test_multiple_routes.cpp)
target_link_libraries(test_multiple_routes PRIVATE vrp_solver_core)

# Test executable for infinite loop fix
add_executable(test_infinite_loop src/test_infinite_loop.cpp)
target_link_libraries(test_infinite_loop PRIVATE vrp_solver_core)

# Test executable for Euclidean distance
add_executable(test_euclidean src/test_euclidean.cpp)
target_link_libraries(test_euclidean PRIVATE vrp_solver_core)

# Test executable for service_time field
add_executable(test_service_time_cpp src/test_service_time_cpp.cpp)
target_link_libraries(test_service_time_cpp PRIVATE vrp_solver_core)

