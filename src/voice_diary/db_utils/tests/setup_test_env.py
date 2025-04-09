#!/usr/bin/env python3
"""
Setup Test Environment for Database Utilities

This script sets up the testing environment by creating a test configuration
and ensuring all required dependencies are installed.
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path

def check_and_install_requirements():
    """Check and install required testing packages."""
    required_packages = [
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
        'psycopg2-binary>=2.9.5'
    ]
    
    print("Checking for required packages...")
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name)
            print(f"✓ {package_name} is already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def create_test_config_if_needed():
    """Create test configuration files if they don't exist."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    test_data_dir = script_dir / 'test_data'
    
    # Ensure test_data directory exists
    test_data_dir.mkdir(exist_ok=True)
    
    # Check if test config already exists
    test_config_path = test_data_dir / 'test_db_utils_config.json'
    if not test_config_path.exists():
        print("Creating test configuration file...")
        test_config = {
            "database": {
                "default_url": "postgresql://test:test@localhost/testdb"
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "log_file": "test_db_utils.log",
                "max_size_bytes": 1048576,
                "backup_count": 3
            },
            "test_data": {
                "sample_transcription": "This is a sample transcription for testing purposes",
                "sample_categories": ["Meeting", "Personal", "Ideas", "Tasks"]
            }
        }
        
        with open(test_config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        print(f"Created test configuration at {test_config_path}")
    else:
        print(f"Test configuration already exists at {test_config_path}")

def fix_common_issues():
    """Fix common test issues."""
    print("\nFIXING COMMON TEST ISSUES")
    print("-------------------------")
    
    # Check for Python path issues
    project_root = Path(__file__).parent.parent.parent.parent.parent.absolute()
    print(f"Project root identified as: {project_root}")
    
    # Add project root to PYTHONPATH if needed
    sys_path_file = Path.home() / ".pth" / "voice_diary_test.pth"
    if not sys_path_file.parent.exists():
        sys_path_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not sys_path_file.exists():
        print(f"Creating .pth file to add project root to Python path: {sys_path_file}")
        with open(sys_path_file, 'w') as f:
            f.write(str(project_root))
        print("✓ Added project root to Python path")
    else:
        print("✓ Project path file already exists")
    
    # Check if setup.py exists at project root, create if not
    setup_py_path = project_root / "setup.py"
    if not setup_py_path.exists():
        print("Creating basic setup.py for development mode installation...")
        setup_py_content = """
from setuptools import setup, find_packages

setup(
    name="voice_diary",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
"""
        with open(setup_py_path, 'w') as f:
            f.write(setup_py_content)
        
        # Install in development mode
        try:
            print("Installing package in development mode...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e', '.'], cwd=project_root)
            print("✓ Installed voice_diary package in development mode")
        except subprocess.CalledProcessError:
            print("! Could not install package in development mode. You may need to run: pip install -e .")
    else:
        print("✓ setup.py already exists")
    
    # Check if there's a __init__.py in each directory
    module_dirs = [
        project_root / "src" / "voice_diary",
        project_root / "src" / "voice_diary" / "db_utils",
        project_root / "src" / "voice_diary" / "db_utils" / "tests",
    ]
    
    for dir_path in module_dirs:
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            print(f"Creating __init__.py in {dir_path.relative_to(project_root)}")
            with open(init_file, 'w') as f:
                f.write('"""Voice Diary package."""\n')
            print(f"✓ Created {init_file}")
        else:
            print(f"✓ {init_file} already exists")
    
    print("\nCommon issues fixed. Please try running the tests again.")

def main():
    """Main function to set up the test environment."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Setup the test environment for voice_diary.db_utils')
    parser.add_argument('--fix', action='store_true', help='Fix common test issues')
    args = parser.parse_args()
    
    print("Setting up test environment for voice_diary.db_utils...")
    
    # Check and install required packages
    check_and_install_requirements()
    
    # Create test configuration
    create_test_config_if_needed()
    
    # Fix common issues if requested
    if args.fix:
        fix_common_issues()
    
    print("\nTest environment setup complete!")
    print("To run tests, use: python -m voice_diary.db_utils.tests.run_tests")
    
    # Provide additional help for fixing issues
    if not args.fix:
        print("\nIf you encounter issues running tests, try:")
        print("python -m voice_diary.db_utils.tests.setup_test_env --fix")

if __name__ == "__main__":
    main() 