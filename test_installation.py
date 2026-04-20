"""
Quick installation verification script
Run this after setup to verify everything is working
"""
import sys

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing Python dependencies...")
    
    required_modules = [
        'pytest',
        'hypothesis',
        'streamlit',
        'pandas',
        'plotly',
        'reportlab'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} - MISSING")
            missing.append(module)
    
    if missing:
        print(f"\n❌ Missing modules: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✓ All Python dependencies installed\n")
    return True

def test_vrp_module():
    """Test that the pure Python VRP module can be loaded"""
    print("Testing VRP module...")
    
    try:
        import vrp_core
        print("  ✓ vrp_core module loaded")
        
        # Test basic functionality
        loc = vrp_core.Location(19.065, 72.835)
        print(f"  ✓ Location created: ({loc.latitude}, {loc.longitude})")
        
        customer = vrp_core.Customer(0, loc, 0.0, 0.0, 600.0, 0.0)
        print(f"  ✓ Customer created: ID {customer.id}")
        
        solver = vrp_core.VRPSolver()
        print("  ✓ VRPSolver instantiated")
        
        print("✓ Pure Python VRP module working correctly\n")
        return True
        
    except ImportError as e:
        print(f"  ✗ Failed to import vrp_core: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure vrp_core.py is in the project root")
        print("  2. Check Python path includes project root")
        return False
    except Exception as e:
        print(f"  ✗ Error testing module: {e}")
        return False

def test_sample_solve():
    """Test a simple VRP solve"""
    print("Testing VRP solver...")
    
    try:
        import vrp_core
        
        # Create simple problem
        depot = vrp_core.Customer(
            0,
            vrp_core.Location(19.065, 72.835),
            0.0, 0.0, 600.0, 0.0
        )
        
        customer1 = vrp_core.Customer(
            1,
            vrp_core.Location(19.070, 72.840),
            10.0, 0.0, 600.0, 10.0
        )
        
        customer2 = vrp_core.Customer(
            2,
            vrp_core.Location(19.075, 72.845),
            15.0, 0.0, 600.0, 10.0
        )
        
        # Solve
        solver = vrp_core.VRPSolver()
        customers = [depot, customer1, customer2]
        vehicle_capacities = [50.0, 50.0]
        
        routes = solver.solve(customers, vehicle_capacities)
        
        print(f"  ✓ Solved VRP with {len(customers)} customers")
        print(f"  ✓ Generated {len(routes)} routes")
        for i, route in enumerate(routes):
            print(f"    Route {i}: {route}")
        
        print("✓ VRP solver working correctly\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Error solving VRP: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("VRP Solver Installation Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Python Dependencies", test_imports()))
    
    # Test VRP module
    results.append(("VRP Module", test_vrp_module()))
    
    # Test solver
    results.append(("VRP Solver", test_sample_solve()))
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ All tests passed! Pure Python installation successful.")
        print("\nNext steps:")
        print("  1. Run dashboard: cd dashboard && streamlit run app.py")
        print("  2. Run full tests: python -m pytest tests/ -v")
        print("  3. Check QUICKSTART.md for usage examples")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        print("See QUICKSTART.md for troubleshooting help.")
    
    print()
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
