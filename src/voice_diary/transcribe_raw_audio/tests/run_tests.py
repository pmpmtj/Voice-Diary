#!/usr/bin/env python3
"""
Test runner for transcribe_raw_audio module tests.

This script discovers and runs all tests for the transcribe_raw_audio module.
"""

import unittest
import os
import sys


def run_tests():
    """Discover and run all tests for the transcribe_raw_audio module."""
    # Get the directory containing this script
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create a test suite with all test modules
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern="test_*.py")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return the test result
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests and exit with appropriate code
    success = run_tests()
    sys.exit(0 if success else 1) 