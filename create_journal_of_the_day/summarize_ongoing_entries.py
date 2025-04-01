#!/usr/bin/env python3
"""
Ongoing Entries Summarizer

This script processes the oldest ongoing entries file identified by check_ongoing_entries.py
and uses OpenAI to create a summarized version.
"""

import os
import sys
import yaml
import json
import logging
import requests
import shutil
import argparse
import subprocess
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_script_dir():
    """Returns the directory where the script is located."""
    return Path(__file__).resolve().parent


def load_config(config_file_path):
    """Load configuration from a YAML file."""
    try:
        with open(config_file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logging.error(f"Failed to load config file {config_file_path}: {e}")
        sys.exit(1)


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
    
    # Set up OpenAI usage logger with rotation if configured
    if 'openai_usage_log_file' in log_config:
        openai_logger = logging.getLogger('openai_usage')
        openai_logger.setLevel(logging.INFO)
        
        # Clear any existing handlers for the openai logger
        if openai_logger.handlers:
            openai_logger.handlers.clear()
        
        # Prevent propagation to root logger to avoid duplicate entries
        openai_logger.propagate = False
        
        openai_log_file = get_script_dir() / log_config['openai_usage_log_file']
        openai_handler = RotatingFileHandler(
            openai_log_file,
            maxBytes=log_config.get('openai_usage_max_size_bytes', 1048576),  # Default 1MB
            backupCount=log_config.get('openai_usage_backup_count', 3)        # Default 3 backups
        )
        
        # Simple formatter for OpenAI usage log (just the message)
        openai_formatter = logging.Formatter('%(message)s')
        openai_handler.setFormatter(openai_formatter)
        openai_logger.addHandler(openai_handler)
    
    return logger


def read_file(file_path):
    """Read the contents of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
        return None


def write_file(file_path, content):
    """Write content to a file."""
    # Use pathlib to ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        logging.info(f"Successfully wrote to file: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to write to file {file_path}: {e}")
        return False


def delete_file(file_path):
    """Delete a file."""
    try:
        # Use pathlib's unlink instead of os.remove
        Path(file_path).unlink()
        logging.info(f"Successfully deleted file: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to delete file {file_path}: {e}")
        return False


def get_oldest_ongoing_entries_file():
    """
    Call check_ongoing_entries.py to identify the oldest ongoing entries file.
    Uses subprocess to capture the output.
    """
    script_dir = get_script_dir()
    check_script_path = script_dir / "check_ongoing_entries.py"
    
    try:
        process = subprocess.run(
            [sys.executable, str(check_script_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output to extract the filename
        output = process.stdout
        logging.info(f"check_ongoing_entries.py output: {output}")
        
        # Try to extract the filename from output
        import re
        match = re.search(r"The oldest ongoing entries file is: ([^\n]+)", output)
        if match:
            oldest_filename = match.group(1)
            # Get app config for output directory path
            app_config_path = get_script_dir() / "config" / "app_config.yaml"
            app_config = load_config(app_config_path)
            output_dir = get_script_dir() / app_config['paths']['output_directory']
            oldest_file_path = output_dir / oldest_filename
            logging.info(f"Found oldest file: {oldest_file_path}")
            return oldest_file_path
        else:
            logging.warning("No oldest file identified from check_ongoing_entries.py output.")
            return None
    except Exception as e:
        logging.error(f"Error executing check_ongoing_entries.py: {e}")
        return None


def get_summarized_entry_path(config, source_filename):
    """Get the path for the summarized entry file."""
    output_config = config['output']
    date_format = output_config['date_format']
    
    # Extract date from the source filename 
    import re
    match = re.search(r'(\d{4}-\d{2}-\d{2})_ongoing_entries', source_filename)
    if match:
        date_str = match.group(1)
    else:
        # Use current date if no date in filename
        date_str = datetime.now().strftime(date_format)
    
    # Use summarized_suffix from config instead of hardcoding
    suffix = output_config.get('summarized_suffix', 'summarized')  # Default to 'summarized' if not in config
    filename = f"{date_str}_{suffix}.{output_config['file_extension']}"
    
    # Use the summarized directory from config
    if 'summarized_directory' in config['paths'] and config['paths']['summarized_directory']:
        output_dir = get_script_dir() / config['paths']['summarized_directory']
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
    
    # Default to script directory
    return get_script_dir() / filename


def process_with_openai(journal_content, prompt_template, openai_config):
    """Process the journal content with OpenAI API using the prompt template."""
    # Format the prompt with the journal content
    prompt = prompt_template.format(
        journal_content=journal_content
    )
    
    # Set up the API request
    config = openai_config['openai_config']
    api_key = config['api_key'] or os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        logging.error("No OpenAI API key found. Set it in the config file or as an environment variable.")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": config['model'],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config['temperature'],
        "max_tokens": config['max_tokens'],
        "top_p": config['top_p'],
        "frequency_penalty": config['frequency_penalty'],
        "presence_penalty": config['presence_penalty']
    }
    
    try:
        response = requests.post(
            config['api_endpoint'],
            headers=headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        result = response.json()
        
        # Log usage if tracking is enabled
        if config['save_usage_stats']:
            usage = result.get('usage', {})
            usage_log = f"{datetime.now().isoformat()} | {config['model']} | " \
                       f"Prompt: {usage.get('prompt_tokens', 0)} | " \
                       f"Completion: {usage.get('completion_tokens', 0)} | " \
                       f"Total: {usage.get('total_tokens', 0)}"
            
            # Use the dedicated OpenAI usage logger instead of direct file writing
            openai_logger = logging.getLogger('openai_usage')
            openai_logger.info(usage_log)
        
        return result['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Error processing with OpenAI: {e}")
        return None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Summarize the oldest ongoing entries file using OpenAI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process the oldest ongoing entries file automatically
  python summarize_ongoing_entries.py
  
  # Process a specific file
  python summarize_ongoing_entries.py --input output/2023-01-15_ongoing_entries.txt
  
  # Save to a specific output file
  python summarize_ongoing_entries.py --output summarized_entries/my_summary.txt
  
  # Process without deleting the original file
  python summarize_ongoing_entries.py --keep-original
  
  # Use verbose logging
  python summarize_ongoing_entries.py --verbose
  
  # Format output as JSON
  python summarize_ongoing_entries.py --format json
  
Exit Codes:
  0 - Success
  1 - No ongoing entries file found
  2 - Failed to read file content
  3 - Failed to process with OpenAI
  4 - Failed to write output file
"""
    )
    
    input_group = parser.add_argument_group('Input/Output Options')
    input_group.add_argument(
        "-i", "--input",
        help="Path to a specific ongoing entries file to summarize (overrides automatic detection)",
        metavar="FILE",
        type=str
    )
    
    input_group.add_argument(
        "-o", "--output",
        help="Path to the output summarized file (overrides default)",
        metavar="FILE",
        type=str
    )
    
    config_group = parser.add_argument_group('Configuration Options')
    config_group.add_argument(
        "--app-config",
        help="Path to the app config file (default: config/app_config.yaml)",
        metavar="FILE",
        type=str,
        default=None
    )
    
    config_group.add_argument(
        "--prompts-config",
        help="Path to the prompts config file (default: config/prompts.yaml)",
        metavar="FILE",
        type=str,
        default=None
    )
    
    config_group.add_argument(
        "--openai-config",
        help="Path to the OpenAI config file (default: config/openai_config.yaml)",
        metavar="FILE",
        type=str,
        default=None
    )
    
    behavior_group = parser.add_argument_group('Behavior Options')
    behavior_group.add_argument(
        "--keep-original", "-k",
        help="Keep the original ongoing entries file (don't delete after processing)",
        action="store_true"
    )
    
    behavior_group.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (text or JSON)"
    )
    
    behavior_group.add_argument(
        "--dry-run",
        help="Show what would be done without making any changes",
        action="store_true"
    )
    
    behavior_group.add_argument(
        "-v", "--verbose",
        help="Increase output verbosity",
        action="store_true"
    )
    
    return parser.parse_args()


