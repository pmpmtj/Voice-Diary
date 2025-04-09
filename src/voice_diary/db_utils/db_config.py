import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import importlib.resources
from logging.handlers import RotatingFileHandler

# Load configuration from JSON
def load_config():
    """Load configuration from db_utils_config.json package resource"""
    try:
        # Replace open_text with files().open()
        config_file = importlib.resources.files('voice_diary.db_utils.db_utils_config').joinpath('db_utils_config.json')
        with config_file.open('r') as f:
            return json.load(f)
    except (ImportError, FileNotFoundError):
        logging.warning("Could not load config file from package resources")
        return {}

# Load config once at module import time
CONFIG = load_config()

# Configure logging based on config
def configure_logging():
    """Configure logging with rotation based on config settings"""
    # Check if root logger already has handlers to avoid duplicate configuration
    root_logger = logging.getLogger()
    if root_logger.handlers:
        logging.debug("Logging already configured, skipping reconfiguration") 
        return

    log_level = getattr(logging, CONFIG.get('logging', {}).get('level', 'INFO'))
    log_format = CONFIG.get('logging', {}).get('format', '%(asctime)s - %(levelname)s - %(message)s')
    log_file_name = CONFIG.get('logging', {}).get('log_file', 'db_utils.log')
    max_size = CONFIG.get('logging', {}).get('max_size_bytes', 1048576)  # Default 1MB
    backup_count = CONFIG.get('logging', {}).get('backup_count', 3)
    
    # Create the logs directory inside db_utils if it doesn't exist
    # Get the directory where this script is located
    db_utils_dir = Path(__file__).parent
    logs_dir = db_utils_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Full path to the log file
    log_file_path = logs_dir / log_file_name

    # Create a formatter
    formatter = logging.Formatter(log_format)

    # Create handlers
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)

    # Get the root logger
    root_logger.setLevel(log_level)
    
    # Add the handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log the location of the log file
    logging.info(f"Logging to: {log_file_path.absolute()}")

# Configure logging
configure_logging()

# Load environment variables from .env file
try:
    # First try to load from package resources using files() instead of path()
    env_path = importlib.resources.files('voice_diary').joinpath('.env')
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.info("Loaded environment variables from package resource .env file")
except (ImportError, FileNotFoundError):
    # Fallback to a few common locations
    possible_env_paths = [
        Path.cwd() / '.env',                # Current working directory
        Path.home() / '.voice_diary' / '.env',  # User's home directory
        Path('/etc/voice_diary/.env')       # System-wide config
    ]
    
    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            logging.info(f"Loaded environment variables from .env file at {env_path}")
            break

# Database configuration
def get_db_url():
    """Get database URL from environment or return a default local URL"""
    # First try to get the URL from environment variable
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        # Log that we couldn't find it in environment
        logging.warning("DATABASE_URL not found in environment. Trying to load from .env file.")
        
        # Look for .env file in the current directory and voice_diary package directory
        possible_env_paths = [
            Path.cwd() / '.env',                     # Current working directory
            Path(__file__).parent.parent / '.env',   # voice_diary package directory
            Path.home() / '.voice_diary' / '.env',   # User's home directory
            Path('/etc/voice_diary/.env')            # System-wide config
        ]
        
        for env_path in possible_env_paths:
            if env_path.exists():
                logging.info(f"Found .env file at {env_path}")
                load_dotenv(dotenv_path=env_path)
                db_url = os.environ.get('DATABASE_URL')
                if db_url:
                    logging.info("Successfully loaded DATABASE_URL from .env file")
                    break
        
        # If still not found, use default URL from config
        if not db_url:
            logging.warning("DATABASE_URL not found in any .env file. Using default database.")
            db_url = CONFIG.get('database', {}).get('default_url')
            if not db_url:
                logging.error("No default database URL configured in db_utils_config.json")
    
    logging.info(f"Using database URL: {db_url}")
    return db_url
