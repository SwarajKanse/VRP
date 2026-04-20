"""Quick installation verification for the platform-only VRP system."""

from __future__ import annotations

import sys


RUNTIME_MODULES = [
    "alembic",
    "nicegui",
    "pandas",
    "pydantic",
    "pydantic_settings",
    "redis",
    "reportlab",
    "requests",
    "rq",
    "sqlalchemy",
]


def test_imports() -> bool:
    """Verify that the platform runtime dependencies import cleanly."""

    print("Testing Python dependencies...")
    missing: list[str] = []
    for module in RUNTIME_MODULES:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError:
            print(f"  [MISSING] {module}")
            missing.append(module)

    if missing:
        print(f"\n[FAIL] Missing modules: {', '.join(missing)}")
        print("Run: python -m pip install -e .")
        return False

    print("[OK] Runtime dependencies installed\n")
    return True


def test_platform_bootstrap() -> bool:
    """Boot the platform and execute a demo planning run."""

    print("Testing platform bootstrap...")
    try:
        from vrp_platform.bootstrap import bootstrap_platform, build_demo_request

        app = bootstrap_platform()
        response = app.solve_plan(build_demo_request())

        print(f"  [OK] Platform bootstrapped with database: {app.settings.database_url}")
        print(f"  [OK] Demo run created: {response.run_id}")
        print(f"  [OK] Route count: {len(response.routes)}")
        print(f"  [OK] Unassigned orders: {len(response.unassigned_orders)}")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic entrypoint
        print(f"  [ERROR] Platform bootstrap failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


def main() -> int:
    """Run installation checks."""

    print("=" * 60)
    print("VRP Platform Installation Verification")
    print("=" * 60)
    print()

    results = [
        ("Python Dependencies", test_imports()),
        ("VRP Platform", test_platform_bootstrap()),
    ]

    print("=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
        all_passed = all_passed and passed

    print("=" * 60)
    if all_passed:
        print("\n[PASS] Platform installation verified.")
        print("\nNext steps:")
        print("  1. Run the app: python -m vrp_platform.ui.app")
        print("  2. Run focused platform checks: python -m pytest tests/platform -q")
        print("  3. Configure VRP_DATABASE_URL for PostgreSQL when moving beyond local SQLite")
    else:
        print("\n[FAIL] Some checks failed. Review the errors above.")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
