import logging
import json
import os
import sys
from datetime import datetime, timedelta
import time
import traceback
import subprocess

# Add constant at the top of file
STATE_FILE = os.path.join(os.path.dirname(__file__), 'pipeline_state.json')

# Load configuration
def load_config():
    """Load configuration from config.json file"""
    # Handle both PyInstaller bundle and normal environments
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
        config_path = os.path.join(sys._MEIPASS, 'config.json')
    else:
        # Running in normal Python environment
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'config.json')
    
    # Print debug info
    print(f"Looking for config file at: {config_path}")
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print("Please create a config.json file before running the scheduler.")
        sys.exit(1)
    
    # Try to load and parse the config file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate that required sections exist
        if "scheduler" not in config:
            print("ERROR: Missing 'scheduler' section in config.json")
            sys.exit(1)
            
        return config
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config.json: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load config.json: {str(e)}")
        sys.exit(1)

def validate_config(config):
    """Validate configuration settings"""
    required_sections = ["scheduler"]
    required_scheduler_params = ["runs_per_day"]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")
            
    for param in required_scheduler_params:
        if param not in config["scheduler"]:
            raise ValueError(f"Missing required parameter in scheduler section: {param}")
            
    if not isinstance(config["scheduler"]["runs_per_day"], (int, float)):
        raise ValueError("runs_per_day must be a number")

def calculate_interval_seconds(config):
    """
    Calculate interval in seconds based on configuration.
    The 'runs_per_day' in config.json represents how many times the pipeline runs per day.
    If runs_per_day is 0: run once and exit
    Otherwise: convert runs per day to seconds interval (86400/N)
    """
    runs_per_day = config.get("scheduler", {}).get("runs_per_day", 1)
    
    # If runs_per_day is 0, we'll run once and exit
    if runs_per_day == 0:
        return 0
        
    # Convert "runs per day" to seconds: 86400 seconds / N runs
    seconds_per_day = 86400
    interval_seconds = seconds_per_day / runs_per_day
    logging.info(f"Configured to run {runs_per_day} times per day (every {int(interval_seconds)} seconds)")
    return int(interval_seconds)

def calculate_next_run_time(interval_seconds):
    """
    Calculate the next run time, taking into account midnight crossover
    Args:
        interval_seconds: The interval between runs in seconds
    Returns:
        datetime: The next run time
    """
    now = datetime.now()
    next_run = now + timedelta(seconds=interval_seconds)
    
    # Get seconds until midnight
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = (midnight - now).total_seconds()
    
    # If interval crosses midnight, adjust the message
    if interval_seconds > seconds_until_midnight:
        return next_run
    
    return next_run

