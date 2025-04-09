#!/usr/bin/env python3
"""
Test script for running the resend_summarized_journal_of_the_day with detailed logging.
This helps diagnose configuration issues by adding more verbose logging.
"""
import logging
import os
import sys
from pathlib import Path

# Configure basic logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_resend")

def main():
    """Main function to test the resend script"""
    try:
        logger.info("Starting test of resend_summarized_journal_of_the_day")
        
        # Get the directory structure to verify paths
        script_dir = Path(__file__).parent.absolute()
        project_root = script_dir.parent
        
        # Check if required folders exist
        config_dir = project_root / "project_modules_configs" / "config_app_utils"
        email_config_dir = project_root / "project_modules_configs" / "config_send_email"
        
        # Log directory information 
        logger.info(f"Script directory: {script_dir}")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Config directory exists: {config_dir.exists()}")
        logger.info(f"Config directory path: {config_dir}")
        
        if config_dir.exists():
            logger.info(f"Config directory contents: {list(config_dir.glob('*'))}")
        
        logger.info(f"Email config directory exists: {email_config_dir.exists()}")
        logger.info(f"Email config directory path: {email_config_dir}")
        
        if email_config_dir.exists():
            logger.info(f"Email config directory contents: {list(email_config_dir.glob('*'))}")
            
        # Import and run the resend script
        from voice_diary.app_utils.resend_summarized_journal_of_the_day import main as resend_main
        
        logger.info("Calling resend_summarized_journal_of_the_day.main()")
        result = resend_main()
        
        logger.info(f"Resend completed with result: {result}")
        return result
        
    except Exception as e:
        logger.exception(f"Error running resend test: {str(e)}")
        return False

if __name__ == "__main__":
    main() 