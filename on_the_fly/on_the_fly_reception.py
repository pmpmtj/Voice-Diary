"""
On-the-Fly Reception Report Generator

This standalone script generates reports from the transcription database for specific date ranges
and optionally emails the results using the send_email.py module.

Key features:
- Query transcriptions for specified date range
- Process with OpenAI LLM using a custom prompt
- Save output to specified directory
- Optionally send email with results
- Independent from the scheduler pipeline

Usage: python on_the_fly_reception.py
"""

import os
import sys
import json
import logging
import sqlite3
from logging.handlers import RotatingFileHandler
from datetime import datetime
import traceback
import dotenv

# Make sure we can import send_email module
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

try:
    from send_email import send_email as email_sender
except ImportError:
    print("Error: Could not import send_email module. Make sure it's in the parent directory.")
    sys.exit(1)

# Load environment variables from .env file
dotenv.load_dotenv(os.path.join(project_root, '.env'))

# Configure logging
def setup_logging():
    """Set up logging with rotation"""
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "on_the_fly.log")
    max_size = 1 * 1024 * 1024  # 1 MB
    backup_count = 3  # Keep last 3 logs
    
    handler = RotatingFileHandler(
        log_file, maxBytes=max_size, backupCount=backup_count
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def load_config():
    """Load configuration from on_the_fly_config.json file"""
    config_path = os.path.join(script_dir, "config", "on_the_fly_config.json")
    
    if not os.path.exists(config_path):
        logging.error(f"Config file not found: {config_path}")
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required configuration parameters
        required_params = ["prompt", "send_email", "recipient", "subject", 
                          "lookup_date_range", "output_directory", "output_file_name"]
        
        for param in required_params:
            if param not in config:
                logging.error(f"Missing required parameter in config: {param}")
                print(f"ERROR: Missing required parameter in config: {param}")
                sys.exit(1)
                
        return config
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {str(e)}")
        print(f"ERROR: Invalid JSON in config file: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to load config: {str(e)}")
        print(f"ERROR: Failed to load config: {str(e)}")
        sys.exit(1)

def connect_to_database():
    """Connect to the PostgreSQL database using connection details from .env"""
    try:
        import psycopg2
        from psycopg2.extras import DictCursor
        
        # Get database URL from environment variable
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logging.error("DATABASE_URL not found in environment variables")
            print("ERROR: DATABASE_URL not found in environment. Check your .env file.")
            sys.exit(1)
            
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        conn.cursor_factory = DictCursor
        logging.info(f"Connected to PostgreSQL database: {database_url.split('@')[1] if '@' in database_url else database_url}")
        
        # Verify the optimize_transcriptions table exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_name = 'optimize_transcriptions'
            );
        """)
        if not cursor.fetchone()[0]:
            logging.error("Table 'optimize_transcriptions' does not exist in the database")
            print("ERROR: Table 'optimize_transcriptions' does not exist in the database")
            sys.exit(1)
            
        # Check table schema
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'optimize_transcriptions'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        required_columns = ['id', 'content', 'metadata']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logging.error(f"Missing required columns in 'optimize_transcriptions': {', '.join(missing_columns)}")
            print(f"ERROR: Missing required columns in 'optimize_transcriptions': {', '.join(missing_columns)}")
            sys.exit(1)
            
        return conn
    except ImportError:
        logging.error("PostgreSQL driver (psycopg2) not installed")
        print("ERROR: PostgreSQL driver not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to connect to database: {str(e)}")
        print(f"ERROR: Failed to connect to database: {str(e)}")
        sys.exit(1)

def query_transcriptions(conn, date_range):
    """
    Query transcriptions from database based on date range
    
    Args:
        conn: Database connection
        date_range: List of dates in YYMMDD format
    
    Returns:
        List of transcription entries
    """
    try:
        cursor = conn.cursor()
        
        # Convert the input date format (YYMMDD) to database date format (YYYY-MM-DD)
        formatted_dates = []
        for date_str in date_range:
            if len(date_str) == 6:  # YYMMDD format
                year = int("20" + date_str[0:2])
                month = int(date_str[2:4])
                day = int(date_str[4:6])
                formatted_date = f"{year}-{month:02d}-{day:02d}"
                formatted_dates.append(formatted_date)
            else:
                logging.error(f"Invalid date format: {date_str}. Expected YYMMDD format.")
                print(f"ERROR: Invalid date format: {date_str}. Expected YYMMDD format.")
                return []
        
        logging.info(f"Querying for dates: {formatted_dates}")
        
        if len(formatted_dates) == 1:
            # Single date query - extract the date part from the timestamp
            query = """
            SELECT id, content, metadata, created_at
            FROM optimize_transcriptions 
            WHERE DATE(created_at) = %s
            ORDER BY created_at
            """
            cursor.execute(query, (formatted_dates[0],))
        else:
            # Date range query (start to end inclusive)
            query = """
            SELECT id, content, metadata, created_at
            FROM optimize_transcriptions 
            WHERE DATE(created_at) >= %s AND DATE(created_at) <= %s
            ORDER BY DATE(created_at), created_at
            """
            cursor.execute(query, (formatted_dates[0], formatted_dates[1]))
            
        results = cursor.fetchall()
        
        # Convert results to list of dictionaries with consistent structure
        entries = []
        for row in results:
            # Extract date and time from created_at timestamp
            created_dt = row['created_at']
            
            # Create a new entry dictionary
            entry = {
                'id': row['id'],
                'content': row['content'],
                'date': created_dt.strftime('%y%m%d'),  # Format as YYMMDD
                'time': created_dt.strftime('%H%M')     # Format as HHMM
            }
            
            # If there's also metadata with date/time, prefer that over created_at
            if row['metadata'] and isinstance(row['metadata'], dict):
                metadata = row['metadata']
                if 'date' in metadata:
                    entry['date'] = metadata.get('date')
                if 'time' in metadata:
                    entry['time'] = metadata.get('time')
                
            entries.append(entry)
            
        logging.info(f"Query returned {len(entries)} entries")
        return entries
    except Exception as e:
        logging.error(f"Database query failed: {str(e)}")
        print(f"ERROR: Database query failed: {str(e)}")
        traceback.print_exc()  # Print the full traceback for debugging
        return []

def process_with_openai(entries, prompt_template):
    """
    Process transcription entries with OpenAI
    
    Args:
        entries: List of transcription entries
        prompt_template: Template for the OpenAI prompt
    
    Returns:
        Generated report text
    """
    try:
        # Import requests for API call
        import requests
        
        # Check for OpenAI API key - first in environment, then in .env
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.warning("OPENAI_API_KEY not found in environment variables, checking .env file")
            # We already loaded the .env file at the top of the script
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not api_key:
            logging.error("OpenAI API key not found in environment variables or .env file")
            print("ERROR: OpenAI API key not found. Set OPENAI_API_KEY environment variable or add it to .env file.")
            sys.exit(1)
            
        # Prepare entries for prompt
        entries_text = ""
        for entry in entries:
            # Format the date for better readability (if possible)
            date_str = entry.get('date', 'unknown')
            time_str = entry.get('time', 'unknown')
            
            # Try to format the date if it's in the format YYMMDD
            if date_str != 'unknown' and len(date_str) == 6:
                try:
                    # For YYMMDD format
                    year = int("20" + date_str[0:2])  # Assume 20YY for the year
                    month = int(date_str[2:4])
                    day = int(date_str[4:6])
                    formatted_date = f"{year}-{month:02d}-{day:02d}"
                except ValueError:
                    formatted_date = date_str
            else:
                formatted_date = date_str
                
            entries_text += f"Date: {formatted_date}, Time: {time_str}\n"
            entries_text += f"Content: {entry.get('content', '')}\n\n"
        
        logging.info(f"Prepared {len(entries)} entries for OpenAI processing")
        
        # Format the prompt with actual entries
        prompt = prompt_template.format(entries=entries_text)
        
        # Set up the API request headers and payload
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-4",  # Use the same model as in the pipeline
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that processes transcription entries."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # Define API endpoint
        api_endpoint = "https://api.openai.com/v1/chat/completions"
        
        # Send request to OpenAI API
        logging.info("Sending request to OpenAI API")
        response = requests.post(
            api_endpoint,
            headers=headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Process the response
        result = response.json()
        generated_text = result['choices'][0]['message']['content'].strip()
        
        # Log usage
        usage = result.get('usage', {})
        logging.info(f"OpenAI API usage - Prompt tokens: {usage.get('prompt_tokens', 0)}, " +
                    f"Completion tokens: {usage.get('completion_tokens', 0)}, " +
                    f"Total tokens: {usage.get('total_tokens', 0)}")
        
        logging.info("Successfully received response from OpenAI API")
        return generated_text
        
    except ImportError as e:
        logging.error(f"Missing required package: {str(e)}")
        print(f"ERROR: Missing required package: {str(e)}. Install with pip.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error: {str(e)}")
        print(f"ERROR: API request error: {str(e)}")
        return f"Error generating report: API request failed - {str(e)}"
    except Exception as e:
        logging.error(f"OpenAI processing failed: {str(e)}")
        print(f"ERROR: OpenAI processing failed: {str(e)}")
        return f"Error generating report: {str(e)}"

def save_to_file(text, config):
    """Save generated text to output file"""
    try:
        # Ensure output directory exists
        output_dir = os.path.join(script_dir, config["output_directory"])
        os.makedirs(output_dir, exist_ok=True)
        
        # Create timestamp with seconds granularity
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output file path with timestamp
        output_file = os.path.join(output_dir, f"{timestamp}{config['output_file_name']}.txt")
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
            
        logging.info(f"Report saved to: {output_file}")
        print(f"Report saved to: {output_file}")
        
        return output_file
    except Exception as e:
        logging.error(f"Failed to save output file: {str(e)}")
        print(f"ERROR: Failed to save output file: {str(e)}")
        return None

def send_email(text, config):
    """Send email with generated report"""
    if not config.get("send_email", False):
        logging.info("Email sending disabled in config")
        return False, "Email sending disabled in config"
    
    try:
        # Check if Gmail credential files exist
        credentials_path = os.path.join(script_dir, "config", "credentials_gmail.json")
        token_path = os.path.join(script_dir, "config", "token_gmail.pickle")
        
        if not os.path.exists(credentials_path):
            logging.error(f"Gmail credentials file not found: {credentials_path}")
            print(f"ERROR: Gmail credentials file not found: {credentials_path}")
            print("\nTo create your Gmail credentials file:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Select your project")
            print("3. Enable the Gmail API:")
            print("   - Navigate to 'APIs & Services' > 'Library'")
            print("   - Search for 'Gmail API' and enable it")
            print("4. Create OAuth credentials:")
            print("   - Go to 'APIs & Services' > 'Credentials'")
            print("   - Click 'Create Credentials' > 'OAuth client ID'")
            print("   - Select 'Desktop app' as application type")
            print("   - Download the JSON file and rename it to 'credentials_gmail.json'")
            print("   - Place it in the on_the_fly/config directory")
            return False, "Gmail credentials file not found"
        
        # Prepare email service - Note: This will use the credentials file and create the token file
        creds = email_sender.authenticate_gmail()
        if not creds:
            return False, "Failed to authenticate with Gmail"
        
        # Create Gmail API service
        service = email_sender.build('gmail', 'v1', credentials=creds)
        
        # Get the authenticated user's email address
        user_profile = service.users().getProfile(userId='me').execute()
        sender = user_profile['emailAddress']
        
        # Create and send email
        message = email_sender.create_message(
            sender,
            config["recipient"],
            config["subject"],
            text
        )
        
        result = email_sender.send_message(service, 'me', message)
        
        if result:
            logging.info("Email sent successfully")
            print("Email sent successfully")
            return True, "Email sent successfully"
        else:
            logging.error("Failed to send email")
            print("Failed to send email")
            return False, "Failed to send email"
            
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        print(f"ERROR: Error sending email: {str(e)}")
        return False, f"Error sending email: {str(e)}"

def main():
    """Main execution function"""
    try:
        # Set up logging
        logger = setup_logging()
        
        # Log start of execution
        logging.info("Starting On-the-Fly Reception Report Generator")
        print("Starting On-the-Fly Reception Report Generator")
        
        # Load configuration
        config = load_config()
        logging.info("Configuration loaded successfully")
        
        # If email sending is enabled, check for Gmail credentials early
        if config.get("send_email", False):
            credentials_path = os.path.join(script_dir, "config", "credentials_gmail.json")
            if not os.path.exists(credentials_path):
                logging.warning("Email sending is enabled, but Gmail credentials file not found")
                print("WARNING: Email sending is enabled, but Gmail credentials file not found")
                print(f"Expected location: {credentials_path}")
                print("Email will not be sent unless you add the credentials file")
        
        # Connect to database
        conn = connect_to_database()
        logging.info("Connected to database")
        
        # Query transcriptions
        date_range = config["lookup_date_range"]
        entries = query_transcriptions(conn, date_range)
        
        if not entries:
            logging.warning(f"No entries found for date range: {date_range}")
            print(f"WARNING: No entries found for date range: {date_range}")
            conn.close()
            return
            
        logging.info(f"Found {len(entries)} entries for processing")
        
        # Process with OpenAI
        report_text = process_with_openai(entries, config["prompt"])
        logging.info("Generated report with OpenAI")
        
        # Save to file
        output_file = save_to_file(report_text, config)
        
        # Send email if enabled
        if config.get("send_email", False):
            success, message = send_email(report_text, config)
            if success:
                logging.info("Email sent successfully")
            else:
                logging.error(f"Email sending failed: {message}")
        
        # Close database connection
        conn.close()
        logging.info("On-the-Fly Reception Report Generator completed successfully")
        print("On-the-Fly Reception Report Generator completed successfully")
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.error(traceback.format_exc())
        print(f"ERROR: An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
