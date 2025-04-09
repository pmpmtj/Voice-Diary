#!/usr/bin/env python3
"""
Voice Diary - Delete OpenAI Thread

This script deletes a thread from OpenAI Assistants API and updates the configuration file.
It can either delete a specific thread ID provided as an argument, or delete the thread
currently saved in the configuration file.
"""

import json
import logging
import logging.handlers
import os
import sys
import argparse
from pathlib import Path
from openai import OpenAI

# Constants
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "summarize_day_config" / "summarize_day_config.json"
OPENAI_CONFIG_PATH = SCRIPT_DIR / "summarize_day_config" / "openai_config.json"
LOG_DIR = SCRIPT_DIR / "log"

# Create log directory if it doesn't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize logger
logger = logging.getLogger("delete_thread")

def load_openai_config():
    """Load OpenAI configuration from JSON file"""
    try:
        with open(OPENAI_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading OpenAI configuration: {str(e)}")
        sys.exit(1)

def setup_logging():
    """Setup logging configuration"""
    log_level = logging.INFO
    
    logger.setLevel(log_level)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Set up file handler with rotation
    log_file = "delete_thread.log"
    max_bytes = 1048576  # 1MB default
    backup_count = 3
    
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info("Logging configured successfully")

def delete_thread(thread_id=None, update_config=True):
    """
    Delete an OpenAI thread and optionally update the config file.
    
    Args:
        thread_id (str, optional): The ID of the thread to delete. If None, uses the thread from config.
        update_config (bool): Whether to update the config file after deletion.
        
    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    # Set up logging
    setup_logging()
    
    logger.info("Starting delete_thread process")
    
    # Load OpenAI config
    openai_config = load_openai_config()
    config = openai_config.get('openai_config', {})
    
    # If no thread_id provided, use the one from config
    if not thread_id:
        thread_id = config.get('thread_id')
        if not thread_id:
            logger.error("No thread_id specified and none found in config")
            return False
    
    # Get API key from config or environment
    api_key = config.get('api_key') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("No OpenAI API key found. Set it in the config file or as an environment variable.")
        return False
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    try:
        # Delete the thread
        logger.info(f"Deleting thread with ID: {thread_id}")
        response = client.beta.threads.delete(thread_id)
        
        # Check response - if we get here, it means the deletion was successful
        if response.deleted:
            logger.info(f"Thread {thread_id} deleted successfully")
            
            # Update the configuration file if requested
            if update_config and thread_id == config.get('thread_id'):
                logger.info("Updating configuration file to remove thread_id")
                config['thread_id'] = ""
                config['thread_created_at'] = ""
                
                with open(OPENAI_CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(openai_config, f, indent=2)
                
                logger.info("Configuration file updated successfully")
            
            return True
        else:
            logger.error(f"Failed to delete thread {thread_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {str(e)}")
        return False

def main():
    """Parse arguments and run thread deletion function"""
    parser = argparse.ArgumentParser(description="Delete an OpenAI thread and update the config file")
    parser.add_argument("--thread-id", type=str, help="Thread ID to delete. If not provided, uses thread ID from config")
    parser.add_argument("--no-update-config", action="store_true", help="Don't update the config file after deletion")
    
    args = parser.parse_args()
    
    result = delete_thread(args.thread_id, not args.no_update_config)
    
    if result:
        print("Thread deleted successfully")
    else:
        print("Failed to delete thread. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()