def run_pipeline():
    """
    Run the pipeline to download files from Google Drive and transcribe them.
    Returns True if pipeline completes successfully, False otherwise.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting pipeline execution")
    
    try:
        # Load state from previous runs
        pipeline_state = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                pipeline_state = json.load(f)
        
        # Initialize processing statistics if they don't exist
        if 'processing_stats' not in pipeline_state:
            pipeline_state['processing_stats'] = {
                'total_processed': 0,
                'successful_processed': 0,
                'failed_processed': 0,
                'last_processed_time': None
            }
        
        # Step 1: Download files from Google Drive
        logger.info("Starting Google Drive download step")
        gdrive_script = os.path.join(os.path.dirname(__file__), 'gdrive_downloader', 'download_from_gdrive.py')
        gdrive_result = subprocess.run(
            [sys.executable, gdrive_script], 
            capture_output=True, 
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if gdrive_result.returncode != 0:
            logger.error(f"Google Drive download failed: {gdrive_result.stderr}")
            pipeline_state['last_failed_step'] = 'gdrive_download'
            pipeline_state['last_error'] = gdrive_result.stderr
            pipeline_state['last_run_status'] = 'failed'
            
            # Save state
            update_pipeline_state(STATE_FILE, pipeline_state)
            return False
            
        logger.info("Google Drive download completed successfully")
        
        
        #################### input("Google Drive download completed successfully") ##################################
        
        # Step 2: Transcribe downloaded files
        logger.info("Starting audio transcription step")
        whisper_script = os.path.join(os.path.dirname(__file__), 'transcribe_audio', 'openai_whisper.py')
        whisper_result = subprocess.run([sys.executable, whisper_script], capture_output=True, text=True)
        
        if whisper_result.returncode != 0:
            logger.error(f"Audio transcription failed: {whisper_result.stderr}")
            pipeline_state['last_failed_step'] = 'transcription'
            pipeline_state['last_error'] = whisper_result.stderr
            pipeline_state['last_run_status'] = 'failed'
            success = False
        else:
            logger.info("Audio transcription completed successfully")
            
            # Check if transcription.txt exists before proceeding
            TRANSCRIPTION_FILE = os.path.join(os.path.dirname(__file__), 'transcription.txt')
            if not os.path.exists(TRANSCRIPTION_FILE):
                logger.error(f"Transcription file not found: {TRANSCRIPTION_FILE}")
                pipeline_state['last_failed_step'] = 'transcription_file_missing'
                pipeline_state['last_error'] = 'Transcription file not found'
                pipeline_state['last_run_status'] = 'failed'
                success = False
            else:
                # Step 3: Process transcription
                logger.info("Starting transcription processing step")
                process_script = os.path.join(os.path.dirname(__file__), 'optimize_transcription', 'process_transcription.py')
                process_result = subprocess.run([sys.executable, process_script], capture_output=True, text=True)
                
                # Update processing statistics
                pipeline_state['processing_stats']['total_processed'] += 1
                pipeline_state['processing_stats']['last_processed_time'] = datetime.now().isoformat()
                
                if process_result.returncode != 0:
                    logger.error(f"Transcription processing failed: {process_result.stderr}")
                    pipeline_state['last_failed_step'] = 'transcription_processing'
                    pipeline_state['last_error'] = process_result.stderr
                    pipeline_state['last_run_status'] = 'failed'
                    pipeline_state['processing_stats']['failed_processed'] += 1
                    success = False
                else:
                    logger.info("Transcription processing completed successfully")
                    pipeline_state['last_run_status'] = 'success'
                    pipeline_state['processing_stats']['successful_processed'] += 1
                    success = True

                    # Step 4: Process ongoing entries
                    logger.info("Starting ongoing entries processing step")
                    ongoing_script = os.path.join(os.path.dirname(__file__), 
                        'create_journal_of_the_day', 'process_ongoing_entries.py')
                    ongoing_result = subprocess.run(
                        [sys.executable, ongoing_script, '--format', 'json'],
                        capture_output=True,
                        text=True,
                        timeout=1800  # 30 minute timeout
                    )

                    if ongoing_result.returncode != 0:
                        logger.error(f"Ongoing entries processing failed: {ongoing_result.stderr}")
                        pipeline_state['last_failed_step'] = 'ongoing_entries_processing'
                        pipeline_state['last_error'] = ongoing_result.stderr
                        pipeline_state['last_run_status'] = 'failed'
                        success = False
                    else:
                        try:
                            result = json.loads(ongoing_result.stdout)
                            if result['status'] == 'no_file':
                                logger.info("No ongoing entries to process")
                            elif result['status'] != 'success':
                                logger.warning(f"Ongoing entries processing status: {result['message']}")
                            else:
                                logger.info("Ongoing entries processing completed successfully")
                                
                                # Step 5: Send email with summary
                                if result.get('output_file'):  # Check if we have the summary file path
                                    logger.info("Starting email step with summary content")
                                    
                                    # Read the summary content
                                    with open(result['output_file'], 'r', encoding='utf-8') as f:
                                        summary_content = f.read()
                                    
                                    # Import the email sender module
                                    sys.path.append(os.path.join(os.path.dirname(__file__), 'send_email'))
                                    from send_email import send_demo_email
                                    
                                    # Send the email with summary content
                                    email_success, email_message = send_demo_email(summary_content)
                                    if email_success:
                                        logger.info("Email sent successfully")
                                    else:
                                        logger.error(f"Failed to send email: {email_message}")
                                        success = False
                                else:
                                    logger.warning("No summary file path provided in ongoing entries result")
                                    
                        except json.JSONDecodeError:
                            logger.warning("Could not parse JSON output from ongoing entries processing")
        
        # Update state with run information
        pipeline_state['last_run_time'] = datetime.now().isoformat()
        pipeline_state['total_runs'] = pipeline_state.get('total_runs', 0) + 1
        if success:
            pipeline_state['successful_runs'] = pipeline_state.get('successful_runs', 0) + 1
        
        # Save state
        update_pipeline_state(STATE_FILE, pipeline_state)
        
        if success:
            logger.info("Pipeline execution completed successfully")
        return success
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        # Update state for unexpected errors
        pipeline_state = {
            'last_run_time': datetime.now().isoformat(),
            'last_run_status': 'error',
            'last_error': str(e),
            'error_traceback': traceback.format_exc()
        }
        update_pipeline_state(STATE_FILE, pipeline_state)
        return False

def update_pipeline_state(state_file, updates):
    """Update pipeline state file with new information"""
    try:
        with open(state_file, 'w') as f:
            json.dump(updates, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to update state file: {e}")
        # Consider raising the exception to handle it at a higher level
        raise

def main():
    try:
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scheduler.log'),
                logging.StreamHandler()
            ]
        )
        
        # Load configuration
        config = load_config()
        logging.info("Configuration loaded successfully")
        
        # Get the interval in seconds
        interval_seconds = calculate_interval_seconds(config)
        
        # Check for OpenAI API key at startup
        # check_openai_api_key()
        
        # If interval is 0, run once and exit
        if interval_seconds == 0:
            logging.info("Running pipeline once and exiting")
            run_pipeline()
            logging.info("Done. Exiting.")
            return
        
        # Run in a loop with the specified interval
        try:
            while True:
                # Run the pipeline
                run_pipeline()
                
                # Calculate and display the next run time
                next_run = calculate_next_run_time(interval_seconds)
                logging.info(f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Sleep until the next run
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
            print("\nScheduler stopped by user. Exiting.")
        except Exception as e:
            logging.error(f"Error in scheduler: {str(e)}")
            logging.error(traceback.format_exc())
            print(f"Error in scheduler: {str(e)}")
            sys.exit(1)
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()