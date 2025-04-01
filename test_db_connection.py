#!/usr/bin/env python3
"""
Test script to verify database connection with .env loading
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils.db_config import get_db_url

def main():
    """Test database connection"""
    print("Testing database connection...")
    print(f"Current working directory: {os.getcwd()}")
    
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        print(f"Found .env file at: {env_path}")
    else:
        print(f"WARNING: .env file not found at: {env_path}")
    
    # Get DATABASE_URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"DATABASE_URL found in environment: {db_url.replace('postgres:', 'postgres:*****:')}")
    else:
        print("DATABASE_URL not found in environment")
    
    # Try connecting to database
    try:
        import psycopg2
        db_url = get_db_url()
        print(f"Using DB URL: {db_url.replace('postgres:', 'postgres:*****:')}")
        conn = psycopg2.connect(db_url)
        print("Database connection successful!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    print("\nPress Enter to exit...")
    input()
    sys.exit(0 if success else 1) 