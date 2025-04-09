#!/usr/bin/env python3
"""
Test Runner for App Scheduler module

This script runs all tests for the app_scheduler module. It can be run directly
or via pytest.
"""

import os
import sys
import unittest

def run_tests():
    """Discover and run all tests for the app_scheduler module."""
    # Get the directory containing this script
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create a test suite with all test modules
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern="test_*.py")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 