@echo off
REM Clean build artifacts before creating distribution ZIP

echo Cleaning build artifacts for distribution...
echo.

REM Remove build directory
if exist build (
    rmdir /s /q build
    echo [OK] Removed build/
) else (
    echo [SKIP] build/ not found
)

REM Remove Python cache
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo [OK] Removed __pycache__/
) else (
    echo [SKIP] __pycache__/ not found
)

if exist dashboard\__pycache__ (
    rmdir /s /q dashboard\__pycache__
    echo [OK] Removed dashboard/__pycache__/
) else (
    echo [SKIP] dashboard/__pycache__/ not found
)

if exist tests\__pycache__ (
    rmdir /s /q tests\__pycache__
    echo [OK] Removed tests/__pycache__/
) else (
    echo [SKIP] tests/__pycache__/ not found
)

REM Remove pytest cache
if exist .pytest_cache (
    rmdir /s /q .pytest_cache
    echo [OK] Removed .pytest_cache/
) else (
    echo [SKIP] .pytest_cache/ not found
)

REM Remove hypothesis cache
if exist .hypothesis (
    rmdir /s /q .hypothesis
    echo [OK] Removed .hypothesis/
) else (
    echo [SKIP] .hypothesis/ not found
)

REM Remove compiled Python files
del /q *.pyc 2>nul
del /q dashboard\*.pyc 2>nul
del /q tests\*.pyc 2>nul

REM Remove compiled extensions (users will build these)
del /q vrp_core.*.pyd 2>nul
del /q vrp_core.*.so 2>nul
if %errorlevel% equ 0 (
    echo [OK] Removed compiled extensions
)

echo.
echo ============================================================
echo Cleanup complete!
echo ============================================================
echo.
echo The project is now ready for distribution.
echo Create a ZIP file of this folder and share it.
echo.
echo Users will run setup.bat to build everything.
echo.
pause
