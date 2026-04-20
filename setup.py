"""
Setup script for VRP Solver (Pure Python)
Installs Python dependencies only - no compilation required
"""
import sys
import subprocess

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

def main():
    """Main setup function"""
    print("=" * 60)
    print("VRP Solver Setup (Pure Python)")
    print("=" * 60)
    
    # Install Python dependencies
    if not install_python_deps():
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