def find_files_by_date_pattern(directory, date_pattern):
    """
    Find files in the specified directory matching the date pattern.
    
    Args:
        directory (Path): Directory to search
        date_pattern (str): Date pattern to match (e.g., "20250330")
        
    Returns:
        list: List of Path objects for files matching the pattern
    """
    try:
        # Convert to Path object if string
        dir_path = Path(directory)
        
        # Check if directory exists
        if not dir_path.exists():
            logging.warning(f"Directory {dir_path} does not exist")
            return []
        
        # Build regex pattern to match the date pattern in filenames
        regex_pattern = rf"{date_pattern}"
        
        # Find all files matching the pattern
        matching_files = []
        for file_path in dir_path.iterdir():
            if file_path.is_file() and re.search(regex_pattern, file_path.name):
                matching_files.append(file_path)
                
        logging.info(f"Found {len(matching_files)} files matching pattern '{date_pattern}' in {dir_path}")
        return matching_files
    
    except Exception as e:
        logging.error(f"Error searching for files in {directory}: {e}")
        return []


def get_date_from_filename(filename):
    """
    Extract date from filename (supporting multiple formats).
    
    Args:
        filename (str): Filename to parse
        
    Returns:
        str: Extracted date string or None if not found
    """
    # Try YYYY-MM-DD format
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1).replace('-', '')
    
    # Try YYYYMMDD format directly
    match = re.search(r'(\d{8})', filename)
    if match:
        return match.group(1)
        
    return None


