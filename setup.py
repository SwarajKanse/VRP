"""
Setup script for VRP Solver
Builds the C++ extension and installs Python dependencies
"""
import os
import sys
import subprocess
from pathlib import Path

def check_cmake():
    """Check if CMake is installed"""
    try:
        result = subprocess.run(['cmake', '--version'], capture_output=True, text=True)
        print(f"✓ CMake found: {result.stdout.split()[2]}")
        return True
    except FileNotFoundError:
        print("✗ CMake not found. Please install CMake 3.15 or higher.")
        print("  Download from: https://cmake.org/download/")
        return False

def check_compiler():
    """Check if a C++20 compiler is available"""
    compilers = []
    
    # Check for GCC
    try:
        result = subprocess.run(['g++', '--version'], capture_output=True, text=True)
        version = result.stdout.split('\n')[0]
        compilers.append(f"✓ GCC found: {version}")
    except FileNotFoundError:
        pass
    
    # Check for Clang
    try:
        result = subprocess.run(['clang++', '--version'], capture_output=True, text=True)
        version = result.stdout.split('\n')[0]
        compilers.append(f"✓ Clang found: {version}")
    except FileNotFoundError:
        pass
    
    # Check for MSVC (Windows)
    try:
        result = subprocess.run(['cl'], capture_output=True, text=True)
        if 'Microsoft' in result.stderr:
            compilers.append("✓ MSVC found")
    except FileNotFoundError:
        pass
    
    if compilers:
        for compiler in compilers:
            print(compiler)
        return True
    else:
        print("✗ No C++20 compiler found.")
        print("  Please install GCC 10+, Clang 10+, or MSVC 19.29+")
        return False

def install_python_deps():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✓ Python dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install Python dependencies")
        return False

def build_cpp_extension():
    """Build the C++ extension using CMake"""
    print("\n🔨 Building C++ extension...")
    
    build_dir = Path('build')
    build_dir.mkdir(exist_ok=True)
    
    try:
        # Configure
        print("  Configuring CMake...")
        subprocess.run(['cmake', '..'], cwd=build_dir, check=True)
        
        # Build
        print("  Building...")
        subprocess.run(['cmake', '--build', '.', '--config', 'Release'], cwd=build_dir, check=True)
        
        print("✓ C++ extension built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("VRP Solver Setup")
    print("=" * 60)
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    cmake_ok = check_cmake()
    compiler_ok = check_compiler()
    
    if not (cmake_ok and compiler_ok):
        print("\n❌ Prerequisites not met. Please install missing components.")
        return False
    
    # Install Python dependencies
    if not install_python_deps():
        return False
    
    # Build C++ extension
    if not build_cpp_extension():
        return False
    
    print("\n" + "=" * 60)
    print("✅ Setup completed successfully!")
    print("=" * 60)
    
    # Run verification test
    print("\n🧪 Running verification tests...")
    try:
        subprocess.run([sys.executable, 'test_installation.py'], check=True)
    except subprocess.CalledProcessError:
        print("\n⚠️  Verification tests failed, but setup completed.")
        print("You can manually run: python test_installation.py")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. Run tests: python -m pytest tests/ -v")
    print("  2. Start dashboard: cd dashboard && streamlit run app.py")
    print("  3. Or use quick launcher: run_dashboard.bat (Windows) or ./run_dashboard.sh (Linux/macOS)")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
