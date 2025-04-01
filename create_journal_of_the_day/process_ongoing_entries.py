#!/usr/bin/env python3
"""
Process Ongoing Entries Chain

This script chains together check_ongoing_entries.py and summarize_ongoing_entries.py
to process the oldest ongoing entries file if one exists.
"""

import os
import sys
import json
import logging
import subprocess
import argparse
from pathlib import Path
from logging.handlers import RotatingFileHandler

def get_script_dir():
    """Returns the directory where the script is located."""
    return Path(__file__).resolve().parent

def setup_logging():
    """Set up logging with rotation."""
    script_dir = get_script_dir()
    log_file = script_dir / "logs" / "process_chain.log"
    
    # Ensure logs directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create main log handler with rotation
    main_handler = RotatingFileHandler(
        log_file,
        maxBytes=1048576,  # 1MB
        backupCount=3
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(formatter)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(main_handler)
    logger.addHandler(console_handler)
    
    return logger

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Chain together check_ongoing_entries.py and summarize_ongoing_entries.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process with default settings
  python process_ongoing_entries.py
  
  # Process with verbose output
  python process_ongoing_entries.py --verbose
  
  # Process with JSON output
  python process_ongoing_entries.py --format json
  
  # Process with custom directory
  python process_ongoing_entries.py --dir /path/to/entries
  
Exit Codes:
  0 - Success
  1 - No ongoing entries file found
  2 - Failed to process with summarize_ongoing_entries.py
"""
    )
    
    parser.add_argument(
        "--dir", "-d",
        help="Custom directory to search for ongoing entry files",
        metavar="DIR"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (text or JSON)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        help="Enable verbose output",
        action="store_true"
    )
    
    return parser.parse_args()

def run_check_ongoing_entries(logger, args):
    """Run check_ongoing_entries.py and return the result."""
    script_dir = get_script_dir()
    check_script_path = script_dir / "check_ongoing_entries.py"
    
    cmd = [sys.executable, str(check_script_path), "--format", args.format]
    if args.dir:
        cmd.extend(["--dir", args.dir])
    if args.verbose:
        cmd.append("--verbose")
    
    logger.info(f"Running check_ongoing_entries.py with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        output = process.stdout
        logger.info(f"check_ongoing_entries.py output: {output}")
        
        # Parse the output based on format
        if args.format == "json":
            result = json.loads(output)
            if result["status"] == "success":
                return result["file_path"]
            else:
                logger.info(f"No valid file found: {result['message']}")
                return None
        else:
            # Try to extract the filename from text output
            import re
            match = re.search(r"The oldest ongoing entries file is: ([^\n]+)", output)
            if match:
                oldest_filename = match.group(1)
                # Get app config for output directory path
                app_config_path = script_dir / "config" / "app_config.yaml"
                with open(app_config_path, 'r', encoding='utf-8') as f:
                    import yaml
                    app_config = yaml.safe_load(f)
                output_dir = script_dir / app_config['paths']['output_directory']
                oldest_file_path = output_dir / oldest_filename
                logger.info(f"Found oldest file: {oldest_file_path}")
                return str(oldest_file_path)
            else:
                logger.info("No valid file found in check_ongoing_entries.py output")
                return None
                
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running check_ongoing_entries.py: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in check_ongoing_entries.py: {e}")
        return None

def run_summarize_ongoing_entries(logger, args, input_file):
    """Run summarize_ongoing_entries.py with the specified input file."""
    script_dir = get_script_dir()
    summarize_script_path = script_dir / "summarize_ongoing_entries.py"
    
    cmd = [sys.executable, str(summarize_script_path), "--input", input_file, "--format", args.format]
    if args.verbose:
        cmd.append("--verbose")
    
    logger.info(f"Running summarize_ongoing_entries.py with command: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        output = process.stdout
        logger.info(f"summarize_ongoing_entries.py output: {output}")
        
        if args.format == "json":
            result = json.loads(output)
            if result["status"] == "success":
                return True, result.get("output_file")
            else:
                logger.error(f"Summarization failed: {result['message']}")
                return False, None
        else:
            return True, None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running summarize_ongoing_entries.py: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error in summarize_ongoing_entries.py: {e}")
        return False, None

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    logger = setup_logging()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    logger.info("Starting ongoing entries processing chain")
    
    # Step 1: Check for oldest ongoing entries file
    oldest_file = run_check_ongoing_entries(logger, args)
    
    if not oldest_file:
        logger.info("No valid ongoing entries file found. Exiting.")
        if args.format == "json":
            result = json.dumps({
                "status": "no_file",
                "message": "No valid ongoing entries file found"
            })
            print(result)
        return 1
    
    # Step 2: Run summarization if a valid file was found
    logger.info(f"Processing file: {oldest_file}")
    success, output_path = run_summarize_ongoing_entries(logger, args, oldest_file)
    
    if not success:
        logger.error("Failed to process ongoing entries file")
        if args.format == "json":
            result = json.dumps({
                "status": "error",
                "message": "Failed to process ongoing entries file"
            })
            print(result)
        return 2
    
    logger.info("Successfully completed processing chain")
    if args.format == "json":
        result = json.dumps({
            "status": "success",
            "message": "Successfully completed processing chain",
            "processed_file": oldest_file,
            "output_file": output_path
        })
        print(result)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 