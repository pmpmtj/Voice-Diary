@echo off
REM Test runner batch file for Windows
REM Executes the Python test runner script

python run_tests.py
echo.
if %ERRORLEVEL% EQU 0 (
    echo Tests completed successfully.
) else (
    echo Tests failed with errors.
)
pause 