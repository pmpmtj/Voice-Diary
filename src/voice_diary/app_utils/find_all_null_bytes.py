#!/usr/bin/env python3
"""
Finds all Python files containing null bytes and automatically cleans them.
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
                return True, content
            return False, None
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return False, None

def clean_file(file_path, content):
    """Clean null bytes from a file."""
    try:
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

def find_and_clean_files_with_null_bytes(directory, file_extension=".py"):
    """Find all files with the specified extension containing null bytes and clean them."""
    directory_path = Path(directory)
    cleaned_files = []
    
    for file_path in directory_path.glob(f"**/*{file_extension}"):
        try:
            has_null_bytes, content = check_file_for_null_bytes(file_path)
            if has_null_bytes:
                clean_file(file_path, content)
                cleaned_files.append(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    return cleaned_files

def main():
    """Main function to find and clean files with null bytes."""
    # Get the root directory of the voice_diary package
    script_dir = Path(__file__).parent
    voice_diary_dir = script_dir.parent
    project_root = voice_diary_dir.parent
    
    print(f"Searching for null bytes in Python files under: {project_root}")
    
    # Find Python files with null bytes and clean them
    cleaned_files = find_and_clean_files_with_null_bytes(project_root)
    
    if cleaned_files:
        print(f"Cleaned {len(cleaned_files)} files with null bytes:")
        for file_path in cleaned_files:
            print(f"  - {file_path}")
    else:
        print("No files with null bytes found.")

if __name__ == "__main__":
    main() 