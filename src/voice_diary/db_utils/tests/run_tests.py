#!/usr/bin/env python3
"""
Test Runner for Database Utilities

This script runs all tests for the db_utils package. It can be run directly
or via pytest.
"""

import os
import sys
import unittest
import pytest

def run_tests_unittest():
    """Run tests using unittest framework."""
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover(test_dir, pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if result.wasSuccessful() else 1

def run_tests_pytest():
    """Run tests using pytest framework."""
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run pytest on the test directory
    return pytest.main(["-v", test_dir])

if __name__ == "__main__":
    # Check if unittest or pytest should be used (default to pytest)
    if len(sys.argv) > 1 and sys.argv[1] == "--unittest":
        exit_code = run_tests_unittest()
    else:
        exit_code = run_tests_pytest()
    
    sys.exit(exit_code) 