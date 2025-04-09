#!/usr/bin/env python3
"""
Test Runner for voice_diary.dwnload_files

This script runs all the tests for the dwnload_files module with coverage reporting.
"""

import sys
import os
import pytest
from pathlib import Path

def run_tests():
    """Run the test suite with pytest."""
    # Get the directory of this script
    script_dir = Path(__file__).parent.resolve()
    
    # Get the directory of the package being tested
    package_dir = script_dir.parent
    
    # Build path for coverage report
    coverage_dir = package_dir / "tests" / "coverage"
    coverage_dir.mkdir(exist_ok=True)
    
    # Set environment variable for coverage file path
    os.environ['COVERAGE_FILE'] = str(coverage_dir / '.coverage')
    
    # Build arguments for pytest
    pytest_args = [
        # The directory containing the tests
        str(script_dir),
        # Show detailed output
        "-v",
        # Enable coverage reporting
        "--cov=src.voice_diary.dwnload_files",
        # Generate coverage report as HTML
        f"--cov-report=html:{coverage_dir}",
        # Also output coverage to terminal
        "--cov-report=term",
        # Find all test files matching the pattern
        "-k", "test_"
    ]
    
    # Run pytest with args
    exit_code = pytest.main(pytest_args)
    
    # Print information about the coverage report
    if exit_code == 0:
        print(f"\nCoverage report generated at: {coverage_dir}")
        print("Open index.html in that directory to view the report.")
    
    return exit_code

if __name__ == "__main__":
    # First make sure the test environment is set up
    try:
        from voice_diary.dwnload_files.tests.setup_test_env import check_and_install_requirements, create_test_config_if_needed
        
        # Check and install requirements
        check_and_install_requirements()
        
        # Create test config if needed
        create_test_config_if_needed()
        
    except ImportError:
        print("Could not import setup_test_env. Run setup_test_env.py first.")
        print("python -m voice_diary.dwnload_files.tests.setup_test_env --fix")
        sys.exit(1)
    
    # Run the tests
    sys.exit(run_tests()) 