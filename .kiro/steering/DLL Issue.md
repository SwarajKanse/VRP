---
inclusion: always
---
---
inclusion: manual
status: obsolete
---

# Windows DLL Loading Configuration (OBSOLETE)

**NOTE: This file is now obsolete. The project has been migrated to pure Python and no longer uses C++ extensions or DLLs.**

## Historical Context

This file previously contained instructions for Windows DLL loading when the project used a C++/Nanobind compiled extension. The DLL loading configuration is no longer needed because:

1. The project now uses pure Python (`vrp_core.py`)
2. No compiled extensions (`.pyd` files) are required
3. No MinGW or C++ runtime DLLs are needed
4. The `os.add_dll_directory()` calls have been removed from all Python files

## Migration Complete

All references to DLL loading have been removed from:
- `dashboard/app.py`
- `tests/test_solver.py`
- `test_installation.py`

The pure Python implementation works on all platforms without any DLL configuration.
