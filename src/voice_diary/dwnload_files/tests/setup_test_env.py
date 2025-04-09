#!/usr/bin/env python3
"""
Setup Test Environment for Google Drive Download Audio Files

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
        'pytest-mock>=3.10.0',
        'google-api-python-client>=2.0.0',
        'google-auth-httplib2>=0.1.0',
        'google-auth-oauthlib>=0.4.0'
    ]
    
    print("Checking for required packages...")
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name.replace('-', '_'))
            print(f"[OK] {package_name} is already installed")
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
    test_config_path = test_data_dir / 'test_config_dwnld_from_gdrive.json'
    if not test_config_path.exists():
        print("Creating test configuration file...")
        test_config = {
            "auth": {
                "credentials_file": "test_credentials.json",
                "token_file": "test_token.pickle"
            },
            "api": {
                "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
            },
            "folders": {
                "target_folders": ["TestAudioFiles"]
            },
            "audio_downloads_path": {
                "downloads_dir": "test_downloads"
            },
            "audio_file_types": {
                "include": [".mp3", ".wav", ".m4a"]
            },
            "download": {
                "add_timestamps": True,
                "timestamp_format": "%Y%m%d_%H%M%S",
                "delete_after_download": False
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                "log_file": "test_dwnld_audio.log",
                "max_size_bytes": 1048576,
                "backup_count": 3
            },
            "dry_run": False
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
        print("[OK] Added project root to Python path")
    else:
        print("[OK] Project path file already exists")
    
    # Check if there's a __init__.py in each directory
    module_dirs = [
        project_root / "src" / "voice_diary",
        project_root / "src" / "voice_diary" / "dwnload_files",
        project_root / "src" / "voice_diary" / "dwnload_files" / "tests",
    ]
    
    for dir_path in module_dirs:
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            print(f"Creating __init__.py in {dir_path.relative_to(project_root)}")
            with open(init_file, 'w') as f:
                f.write('"""Voice Diary package."""\n')
            print(f"[OK] Created {init_file}")
        else:
            print(f"[OK] {init_file} already exists")
    
    # Create mock credentials file for testing
    script_dir = Path(__file__).parent
    credentials_dir = script_dir / 'test_data' / 'gdrive_credentials'
    credentials_dir.mkdir(exist_ok=True, parents=True)
    
    mock_credentials_file = credentials_dir / 'test_credentials.json'
    if not mock_credentials_file.exists():
        print(f"Creating mock credentials file for testing")
        mock_credentials = {
            "installed": {
                "client_id": "test-client-id.apps.googleusercontent.com",
                "project_id": "test-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "test-client-secret",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        with open(mock_credentials_file, 'w') as f:
            json.dump(mock_credentials, f, indent=2)
        print(f"[OK] Created mock credentials file at {mock_credentials_file}")
    else:
        print(f"[OK] Mock credentials file already exists at {mock_credentials_file}")
    
    print("\nCommon issues fixed. Please try running the tests again.")

def main():
    """Main function to set up the test environment."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Setup the test environment for voice_diary.dwnload_files')
    parser.add_argument('--fix', action='store_true', help='Fix common test issues')
    args = parser.parse_args()
    
    print("Setting up test environment for voice_diary.dwnload_files...")
    
    # Check and install required packages
    check_and_install_requirements()
    
    # Create test configuration
    create_test_config_if_needed()
    
    # Fix common issues if requested
    if args.fix:
        fix_common_issues()
    
    print("\nTest environment setup complete!")
    print("To run tests, use: python -m voice_diary.dwnload_files.tests.run_tests")
    
    # Provide additional help for fixing issues
    if not args.fix:
        print("\nIf you encounter issues running tests, try:")
        print("python -m voice_diary.dwnload_files.tests.setup_test_env --fix")

if __name__ == "__main__":
    main() 