def get_optimized_transcriptions_by_date(date_str):
    """
    Retrieve optimized transcriptions from the database by date.
    
    Args:
        date_str (str): Date string in YYYYMMDD format
        
    Returns:
        list: List of optimized transcription records
    """
    # Format the date for database comparison (YYYYMMDD to YYYY-MM-DD)
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    try:
        # Import database utilities
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root))
        
        from db_utils import initialize_db, get_optimized_transcriptions_by_date as db_get_by_date
        
        # Initialize database
        initialize_db()
        
        # Use the database function to get records by date
        records = db_get_by_date(formatted_date)
        
        logging.info(f"Retrieved {len(records)} optimized transcriptions for date {formatted_date}")
        return records
        
    except Exception as e:
        logging.error(f"Error retrieving optimized transcriptions from database: {e}")
        return []


def format_db_records_for_summary(records):
    """
    Format database records for use in the summarization prompt.
    
    Args:
        records (list): List of database record dictionaries
        
    Returns:
        str: Formatted content for the prompt
    """
    if not records:
        return ""
    
    formatted_content = "## OPTIMIZED TRANSCRIPTIONS FROM DATABASE\n\n"
    
    for i, record in enumerate(records, 1):
        formatted_content += f"### Entry {i}\n"
        formatted_content += record.get('content', 'No content available')
        formatted_content += "\n\n" + "="*50 + "\n\n"
    
    return formatted_content


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Determine config paths
    script_dir = get_script_dir()
    app_config_path = Path(args.app_config) if args.app_config else script_dir / "config" / "app_config.yaml"
    prompts_config_path = Path(args.prompts_config) if args.prompts_config else script_dir / "config" / "prompts.yaml"
    openai_config_path = Path(args.openai_config) if args.openai_config else script_dir / "config" / "openai_config.yaml"
    
    # Load configurations
    app_config = load_config(app_config_path)
    prompts_config = load_config(prompts_config_path)
    openai_config = load_config(openai_config_path)
    
    # Set up logging
    logger = setup_logging(app_config)
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    logger.info("Starting ongoing entries summarization")
    
    # Get input path (from args or from check_ongoing_entries.py)
    if args.input:
        input_path = Path(args.input)
        logger.info(f"Using specified input path: {input_path}")
        
        # Extract date from input filename
        date_str = get_date_from_filename(input_path.name)
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
            logger.warning(f"Could not extract date from filename, using current date: {date_str}")
    else:
        # Get the optimize_transcription output directory
        output_dir = Path(script_dir.parent) / "optimize_transcription" / "output"
        
        # Get current date for filtering
        current_date = datetime.now().strftime("%Y%m%d")
        date_str = current_date
        
        # Find files matching the date pattern
        matching_files = find_files_by_date_pattern(output_dir, date_str.replace('-', ''))
        
        # Check if we have at least 2 files
        if len(matching_files) < 2:
            logger.warning(f"Found fewer than 2 files for date {date_str}. Need at least 2 files to proceed.")
            
            if args.format == "json":
                result = json.dumps({
                    "status": "error",
                    "message": f"Insufficient files for date {date_str}. Found {len(matching_files)}, need at least 2.",
                    "error_code": 1
                })
                print(result)
            
            return 1
        
        # Use the first file as input
        input_path = matching_files[0]
        logger.info(f"Using first matching file as input: {input_path}")
    
    # Read the file content
    journal_content = read_file(input_path)
    if not journal_content:
        logger.error(f"Failed to read content from {input_path}")
        
        if args.format == "json":
            result = json.dumps({
                "status": "error",
                "message": f"Failed to read content from {input_path}",
                "error_code": 2
            })
            print(result)
        
        return 2
    
    logger.info(f"Successfully read journal content from {input_path}")
    
    # Retrieve additional content from database
    db_records = get_optimized_transcriptions_by_date(date_str)
    
    # Format database records for inclusion in the prompt
    db_content = format_db_records_for_summary(db_records)
    
    # Combine file content with database content
    if db_content:
        combined_content = f"{journal_content}\n\n{db_content}"
        logger.info(f"Combined file content with {len(db_records)} database records")
    else:
        combined_content = journal_content
        logger.info("No database records found, using only file content")
    
    # Get the prompt template
    prompt_template = prompts_config['summarize_prompt']
    
    # Process the content
    if args.dry_run:
        logger.info("DRY RUN: Would process journal content with OpenAI")
        summarized_content = "DRY RUN: This is where the summarized content would be."
    else:
        logger.info("Processing content with OpenAI")
        summarized_content = process_with_openai(
            combined_content, 
            prompt_template, 
            openai_config
        )
    
    if not summarized_content:
        logger.error("Failed to process content")
        
        if args.format == "json":
            result = json.dumps({
                "status": "error",
                "message": "Failed to process content with OpenAI",
                "error_code": 3
            })
            print(result)
        
        return 3
    
    # Get output path (from args or generate based on input file)
    if args.output:
        output_path = Path(args.output)
        logger.info(f"Using specified output path: {output_path}")
    else:
        output_path = get_summarized_entry_path(app_config, input_path.name)
        logger.info(f"Using generated output path: {output_path}")
    
    # Write the processed content to the output file
    if args.dry_run:
        logger.info(f"DRY RUN: Would write summarized content to {output_path}")
        success = True
    else:
        logger.info(f"Writing summarized content to {output_path}")
        success = write_file(output_path, summarized_content)
    
    if success:
        logger.info("Successfully wrote summarized content to file")
    else:
        logger.error("Failed to write summarized content to file")
        
        if args.format == "json":
            result = json.dumps({
                "status": "error",
                "message": f"Failed to write summarized content to {output_path}",
                "error_code": 4
            })
            print(result)
        
        return 4
    
    # Delete the original file unless --keep-original flag is set
    if not args.keep_original and not args.dry_run:
        logger.info(f"Deleting original file {input_path}")
        if delete_file(input_path):
            logger.info("Successfully deleted original file")
        else:
            logger.warning("Failed to delete original file")
    elif args.keep_original:
        logger.info("Keeping original file (--keep-original flag set)")
    elif args.dry_run:
        if args.keep_original:
            logger.info("DRY RUN: Would keep original file")
        else:
            logger.info(f"DRY RUN: Would delete original file {input_path}")
    
    logger.info("Summarization process completed successfully")
    
    if args.format == "json":
        result = json.dumps({
            "status": "success",
            "message": "Summarization completed successfully",
            "input_file": str(input_path),
            "output_file": str(output_path),
            "kept_original": args.keep_original or args.dry_run,
            "db_records_used": len(db_records)
        })
        print(result)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 

    summarized