import os
import glob
import re
import yaml
import json
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

def get_script_dir():
    """Returns the directory where the script is located."""
    return Path(__file__).resolve().parent

def load_config(config_file_path):
    """Load configuration from a YAML file."""
    try:
        with open(config_file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Failed to load config file {config_file_path}: {e}")
        return None

def setup_logging(config):
    """Set up logging with rotation based on configuration."""
    log_config = config['logging']
    log_file = get_script_dir() / log_config['log_file']
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config['log_level']))
    
    # Clear any existing handlers (to avoid duplicates when called multiple times)
    if logger.handlers:
        logger.handlers.clear()
    
    # Create main log handler with rotation
    main_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config['max_size_bytes'],
        backupCount=log_config['backup_count']
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(formatter)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(main_handler)
    logger.addHandler(console_handler)
    
    return logger

def find_oldest_ongoing_entries_file(custom_output_dir=None, output_format='text'):
    """
    Find the oldest ongoing entries file based on filename date.
    
    Args:
        custom_output_dir (str, optional): Custom directory to search in
        output_format (str): Output format, either 'text' or 'json'
    
    Returns:
        str: Path to the oldest ongoing entries file or None if not found
    """
    # Path to the output directory using pathlib for OS agnostic path handling
    script_dir = get_script_dir()
    
    # Load app config to get output directory and set up logging
    app_config_path = script_dir / "config" / "app_config.yaml"
    app_config = load_config(app_config_path)
    
    # Set up logging if app_config was loaded successfully
    if app_config and 'logging' in app_config:
        logger = setup_logging(app_config)
    else:
        # Configure basic logging if couldn't load config
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger()
    
    # Determine the output directory
    if custom_output_dir:
        output_dir = Path(custom_output_dir)
        logging.info(f"Using custom output directory: {output_dir}")
    elif not app_config or 'paths' not in app_config or 'output_directory' not in app_config['paths']:
        logging.warning("Could not load app config or find output_directory in config. Using default output directory.")
        output_dir = script_dir / "output"
    else:
        output_dir = script_dir / app_config['paths']['output_directory']
    
    # Find all ongoing entries files
    file_pattern = app_config['paths'].get('file_pattern', "*_ongoing_entries*.txt")
    pattern = str(output_dir / file_pattern)
    ongoing_entries_files = glob.glob(pattern)
    
    # If there are no files, return None
    if not ongoing_entries_files:
        message = "No ongoing entries files found."
        logging.info(message)
        
        if output_format == 'json':
            result = json.dumps({
                "status": "no_files",
                "message": message,
                "file_path": None,
                "file_name": None
            })
            print(result)
        else:
            print(message)
        return None
    
    # Modified: Check if there is exactly one file
    if len(ongoing_entries_files) == 1:
        message = "Single file found. At least two files are needed for processing."
        logging.info(message)
        
        if output_format == 'json':
            result = json.dumps({
                "status": "single_file",
                "message": message,
                "file_path": None,
                "file_name": None
            })
            print(result)
        else:
            print(message)
        return None
    
    # Extract dates from filenames and create a dictionary mapping dates to filenames
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_ongoing_entries.*\.txt$')
    file_dates = {}
    
    for file_path in ongoing_entries_files:
        # Convert to Path object for consistent handling
        file_path_obj = Path(file_path)
        filename = file_path_obj.name
        match = date_pattern.search(filename)
        if match:
            date_str = match.group(1)
            try:
                # Parse the date
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                file_dates[file_path] = file_date
            except ValueError:
                logging.warning(f"Couldn't parse date from filename: {filename}")
    
    # Find the file with the oldest date
    if file_dates:
        oldest_file = min(file_dates.items(), key=lambda x: x[1])
        oldest_file_path = oldest_file[0]
        oldest_filename = Path(oldest_file_path).name
        message = f"The oldest ongoing entries file is: {oldest_filename}"
        logging.info(message)
        
        if output_format == 'json':
            result = json.dumps({
                "status": "success",
                "message": message,
                "file_path": str(oldest_file_path),
                "file_name": oldest_filename
            })
            print(result)
        else:
            print(message)
        return oldest_file_path  # Return the full path to the oldest file
    else:
        message = "No valid date-prefixed ongoing entries files found."
        logging.warning(message)
        
        if output_format == 'json':
            result = json.dumps({
                "status": "no_valid_files",
                "message": message,
                "file_path": None,
                "file_name": None
            })
            print(result)
        else:
            print(message)
        return None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find the oldest ongoing entries file.",
        epilog="Example: python check_ongoing_entries.py --format json --dir /path/to/entries",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--dir", "-d",
        dest="directory",
        help="Custom directory to search for ongoing entry files"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (text or JSON)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find the oldest file
    result = find_oldest_ongoing_entries_file(
        custom_output_dir=args.directory,
        output_format=args.format
    )
    
    # Set exit code based on result
    sys.exit(0 if result else 1) 