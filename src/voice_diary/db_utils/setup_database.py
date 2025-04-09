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
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import the db_manager from db_utils
from voice_diary.db_utils.db_manager import initialize_db

def ensure_env_file_exists():
    """
    Ensure the .env file exists in both the source directory and the installed package location.
    This helps ensure the database configuration is properly loaded.
    """
    try:
        # Get the source .env file path
        src_env_path = Path(__file__).parent.parent / '.env'
        
        if src_env_path.exists():
            # Get the installed package location
            import importlib.resources
            pkg_path = importlib.resources.files('voice_diary')
            pkg_env_path = pkg_path / '.env'
            
            # Copy the .env file to the package location if it exists
            if not pkg_env_path.exists() or (src_env_path.read_text() != pkg_env_path.read_text()):
                logger.info(f"Copying .env file from {src_env_path} to {pkg_env_path}")
                shutil.copy2(src_env_path, pkg_env_path)
                return True
            return True
        else:
            logger.warning(f".env file not found at {src_env_path}")
            return False
    except Exception as e:
        logger.error(f"Error ensuring .env file exists: {e}")
        return False

def main():
    """Main function to set up the database"""
    parser = argparse.ArgumentParser(description='Set up the PostgreSQL database for transcriptions')
    args = parser.parse_args()
    
    # Logging is already configured by importing db_config (via db_manager)
    logger = logging.getLogger(__name__)
    
    # Check for PostgreSQL database connection
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.warning("DATABASE_URL environment variable not found.")
        logger.warning("Make sure you have created a PostgreSQL database.")
        
        response = input("Do you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Ensure .env file exists
    ensure_env_file_exists()
    
    # Initialize database
    logger.info("Initializing database...")
    success = initialize_db()
    
    if success:
        logger.info("Database setup completed successfully!")
        logger.info("The following tables have been created:")
        logger.info("  - vd_transcriptions: Stores transcription content and metadata")
        logger.info("  - vd_day_summaries: Stores daily summary content")
    else:
        logger.error("Database setup failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
