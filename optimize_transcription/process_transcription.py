#!/usr/bin/env python3
"""
Transcription Processor Script

This script processes transcription files using a diary organization prompt
and extracts to-do items from the content.
"""

import os
import sys
import yaml
import logging
import datetime
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
import requests
import json


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
    log_file = os.path.join(get_script_dir(), log_config['log_file'])
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config['log_level']))
    
    # Create handlers
    handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config['max_size_bytes'],
        backupCount=log_config['backup_count']
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
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
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception as e:
        logging.error(f"Failed to write to file {file_path}: {e}")
        return False


def append_file(file_path, content):
    """Append content to a file, creating it if it doesn't exist."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            # Add a separator before new content for better readability
            file.write(f"\n\n{'='*50}\n\n{content}")
        return True
    except Exception as e:
        logging.error(f"Failed to append to file {file_path}: {e}")
        return False


def move_transcription_file(source_path, config):
    """Move transcription file to processed directory with timestamp."""
    try:
        # Get timestamp for filename
        timestamp = datetime.datetime.now().strftime(config['output']['timestamp_format'])
        
        # Create processed transcriptions directory
        processed_dir = Path(get_script_dir()) / config['paths']['processed_transcriptions']
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create new filename with timestamp
        new_filename = f"transcription_{timestamp}.txt"
        target_path = processed_dir / new_filename
        
        # Move the file
        shutil.move(str(source_path), str(target_path))
        logging.info(f"Moved transcription file to: {target_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to move transcription file: {e}")
        return False


def get_ongoing_entries_path(config):
    """Get the path to the ongoing entries file with date prefix."""
    output_config = config['output']
    date_format = output_config['date_format']
    current_date = datetime.datetime.now().strftime(date_format)
    
    filename = f"{current_date}_ongoing_entries.{output_config['file_extension']}"
    
    # Check if output directory is specified and use it
    if 'output_directory' in config['paths'] and config['paths']['output_directory']:
        output_dir = Path(get_script_dir()) / config['paths']['output_directory']
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
    
    # Default to script directory
    return Path(get_script_dir()) / filename


def read_ongoing_entries(ongoing_entries_path):
    """Read the ongoing entries file if it exists."""
    if ongoing_entries_path.exists():
        return read_file(ongoing_entries_path)
    return ""


def process_with_openai(transcription, ongoing_entries, prompt_template, openai_config):
    """Process the transcription with OpenAI API using the prompt template."""
    # Format the prompt with the transcription and ongoing entries
    
    # Format the ongoing entries properly - if empty, indicate so
    formatted_ongoing_entries = ongoing_entries if ongoing_entries else "No previous entries yet."
    
    prompt = prompt_template.format(
        diary_entry=transcription,
        ongoing_entries=formatted_ongoing_entries
    )
    
    # Set up the API request
    config = openai_config['openai_config']
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key'] or os.environ.get('OPENAI_API_KEY')}"
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
        return result['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Error processing with OpenAI: {e}")
        return None


def main():
    # Load configurations
    script_dir = get_script_dir()
    app_config_path = script_dir / "config" / "app_config.yaml"
    prompts_config_path = script_dir / "config" / "prompts.yaml"
    openai_config_path = script_dir / "config" / "openai_config.yaml"
    
    app_config = load_config(app_config_path)
    prompts_config = load_config(prompts_config_path)
    openai_config = load_config(openai_config_path)
    
    # Set up logging
    logger = setup_logging(app_config)
    logger.info("Starting transcription processing")
    
    # Import database utilities
    sys.path.insert(0, str(script_dir.parent))
    from db_utils import (
        initialize_db, 
        get_latest_transcriptions, 
        save_transcription,
        save_optimized_transcription
    )
    
    # Initialize database
    initialize_db()
    
    # Get paths for backwards compatibility
    transcription_path = script_dir / app_config['paths']['transcription_file']
    ongoing_entries_path = get_ongoing_entries_path(app_config)
    
    # Get transcription content - first try from database, then fallback to file
    transcription = None
    
    # Try to get the latest transcription from the database
    latest_transcriptions = get_latest_transcriptions(limit=1)
    if latest_transcriptions and len(latest_transcriptions) > 0:
        transcription = latest_transcriptions[0]['content']
        logger.info("Retrieved latest transcription from database")
    
    # If not found in database, try to read from file (backwards compatibility)
    if not transcription and transcription_path.exists():
        transcription = read_file(transcription_path)
        logger.info("Retrieved transcription from file (legacy method)")
    
    if not transcription:
        logger.error("No transcription found in database or file")
        sys.exit(1)
    
    # Read ongoing entries
    ongoing_entries = read_ongoing_entries(ongoing_entries_path)
    logger.info(f"Found ongoing entries: {'Yes' if ongoing_entries else 'No'}")
    
    # Get the prompt template
    prompt_template = prompts_config['diary_organization_prompt']
    
    # Process the transcription
    logger.info("Processing transcription with OpenAI")
    processed_content = process_with_openai(
        transcription, 
        ongoing_entries, 
        prompt_template, 
        openai_config
    )
    
    if not processed_content:
        logger.error("Failed to process transcription")
        sys.exit(1)
    
    # Save processed content to ongoing entries file for backwards compatibility
    logger.info(f"Appending processed content to {ongoing_entries_path}")
    if not ongoing_entries_path.exists():
        # If file doesn't exist, create it with the processed content
        if write_file(ongoing_entries_path, processed_content):
            logger.info("Successfully created and wrote processed content to file")
        else:
            logger.error("Failed to write processed content to file")
            sys.exit(1)
    else:
        # If file exists, append the processed content
        if append_file(ongoing_entries_path, processed_content):
            logger.info("Successfully appended processed content to file")
        else:
            logger.error("Failed to append processed content to file")
            sys.exit(1)
    
    # Also save the processed content to the database with the category 'processed'
    try:
        # Create metadata with reference to original transcription
        metadata = {
            "processing_timestamp": datetime.datetime.now().isoformat(),
            "original_transcription_id": latest_transcriptions[0]['id'] if latest_transcriptions else None,
            "processing_status": "completed"
        }
        
        # Save to optimize_transcriptions table
        save_optimized_transcription(
            content=processed_content,
            original_transcription_id=latest_transcriptions[0]['id'] if latest_transcriptions else None,
            metadata=metadata
        )
        logger.info("Successfully saved processed content to optimize_transcriptions table")
        
        # Also save to transcriptions table with 'processed' category for backwards compatibility
        save_transcription(
            content=processed_content,
            category="processed",
            metadata=metadata
        )
        logger.info("Successfully saved processed content to transcriptions table (for backwards compatibility)")
    except Exception as e:
        logger.error(f"Error saving processed content to database: {str(e)}")
    
    # If using file-based method, move the transcription file to processed directory
    if transcription_path.exists():
        logger.info("Moving transcription file to processed directory")
        if move_transcription_file(transcription_path, app_config):
            logger.info("Successfully moved transcription file")
        else:
            logger.error("Failed to move transcription file")
    
    logger.info("Transcription processing completed successfully")


if __name__ == "__main__":
    main() 