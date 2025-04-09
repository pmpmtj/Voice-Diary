#!/usr/bin/env python3
"""
Binary file inspector that prints each byte in hex.
"""
import sys
from pathlib import Path

def inspect_file(filename):
    """Print each byte in hex and its ASCII representation."""
    try:
        with open(filename, 'rb') as f:
            content = f.read()
            
        print(f"File size: {len(content)} bytes")
        print("Printing first 100 and last 100 bytes:")
        
        # Check for UTF-8 BOM
        if content.startswith(b'\xef\xbb\xbf'):
            print("File starts with UTF-8 BOM marker")
        
        # Print first 100 bytes
        print("\nFirst 100 bytes:")
        for i, byte in enumerate(content[:100]):
            print(f"{i:04d}: 0x{byte:02x} {chr(byte) if 32 <= byte <= 126 else '.'}")
            
        # Print last 100 bytes
        print("\nLast 100 bytes:")
        for i, byte in enumerate(content[-100:]):
            idx = len(content) - 100 + i
            print(f"{idx:04d}: 0x{byte:02x} {chr(byte) if 32 <= byte <= 126 else '.'}")
            
        # Check for null bytes
        null_positions = [i for i, byte in enumerate(content) if byte == 0]
        if null_positions:
            print(f"\nFound {len(null_positions)} null bytes at positions: {null_positions[:20]}...")
            
            # Print context around first null byte
            if null_positions:
                pos = null_positions[0]
                start = max(0, pos - 20)
                end = min(len(content), pos + 20)
                print(f"\nContext around first null byte (position {pos}):")
                for i in range(start, end):
                    byte = content[i]
                    marker = " <-- NULL" if i == pos else ""
                    print(f"{i:04d}: 0x{byte:02x} {chr(byte) if 32 <= byte <= 126 else '.'}{marker}")
        else:
            print("\nNo null bytes found in file")
            
    except Exception as e:
        print(f"Error inspecting file: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Default to resend_summarized_journal_of_the_day.py
        filename = "resend_summarized_journal_of_the_day.py"
    
    print(f"Inspecting file: {filename}")
    inspect_file(filename) 