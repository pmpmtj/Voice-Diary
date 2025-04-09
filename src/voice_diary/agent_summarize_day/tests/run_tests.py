#!/usr/bin/env python3
"""
Test runner script for agent_summarize_day module.

This script discovers and runs all tests in the current directory.
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path to ensure imports work properly
# This is only for the test runner and doesn't modify the actual code
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def run_tests():
    """Discover and run all tests in the current directory."""
    # Get the current directory (where this script is located)
    test_dir = Path(__file__).parent
    
    # Discover all tests in the current directory
    test_suite = unittest.defaultTestLoader.discover(
        str(test_dir),
        pattern="test_*.py"
    )
    
    # Create a test runner
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the tests and return the result
    result = test_runner.run(test_suite)
    
    # Return success/failure for CI/CD integration
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 