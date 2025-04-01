import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Define the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Loaded environment variables from .env file at {env_path}")

# Database configuration
def get_db_url():
    """Get database URL from environment or return a default local URL"""
    # First try to get the URL from environment variable
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        # If running locally, use a default URL
        logging.warning("DATABASE_URL not found in environment. Using local database.")
        db_url = "postgresql://postgres:postgres@localhost:5432/transcriptions"
    
    return db_url
