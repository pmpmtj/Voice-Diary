import os
import io
import pickle
import sys
import logging
from logging.handlers import RotatingFileHandler
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import time
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

def get_base_path():
    """Get the base path for the application, works both in dev and PyInstaller bundle"""
    base_path = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent
    print(f"Base path: {base_path}")  # Debug print
    print(f"Config dir: {base_path / 'config'}")  # Debug print
    return base_path

def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML config from {config_path}: {str(e)}")
        raise

def merge_configs(base_config: Dict[str, Any], gdrive_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge base and Google Drive configurations."""
    config = base_config.copy()
    
    # Update paths with base paths
    for key, value in gdrive_config.get('auth', {}).items():
        if isinstance(value, str):
            config['paths'][key] = value
    
    # Add Google Drive specific settings
    config.update({
        'api': gdrive_config.get('api', {}),
        'auth': gdrive_config.get('auth', {}),
        'folders': gdrive_config.get('folders', {}),
        'file_types': gdrive_config.get('file_types', {}),
        'download': gdrive_config.get('download', {}),
        'error_handling': gdrive_config.get('error_handling', {})
    })
    
    return config

def setup_logging(config: Dict[str, Any]) -> None:
    """Setup logging based on configuration."""
    log_config = config.get('logging', {})
    log_dir = Path(config['paths']['gdrive_logs'])
    log_dir.mkdir(exist_ok=True)
    
    handlers = []
    
    # File handler with rotation
    if 'file' in log_config.get('handlers', {}):
        log_file = log_dir / log_config['handlers']['file']['filename']
        
        # Get rotation settings with fallback values
        max_size_str = log_config['handlers']['file'].get('max_size', '1MB')
        max_size = parse_size(max_size_str) if isinstance(max_size_str, str) else max_size_str
        backup_count = int(log_config['handlers']['file'].get('backup_count', 3))
        
        # Create rotating file handler with UTF-8 encoding
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size, 
            backupCount=backup_count,
            encoding='utf-8'  # Add UTF-8 encoding
        )
        file_handler.setFormatter(logging.Formatter(log_config['format']))
        handlers.append(file_handler)
    
    # Console handler with UTF-8 encoding
    if 'console' in log_config.get('handlers', {}):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_config['format']))
        console_handler.setStream(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'))
        handlers.append(console_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        handlers=handlers,
        force=True  # Ensure our configuration takes precedence
    )

def parse_size(size_str):
    """
    Parse a string representing file size into number of bytes.
    Examples: '1024B', '1KB', '1MB', '1GB'
    """
    try:
        # If it's just a number, return it
        if size_str.isdigit():
            return int(size_str)
        
        # Handle byte units
        if size_str.endswith('B'):
            # Special case for just 'B' unit (not KB, MB, GB)
            if len(size_str) > 1 and size_str[-2] != 'K' and size_str[-2] != 'M' and size_str[-2] != 'G':
                return int(size_str[:-1])  # Remove 'B' and convert to int
        
        # Extract number and unit
        if 'GB' in size_str:
            number = int(size_str[:-2])
            return number * 1024 * 1024 * 1024
        elif 'MB' in size_str:
            number = int(size_str[:-2])
            return number * 1024 * 1024
        elif 'KB' in size_str:
            number = int(size_str[:-2])
            return number * 1024
            
        # If no valid unit is found or parsing fails, return default (1MB)
        return 1024 * 1024
    except (ValueError, IndexError):
        return 1024 * 1024  # Default to 1MB if parsing fails

# Load configurations
try:
    base_path = get_base_path()
    config_dir = base_path / 'config'
    if not config_dir.exists():
        print(f"Error: Config directory '{config_dir.resolve()}' not found.")
        print("Please make sure the config directory exists with base.yaml and gdrive.yaml files.")
        sys.exit(1)
        
    base_config_path = config_dir / 'base.yaml'
    gdrive_config_path = config_dir / 'gdrive.yaml'
    
    if not base_config_path.exists():
        print(f"Error: Base configuration file '{base_config_path.resolve()}' not found.")
        sys.exit(1)
        
    if not gdrive_config_path.exists():
        print(f"Error: Google Drive configuration file '{gdrive_config_path.resolve()}' not found.")
        sys.exit(1)
    
    BASE_CONFIG = load_yaml_config(base_config_path)
    GDRIVE_CONFIG = load_yaml_config(gdrive_config_path)
    CONFIG = merge_configs(BASE_CONFIG, GDRIVE_CONFIG)

    # Set up and create path directories
    for dir_name in ['downloads', 'gdrive_credentials', 'gdrive_logs']:
        # Create directories relative to script location
        dir_path = base_path / CONFIG['paths'].get(dir_name, dir_name)
        dir_path.mkdir(exist_ok=True)
        CONFIG['paths'][dir_name] = str(dir_path)
    
    # Setup logging
    setup_logging(CONFIG)
    logger = logging.getLogger(__name__)

    # Handle stdout encoding in an OS-agnostic way
    # Only modify stdout if it has a buffer (which it should on all modern systems)
    # This prevents errors on systems where stdout might be redirected
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding=CONFIG['file_operations']['encoding'],
                errors='replace'  # Handle encoding errors gracefully
            )
    except Exception as e:
        # Log the error but continue execution
        print(f"Warning: Could not set stdout encoding: {str(e)}")

    # Define paths based on configuration using pathlib.Path
    CREDENTIALS_DIR = Path(CONFIG['paths']['gdrive_credentials'])
    CREDENTIALS_FILE = CREDENTIALS_DIR / CONFIG['auth']['credentials_file']
    TOKEN_FILE = CREDENTIALS_DIR / CONFIG['auth']['token_file']
    DOWNLOAD_DIR = Path(CONFIG['paths']['downloads'])
except Exception as e:
    print(f"Error initializing configuration: {str(e)}")
    print("Please make sure the config files exist in the config directory.")
    sys.exit(1)

def check_credentials_file() -> bool:
    """Check if credentials.json exists and provide help if not."""
    if not CREDENTIALS_FILE.exists():
        logger.error(f"'{CREDENTIALS_FILE}' file not found!")
        print("\nTo create your credentials file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select an existing one")
        print("3. Enable the Google Drive API:")
        print("   - Navigate to 'APIs & Services' > 'Library'")
        print("   - Search for 'Google Drive API' and enable it")
        print("4. Create OAuth credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Select 'Desktop app' as application type")
        print("   - Download the JSON file and rename it to 'credentials.json'")
        print(f"   - Place it in the '{CREDENTIALS_DIR}' directory")
        print("\nThen run this script again.")
        return False
    return True

def authenticate_google_drive():
    """Authenticate with Google Drive API using OAuth."""
    try:
        creds = None
        
        # The token.pickle file stores the user's access and refresh tokens
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
                
        # If no valid credentials are available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not check_credentials_file():
                    sys.exit(1)
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), CONFIG['api']['scopes'])
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build the service with the credentials
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise

def find_folder_by_name(service, folder_name: str) -> Optional[str]:
    """
    Find a folder in Google Drive by name.
    
    Args:
        service: The Google Drive service object
        folder_name: The name of the folder to find
        
    Returns:
        The folder ID if found, None otherwise
    """
    try:
        # Search for the folder by name
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=5  # Limit to avoid long searches for common names
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            logger.warning(f"No folder found with name: {folder_name}")
            return None
            
        if len(items) > 1:
            logger.warning(f"Multiple folders found with name: {folder_name}. Using the first one.")
            
        # Return the ID of the first matching folder
        folder_id = items[0]['id']
        logger.info(f"Found folder '{folder_name}' with ID: {folder_id}")
        return folder_id
        
    except Exception as e:
        logger.error(f"Error finding folder '{folder_name}': {str(e)}")
        return None

def find_file_by_name_in_folder(service, file_name, folder_id):
    """Find a file by name in a specific Google Drive folder."""
    # Search for files with the given name in the specified folder
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        return None
    else:
        # Return the first matching file
        return items[0]

def list_files_in_folder(service, folder_id, file_extensions=None):
    """List all files in a Google Drive folder with filtering by file extension.
    
    Args:
        service: Google Drive API service instance
        folder_id: ID of the folder to list files from
        file_extensions: Optional dict with 'include' list of file extensions
        
    Returns:
        list: List of file objects
    """
    if file_extensions is None:
        file_extensions = {"include": []}
    
    query = f"'{folder_id}' in parents and trashed = false"
    
    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            logger.info(f"No files found in folder {folder_id}.")
            return []
        
        # Filter files by extension if extension lists are provided
        include_extensions = file_extensions.get("include", [])
        
        filtered_files = []
        for file in files:
            # Skip folders
            if file.get('mimeType') == 'application/vnd.google-apps.folder':
                continue
                
            filename = file['name']
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Only include files with specified extensions
            if include_extensions and file_ext not in include_extensions:
                continue
                
            filtered_files.append(file)
        
        return filtered_files
        
    except Exception as e:
        logger.error(f"Error listing files in folder {folder_id}: {str(e)}")
        return []

def download_file(service, file_id, file_name=None, download_dir=None):
    """Download a file from Google Drive by ID.
    
    Args:
        service: Google Drive service instance
        file_id: ID of the file to download OR a file object with 'id' and 'name' keys
        file_name: Name of the file to save (optional if file_id is a dict) or full path to save the file to
        download_dir: Optional directory path where to save downloaded file
    
    Returns:
        dict: A dictionary with the download result information
    """
    try:
        # If file_id is a dict (file object), extract the id and name
        if isinstance(file_id, dict):
            file_info = file_id
            file_name = file_info.get('name')
            file_id = file_info.get('id')
        
        # Determine the output path
        if os.path.isabs(file_name) or '/' in file_name or '\\' in file_name:
            # file_name is already a full path
            output_path = Path(file_name)
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Extract just the filename for logging
            display_name = output_path.name
        else:
            # file_name is just a filename, use download_dir
            if download_dir:
                DOWNLOAD_DIR = Path(download_dir)
            else:
                DOWNLOAD_DIR = Path(CONFIG['paths']['downloads'])
            
            DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
            
            # Generate filename with timestamp if configured
            if CONFIG.get('download', {}).get('add_timestamps', False):
                timestamp_format = CONFIG.get('download', {}).get('timestamp_format', '%Y%m%d_%H%M%S_%f')
                output_filename = generate_filename_with_timestamp(file_name, timestamp_format)
            else:
                output_filename = file_name
                
            # Create the full file path
            output_path = DOWNLOAD_DIR / output_filename
            display_name = file_name
            
        logger.info(f"Downloading {display_name} as {output_path}")
        
        # Create a file handler
        with open(output_path, 'wb') as f:
            # Get the file as media content
            request = service.files().get_media(fileId=file_id)
            
            # Download the file
            downloader = MediaIoBaseDownload(f, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}% complete.")
        
        logger.info(f"Download complete! Saved as: {output_path}")
        
        return {
            "success": True,
            "original_filename": display_name,
            "saved_as": str(output_path),
            "file_id": file_id
        }
            
    except Exception as e:
        logger.error(f"Error downloading file {file_name}: {str(e)}")
        
        return {
            "success": False,
            "original_filename": file_name,
            "file_id": file_id,
            "error": str(e)
        }

def delete_file(service, file_id, file_name=None):
    """Delete a file from Google Drive.
    
    Args:
        service: Google Drive API service instance
        file_id: ID of the file to delete OR a file object with 'id' and 'name' keys
        file_name: Name of the file (for logging purposes), optional if file_id is a dict
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # If file_id is a dict (file object), extract the id and name
        if isinstance(file_id, dict):
            file_name = file_id.get('name', 'Unknown file')
            file_id = file_id.get('id')
        
        # Execute the deletion
        logger.info(f"Deleting file: {file_name}")
        service.files().delete(fileId=file_id).execute()
        logger.info(f"File '{file_name}' deleted successfully.")
        return True
    except Exception as e:
        logger.error(f"Error deleting file '{file_name}': {str(e)}")
        return False

def process_folder(service, folder_id, folder_name, parent_path="", dry_run=False):
    """Process files in a Google Drive folder (non-recursively)."""
    try:
        # Only look for files (not folders) in the specified folder
        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime, fileExtension)",
            pageSize=1000
        ).execute()
        items = results.get('files', [])
        
        if not items:
            logger.info(f"No files found in folder: {folder_name}")
            return {
                'total_files': 0,
                'processed_files': 0,
                'downloaded_files': 0,
                'skipped_files': 0,
                'error_files': 0,
                'deleted_files': 0
            }
            
        logger.info(f"Found {len(items)} files in folder: {folder_name}")
        
        # Count metrics
        stats = {
            'total_files': len(items),
            'processed_files': 0,
            'downloaded_files': 0,
            'skipped_files': 0,
            'error_files': 0,
            'deleted_files': 0
        }
        
        # Setup download directory - now using base downloads directory directly
        base_download_dir = Path(CONFIG['paths']['downloads'])
        
        # Process each file
        for item in items:
            item_id = item['id']
            item_name = item['name']
            mime_type = item.get('mimeType', '')
            
            stats['processed_files'] += 1
            
            # Check if file type is included
            file_ext = os.path.splitext(item_name)[1].lower()
            included_types = CONFIG.get('file_types', {}).get('include', [])
            
            if included_types and file_ext not in included_types:
                logger.info(f"Skipping non-included file type: {item_name}")
                stats['skipped_files'] += 1
                continue
            
            # Generate output path - now directly in downloads folder
            if CONFIG.get('download', {}).get('add_timestamps', False):
                timestamp_format = CONFIG.get('download', {}).get('timestamp_format', '%Y%m%d_%H%M%S_%f')
                timestamped_name = generate_filename_with_timestamp(item_name, timestamp_format)
                output_path = base_download_dir / timestamped_name
            else:
                output_path = base_download_dir / item_name
            
            # In dry run mode, just log what would happen
            if dry_run:
                print(f"Would download: {item_name} -> {output_path}")
                if CONFIG['download'].get('delete_after_download', False):
                    print(f"Would delete file from Google Drive after download: {item_name}")
                stats['downloaded_files'] += 1
                continue
            
            # Download the file
            try:
                download_result = download_file(service, item_id, str(output_path))
                
                if download_result['success']:
                    stats['downloaded_files'] += 1
                    
                    # Delete file from Google Drive if configured
                    if CONFIG['download'].get('delete_after_download', False):
                        delete_file(service, item_id, item_name)
                        stats['deleted_files'] += 1
                else:
                    stats['error_files'] += 1
            except Exception as e:
                logger.error(f"Error processing file {item_name}: {str(e)}")
                stats['error_files'] += 1
        
        # Log statistics for this folder
        logger.info(f"Folder '{folder_name}' statistics:")
        logger.info(f"  - Total files: {stats['total_files']}")
        logger.info(f"  - Processed files: {stats['processed_files']}")
        logger.info(f"  - Downloaded files: {stats['downloaded_files']}")
        logger.info(f"  - Skipped files: {stats['skipped_files']}")
        logger.info(f"  - Failed files: {stats['error_files']}")
        logger.info(f"  - Deleted files: {stats['deleted_files']}")
        
        return stats
        
    except Exception as e:
        logger.exception(f"Error processing folder '{folder_name}': {str(e)}")
        return {
            'total_files': 0,
            'processed_files': 0,
            'downloaded_files': 0,
            'skipped_files': 0,
            'error_files': 1,
            'deleted_files': 0
        }

