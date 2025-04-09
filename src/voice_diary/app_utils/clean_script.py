#!/usr/bin/env python3
"""
Clean script to completely rewrite the Python file from scratch.
"""
import os
import sys
from pathlib import Path

def rewrite_file(filename):
    """Completely rewrite the file to eliminate any potential issues."""
    try:
        # Read the file content
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Create a backup
        backup_filename = filename + '.bak2'
        with open(backup_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created backup: {backup_filename}")
        
        # Create a new file with the correct content
        new_content = """#!/usr/bin/env python3
\"\"\"
Voice Diary - Resend Summarized Journal of the Day

This script reads a date range from app_utils_config.json, retrieves the existing
summary for that date range from the database, and sends it via email.
\"\"\"

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Import voice diary components
from voice_diary.db_utils.db_manager import get_day_summaries_by_date_range, initialize_db
from voice_diary.send_email.send_email import main as send_email_main

# Initialize paths - handling both frozen (PyInstaller) and regular Python execution
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    SCRIPT_DIR = Path(sys._MEIPASS)
else:
    # Running as script
    SCRIPT_DIR = Path(__file__).parent.absolute()

# Project root for path calculations
PROJECT_ROOT = SCRIPT_DIR.parent

# Configuration paths - explicitly define all path components
CONFIG_DIR = PROJECT_ROOT / "project_modules_configs" / "config_app_utils"
CONFIG_PATH = CONFIG_DIR / "app_utils_config.json"
EMAIL_CONFIG_DIR = PROJECT_ROOT / "project_modules_configs" / "config_send_email"
EMAIL_CONFIG_PATH = EMAIL_CONFIG_DIR / "email_config.json"

# Initialize logger
logger = logging.getLogger("resend_summary")

def setup_logging():
    \"\"\"Setup logging configuration\"\"\"
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

def load_config():
    \"\"\"Load configuration from JSON file\"\"\"
    try:
        logger.info(f"Attempting to load config from: {CONFIG_PATH}")
        
        # Check if config file exists
        if not CONFIG_PATH.exists():
            logger.error(f"Config file not found at: {CONFIG_PATH}")
            logger.error(f"Directory exists: {CONFIG_DIR.exists()}")
            logger.error(f"Directory contents: {list(CONFIG_DIR.glob('*'))}")
            sys.exit(1)
            
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"Successfully loaded config: {CONFIG_PATH}")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)

def date_from_int(date_int):
    \"\"\"Convert integer date in format YYYYMMDD to datetime object\"\"\"
    date_str = str(date_int)
    try:
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        return datetime(year, month, day, 0, 0, 0)
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid date format: {date_int}. Expected YYYYMMDD. Error: {str(e)}")
        return None

def get_date_range_from_config(config):
    \"\"\"Get date range from config\"\"\"
    date_range = config.get("resend_date_range", [])
    
    # Fallback to current date if range is empty
    if not date_range:
        today = datetime.now()
        today_int = int(today.strftime("%Y%m%d"))
        logger.info(f"No date range specified, using current date: {today_int}")
        return today, today
    
    # If only one date is specified, use it for both start and end
    if len(date_range) == 1:
        start_date_int = date_range[0]
        start_date = date_from_int(start_date_int)
        if not start_date:
            today = datetime.now()
            logger.warning(f"Invalid date format: {start_date_int}. Falling back to current date.")
            return today, today
        return start_date, start_date
    
    # If two dates are specified, use them for start and end
    if len(date_range) >= 2:
        start_date_int, end_date_int = date_range[0], date_range[1]
        
        start_date = date_from_int(start_date_int)
        end_date = date_from_int(end_date_int)
        
        if not start_date or not end_date:
            today = datetime.now()
            logger.warning("Invalid date format in range. Falling back to current date.")
            return today, today
        
        return start_date, end_date

def update_email_config(summary_content, start_date, end_date):
    \"\"\"Update email config with summary content\"\"\"
    try:
        # Check if email config path exists
        logger.info(f"Attempting to read email config from: {EMAIL_CONFIG_PATH}")
        
        if not EMAIL_CONFIG_PATH.exists():
            logger.error(f"Email config file not found at: {EMAIL_CONFIG_PATH}")
            logger.error(f"Directory exists: {EMAIL_CONFIG_DIR.exists()}")
            logger.error(f"Directory contents: {list(EMAIL_CONFIG_DIR.glob('*'))}")
            return False
            
        # Load the email config
        with open(EMAIL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            email_config = json.load(f)
        
        # Update the email message with the summary content
        if 'email' in email_config:
            # Format date for email subject
            if start_date.date() == end_date.date():
                date_str = start_date.strftime("%Y-%m-%d")
                email_config['email']['subject'] = f"Voice Diary Summary for {date_str}"
            else:
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                email_config['email']['subject'] = f"Voice Diary Summary from {start_str} to {end_str}"
            
            # Set the message content
            email_config['email']['message'] = summary_content
            
            # Make sure email sending is enabled
            email_config['send_email'] = True
            
            # Save the updated config
            with open(EMAIL_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(email_config, f, indent=2)
            
            logger.info("Updated email configuration with summary content")
            return True
        else:
            logger.error("Email configuration doesn't contain 'email' section")
            return False
    except Exception as e:
        logger.error(f"Error updating email config: {str(e)}")
        return False

def main():
    \"\"\"Main function to resend summary\"\"\"
    setup_logging()
    logger.info("Starting resend_summarized_journal_of_the_day")
    
    # Load configuration
    config = load_config()
    
    # Get date range from config
    start_date, end_date = get_date_range_from_config(config)
    
    # Adjust dates to include full days
    start_date = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
    
    logger.info(f"Looking for summary from {start_date} to {end_date}")
    
    # Initialize database connection
    initialize_db()
    
    # Get summaries for the date range
    summaries = get_day_summaries_by_date_range(start_date, end_date, limit=1)
    
    if summaries and len(summaries) > 0:
        # Get the most recent summary
        summary = summaries[0]
        summary_content = summary.get('content', '')
        logger.info(f"Found summary from {summary.get('summary_date')}")
        
        # Update email config with summary content
        if update_email_config(summary_content, start_date, end_date):
            # Send email
            logger.info("Sending email with summary")
            send_email_main()
            logger.info("Email sent successfully")
            return True
        else:
            logger.error("Failed to update email configuration")
            return False
    else:
        logger.warning(f"No summary found for the date range")
        return False

if __name__ == "__main__":
    main()
"""
        
        # Delete the original file 
        os.remove(filename)
        
        # Write to a completely new file
        with open(filename, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        
        print(f"Successfully rewrote file from scratch: {filename}")
        return True
    except Exception as e:
        print(f"Error rewriting file: {str(e)}")
        return False

if __name__ == "__main__":
    file_to_clean = "resend_summarized_journal_of_the_day.py"
    print(f"Rewriting file: {file_to_clean}")
    rewrite_file(file_to_clean) 