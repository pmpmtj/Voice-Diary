#!/usr/bin/env python3
"""
Database Setup Script

This script initializes the PostgreSQL database and creates the necessary tables
for storing transcriptions and related data.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db_utils import initialize_db

def main():
    """Main function to set up the database"""
    parser = argparse.ArgumentParser(description='Set up the PostgreSQL database for transcriptions')
    parser.add_argument('--force', action='store_true', help='Force recreation of tables')
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check for PostgreSQL database connection
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logging.warning("DATABASE_URL environment variable not found.")
        logging.warning("Make sure you have created a PostgreSQL database in Replit.")
        logging.warning("To add a PostgreSQL database:")
        logging.warning("1. Open a new tab in Replit and type 'Database'")
        logging.warning("2. Click 'create a database'")
        logging.warning("3. The environment variables will be set up automatically")
        
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Initialize database
    logging.info("Initializing database...")
    success = initialize_db()
    
    if success:
        logging.info("Database setup completed successfully!")
        logging.info("The following tables have been created:")
        logging.info("  - transcriptions: Stores transcription content and metadata")
        logging.info("  - categories: Categorization of transcriptions")
        logging.info("  - processed_files: Tracks processed audio files")
        logging.info("  - optimize_transcriptions: Stores optimized transcription content with structured data")
    else:
        logging.error("Database setup failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