def generate_filename_with_timestamp(filename: str, timestamp_format: Optional[str] = None) -> str:
    """
    Generate a filename with a timestamp prefix.
    
    Args:
        filename: The original filename
        timestamp_format: Format string for the timestamp, if None the original filename is returned
    
    Returns:
        The filename with timestamp prefix added
    """
    if not timestamp_format:
        return filename
        
    timestamp = datetime.now().strftime(timestamp_format)
    return f"{timestamp}_{filename}"

def main():
    """Main function to process Google Drive files."""
    if not check_credentials_file():
        return
    
    try:
        # Authenticate with Google Drive
        service = authenticate_google_drive()
        if not service:
            logger.error("Failed to authenticate with Google Drive.")
            return
            
        # Get target folders from configuration
        target_folders = CONFIG['folders'].get('target_folders', ['root'])
        
        # Check if running in dry run mode
        dry_run = CONFIG.get('dry_run', False)
        if dry_run:
            logger.info("Running in DRY RUN mode - no files will be downloaded or deleted")
            print("\n=== DRY RUN MODE - NO FILES WILL BE DOWNLOADED OR DELETED ===\n")
        
        # Process each target folder
        for folder_name in target_folders:
            if folder_name.lower() == 'root':
                # Root folder has a special ID
                folder_id = 'root'
                logger.info(f"Processing root folder")
            else:
                # Find folder by name
                logger.info(f"Looking for folder: {folder_name}")
                folder_id = find_folder_by_name(service, folder_name)
                
                if not folder_id:
                    logger.warning(f"Folder '{folder_name}' not found. Skipping.")
                    continue
                
                logger.info(f"Processing folder: {folder_name} (ID: {folder_id})")
            
            # Process files in the folder
            process_folder(service, folder_id, folder_name, dry_run=dry_run)
        
        logger.info("Google Drive download process completed.")
        
    except Exception as e:
        logger.exception(f"An error occurred during the download process: {str(e)}")

def run_with_config(config: Dict[str, Any]) -> None:
    """
    Run the Google Drive downloader with the provided configuration.
    This allows the script to be called programmatically with a custom configuration.
    
    Args:
        config: Configuration dictionary with all settings needed for the download
    """
    global CONFIG, logger, CREDENTIALS_DIR, CREDENTIALS_FILE, TOKEN_FILE, DOWNLOAD_DIR
    
    # Set global variables based on the provided config
    CONFIG = config
    
    # Setup logging
    setup_logging(CONFIG)
    logger = logging.getLogger(__name__)
    
    # Define paths based on configuration
    CREDENTIALS_DIR = Path(CONFIG['paths']['gdrive_credentials'])
    CREDENTIALS_FILE = CREDENTIALS_DIR / CONFIG['auth']['credentials_file']
    TOKEN_FILE = CREDENTIALS_DIR / CONFIG['auth']['token_file']
    DOWNLOAD_DIR = Path(CONFIG['paths']['downloads'])
    
    # Create necessary directories
    CREDENTIALS_DIR.mkdir(exist_ok=True)
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    
    # Run the main process
    main()

if __name__ == "__main__":
    main()
