---
inclusion: always
---
---
inclusion: fileMatch
fileMatchPattern: ['**/*.py', 'dashboard/**/*', 'tests/**/*']
---

# Windows DLL Loading Configuration

## Critical Rule: Preserve DLL Directory Setup

When working with Python files that import the `vrp_core` module, you MUST preserve the DLL loading configuration at the top of the file.

### Protected Files

The following files contain critical DLL path configuration:
- `dashboard/app.py`
- `tests/test_solver.py`

### Required Configuration Block

These files include an `os.add_dll_directory()` block that MUST be preserved:

```python
import os
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))
```

### Why This Matters

This project uses MinGW-compiled C++ extensions on Windows. The hardcoded paths resolve a specific Windows DLL loading issue where:
1. The Python extension (`vrp_core.pyd`) depends on MinGW runtime DLLs
2. Windows cannot find these DLLs without explicit directory registration
3. The `os.add_dll_directory()` calls add these paths to the DLL search path

### Rules for AI Assistants

1. **Never remove or modify** the `os.add_dll_directory()` calls in protected files
2. **Always preserve** the exact paths: `C:\mingw64\bin` and `build/`
3. **When regenerating files**, copy the DLL configuration block verbatim from the original
4. **When creating new Python files** that import `vrp_core`, include the same DLL configuration block before the import
5. **Do not suggest** alternative DLL loading methods unless explicitly requested by the user

### Failure Mode

Removing or modifying this configuration will cause immediate import failures:
```
ImportError: DLL load failed while importing vrp_core
```

### Template for New Python Files

When creating new Python files that use `vrp_core`:

```python
import os
import sys

# Critical: Add DLL directories for MinGW runtime
os.add_dll_directory(r"C:\mingw64\bin")
os.add_dll_directory(os.path.abspath("build"))

import vrp_core

# Your code here
```