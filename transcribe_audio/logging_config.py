#!/usr/bin/env python3
"""
Centralized logging configuration for the transcription service.
Provides consistent logging setup with rotation across the entire application.
"""

import logging
import logging.handlers
from pathlib import Path

def setup_logging(logs_dir, log_filename="app.log", to_file=True, log_level=logging.INFO):
    """
    Set up application logging with rotation.
    
    Args:
        logs_dir: Directory to store log files
        log_filename: Name of the log file
        to_file: Whether to log to a file (in addition to console)
        log_level: Logging level (default: INFO)
    
    Returns:
        Logger: Configured logger instance
    """
    # Ensure logs directory exists
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the root logger and remove any existing handlers
    logger = logging.getLogger()
    logger.handlers.clear()
    
    # Set the log level
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add rotating file handler if requested
    if to_file:
        log_file = logs_dir / log_filename
        max_size = 1 * 1024 * 1024  # 1 MB
        backup_count = 3  # Keep last 3 logs
        
        rotating_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        rotating_handler.setFormatter(formatter)
        logger.addHandler(rotating_handler)
    
    if to_file:
        logger.info(f"Logging to file: {log_file}")
        logger.info(f"Maximum log size: {max_size/1024/1024:.1f} MB")
        logger.info(f"Number of backup files: {backup_count}")
    
    return logger 