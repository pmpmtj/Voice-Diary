#!/usr/bin/env python3
"""
Finds all Python files containing null bytes in a directory and its subdirectories.
"""
import os
import sys
from pathlib import Path

def check_file_for_null_bytes(file_path):
    """Check if a file contains null bytes."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            has_null_bytes = b'\x00' in content
            if has_null_bytes:
                print(f"Found null bytes in: {file_path}")
                return True
            return False
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return False

def find_files_with_null_bytes(directory, file_extension=".py"):
    """Find all files with the specified extension containing null bytes."""
    directory_path = Path(directory)
    found_files = []
    
    for file_path in directory_path.glob(f"**/*{file_extension}"):
        try:
            if check_file_for_null_bytes(file_path):
                found_files.append(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    return found_files

def main():
    """Main function to find files with null bytes."""
    # Get the root directory of the voice_diary package
    script_dir = Path(__file__).parent
    package_root = script_dir.parent.parent
    
    print(f"Searching for null bytes in Python files under: {package_root}")
    
    # Find Python files with null bytes
    files_with_null_bytes = find_files_with_null_bytes(package_root)
    
    if files_with_null_bytes:
        print(f"Found {len(files_with_null_bytes)} files with null bytes:")
        for file_path in files_with_null_bytes:
            print(f"  - {file_path}")
            
        # Ask if user wants to clean these files
        prompt = "Would you like to clean these files? (y/n): "
        user_input = input(prompt).strip().lower()
        
        if user_input == 'y':
            for file_path in files_with_null_bytes:
                clean_file(file_path)
    else:
        print("No files with null bytes found.")

def clean_file(file_path):
    """Clean null bytes from a file."""
    try:
        # Read the file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Create a backup
        backup_path = str(file_path) + '.null_bytes_backup'
        with open(backup_path, 'wb') as f:
            f.write(content)
        
        # Remove null bytes
        clean_content = content.replace(b'\x00', b'')
        
        # Write the cleaned content back
        with open(file_path, 'wb') as f:
            f.write(clean_content)
        
        print(f"Cleaned: {file_path} (backup at {backup_path})")
        return True
    except Exception as e:
        print(f"Error cleaning file {file_path}: {str(e)}")
        return False

if __name__ == "__main__":
    main() 