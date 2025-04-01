#!/usr/bin/env python3
"""
OpenAI Whisper API Transcription

This script transcribes audio files using OpenAI's API:
- whisper-1 API endpoint 
- 4o transcribe API endpoint

It processes audio files in the downloads directory, supporting both
individual files and batch processing based on the configuration.
"""

import os
import sys
import json
import argparse
import logging
import time
import shutil
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import asyncio
import concurrent.futures
import traceback
import platform
import subprocess
import logging.handlers

# Support both package import and direct script execution
try:
    # When running as a package
    from .logging_config import setup_logging
except ImportError:
    try:
        # When running as a script
        from logging_config import setup_logging
    except ImportError:
        # Fallback logging configuration
        def setup_logging(logs_dir, log_filename="app.log", to_file=True, log_level=logging.INFO):
            """Fallback logging setup if logging_config module is not available."""
            logs_dir = Path(logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            handlers = [logging.StreamHandler()]
            
            if to_file:
                log_file = logs_dir / log_filename
                max_size = 1 * 1024 * 1024
                backup_count = 3
                
                rotating_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=max_size,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                handlers.append(rotating_handler)
            
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            
            logger = logging.getLogger()
            
            if to_file:
                logger.info(f"Logging to file: {log_file}")
                logger.info(f"Maximum log size: {max_size/1024/1024:.1f} MB")
                logger.info(f"Number of backup files: {backup_count}")
            
            return logger

# Determine the package directory and project root
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

# Load main configuration first to get directory paths
def load_main_config():
    """Load the main configuration file."""
    try:
        config_path = PACKAGE_DIR / 'config' / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Resolve paths relative to project root
        downloads_path = PROJECT_ROOT / config.get("downloads_directory").lstrip("../")
        config.update({
            "downloads_directory": str(downloads_path),
            "processed_directory": str(PACKAGE_DIR / "processed_audio"),
            "received_transcriptions_directory": str(PACKAGE_DIR / "received_transcriptions")
        })
        return config
    except Exception as e:
        logging.error(f"Error loading {config_path}: {str(e)}")
        return {
            "downloads_directory": str(PACKAGE_DIR / "downloads"),
            "output_file": "transcription.txt",
            "processed_directory": str(PACKAGE_DIR / "processed_audio"),
            "received_transcriptions_directory": str(PACKAGE_DIR / "received_transcriptions")
        }

# Load main config to get directory paths
main_config = load_main_config()

# Define directory paths using Path objects for cross-platform compatibility
CONFIG_DIR = PACKAGE_DIR / 'config'
LOGS_DIR = PACKAGE_DIR / 'logs'
# Use paths from config relative to workspace root
DOWNLOADS_DIR = Path(main_config.get("downloads_directory", "downloads"))
PROCESSED_DIR = Path(main_config.get("processed_directory", "processed_audio"))
RECEIVED_DIR = Path(main_config.get("received_transcriptions_directory", "received_transcriptions"))

# Create directories if they don't exist
for directory in [CONFIG_DIR, LOGS_DIR, DOWNLOADS_DIR, PROCESSED_DIR, RECEIVED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

try:
    import openai
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    print("Error: OpenAI package not found. Install it with pip install openai")
    sys.exit(1)

# Set up logging with rotation using the centralized configuration
logger = setup_logging(LOGS_DIR, log_filename='openai_whisper.log')

# Log startup information
logger.info("Starting OpenAI Whisper transcription service")

# Load the configuration
def load_config():
    """Load the transcription configuration from YAML file."""
    try:
        config_path = CONFIG_DIR / 'transcribe_config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['transcribe_config'], config['output_config'], config['model_capabilities']
    except Exception as e:
        logging.error(f"Error: Could not load {config_path}: {str(e)}")
        sys.exit(1)

def get_openai_client():
    """Initialize and return the OpenAI client."""
    transcribe_config, _, _ = load_config()
    api_key = transcribe_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logging.error("OpenAI API key is not set. Please run setup_transcribe_model.py to configure it.")
        sys.exit(1)
    
    return OpenAI(api_key=api_key)

def get_async_openai_client():
    """Initialize and return the AsyncOpenAI client."""
    transcribe_config, _, _ = load_config()
    api_key = transcribe_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logging.error("OpenAI API key is not set. Please run setup_transcribe_model.py to configure it.")
        sys.exit(1)
    
    return AsyncOpenAI(api_key=api_key)

def find_audio_files(directory):
    """Find all audio files in the specified directory."""
    audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.mp4']
    audio_files = []
    
    # Convert directory to Path object
    dir_path = Path(directory)
    
    # Check if directory exists
    if not dir_path.exists():
        logging.warning(f"Directory {dir_path} does not exist")
        return audio_files
    
    # Scan directory for audio files using Path objects
    try:
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                audio_files.append(str(file_path))
    except Exception as e:
        logging.error(f"Error scanning directory {dir_path}: {str(e)}")
    
    return audio_files

def ensure_processed_directory(directory):
    """Ensure the processed audio directory exists."""
    dir_path = Path(directory)
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True)
            logging.info(f"Created directory: {dir_path}")
        except Exception as e:
            logging.error(f"Error creating directory {dir_path}: {str(e)}")
            return False
    return True

def calculate_duration(file_path):
    """Calculate estimated duration of an audio file in seconds."""
    try:
        # Use ffprobe with platform-agnostic command construction
        ffprobe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        
        # Use subprocess.run with shell=False for better cross-platform compatibility
        result = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        return float(result.stdout.strip())
    except Exception:
        # Fallback: use file size as a very rough estimate (3MB ≈ 1 minute)
        file_size = os.path.getsize(file_path)
        return (file_size / (3 * 1024 * 1024)) * 60  # Convert to seconds

def transcribe_with_whisper1(file_path, config, output_config):
    """Transcribe an audio file using the whisper-1 API."""
    client = get_openai_client()
    
    # Prepare parameters
    whisper_config = config["whisper_api"]
    params = {
        "model": whisper_config["model"],
        "response_format": whisper_config["response_format"],
        "temperature": whisper_config["temperature"],
    }
    
    # Add optional parameters if provided
    if whisper_config["language"]:
        params["language"] = whisper_config["language"]
    
    if whisper_config["prompt"]:
        params["prompt"] = whisper_config["prompt"]
    
    # Open the audio file
    try:
        with open(file_path, "rb") as audio_file:
            logger.info(f"Transcribing {file_path} with whisper-1 API...")
            
            start_time = time.time()
            response = client.audio.transcriptions.create(
                file=audio_file,
                **params
            )
            end_time = time.time()
            
            # Process and return the response
            if whisper_config["response_format"] == "text":
                # The response is already the text content when response_format is 'text'
                transcript = response
            elif whisper_config["response_format"] in ["verbose_json", "json"]:
                # For JSON formats, dump the JSON content
                try:
                    transcript = json.dumps(response.model_dump(), indent=2)
                except AttributeError:
                    # If response is not an object with model_dump method, convert directly
                    if isinstance(response, dict):
                        transcript = json.dumps(response, indent=2)
                    else:
                        transcript = str(response)
            else:
                # For other formats (vtt, srt), convert to string
                transcript = str(response)
            
            logger.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
            return transcript
            
    except Exception as e:
        logger.error(f"Error transcribing {file_path}: {str(e)}")
        traceback.print_exc()
        return None

def transcribe_with_4o(file_path, config, output_config):
    """Transcribe an audio file using the 4o transcribe API."""
    client = get_openai_client()
    
    # Prepare parameters
    transcribe_config = config["4o_transcribe"]
    
    # Open the audio file
    try:
        with open(file_path, "rb") as audio_file:
            logger.info(f"Transcribing {file_path} with 4o transcribe API...")
            
            start_time = time.time()
            
            # Create a file object that OpenAI's API can handle
            file = client.files.create(
                file=audio_file,
                purpose="audio"
            )
            
            # Call the appropriate API based on whether we're using chat or a dedicated endpoint
            response = client.chat.completions.create(
                model=transcribe_config["model"],
                temperature=transcribe_config["temperature"],
                messages=[
                    {"role": "system", "content": "Transcribe the audio accurately"},
                    {"role": "user", "content": [
                        {"type": "text", "text": transcribe_config["prompt"] if transcribe_config["prompt"] else "Please transcribe this audio."},
                        {"type": "file_id", "file_id": file.id}
                    ]}
                ]
            )
            
            # Clean up the file
            client.files.delete(file.id)
            
            end_time = time.time()
            transcript = response.choices[0].message.content
            
            logger.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
            return transcript
            
    except Exception as e:
        logger.error(f"Error transcribing {file_path} with 4o API: {str(e)}")
        traceback.print_exc()
        return None

def chunk_audio_file(file_path, max_chunk_size_ms, output_dir=None):
    """Split an audio file into chunks using ffmpeg."""
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use platform-agnostic path handling
        file_path = Path(file_path)
        base_name = file_path.stem
        extension = file_path.suffix
        
        # Get duration in milliseconds
        duration_ms = int(calculate_duration(str(file_path)) * 1000)
        chunk_size_ms = min(max_chunk_size_ms, duration_ms)
        
        chunks = []
        for i in range(0, duration_ms, chunk_size_ms):
            output_file = output_dir / f"{base_name}_chunk{i//chunk_size_ms}{extension}"
            
            # Construct ffmpeg command in a platform-agnostic way
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", str(file_path),
                "-ss", str(i/1000),  # Convert ms to seconds
                "-t", str(chunk_size_ms/1000),  # Convert ms to seconds
                "-c", "copy",
                "-y",
                str(output_file)
            ]
            
            # Use subprocess.run with shell=False for better cross-platform compatibility
            subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            chunks.append(str(output_file))
        
        return chunks
    except Exception as e:
        logger.error(f"Error chunking audio file: {str(e)}")
        return []

def save_individual_transcription(transcript, audio_file, output_dir, model_type):
    """
    Save an individual transcription to the received_transcriptions directory
    with metadata about which model produced it and when.
    
    Args:
        transcript: The transcription text
        audio_file: The path to the original audio file
        output_dir: The directory to save transcriptions
        model_type: The type of model used (whisper-1 or 4o-transcribe)
    """
    try:
        # Convert all paths to Path objects
        output_path = Path(output_dir)
        audio_path = Path(audio_file)
        
        # Create the directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_path}")
        
        # Get the base filename without extension
        base_name = audio_path.stem
        
        # Create a filename with timestamp and model info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_name}_{model_type}_{timestamp}.txt"
        output_file = output_path / output_filename
        
        # Write the transcription with metadata
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Transcription of {audio_path.name}\n")
            f.write(f"# Model: {model_type}\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Original file: {audio_path}\n\n")
            f.write(transcript)
        
        logger.info(f"Saved individual transcription to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving individual transcription: {str(e)}")
        return False

async def transcribe_audio_files(audio_files, config, output_config):
    """Transcribe a list of audio files."""
    transcripts = []
    
    # Determine if we should chunk audio files
    should_chunk = config.get("chunk_audio", False)
    max_chunk_size = config.get("max_chunk_size", 24 * 60 * 1000)  # Default 24 mins
    
    # Get the transcription model type
    model_type = config["model_type"]
    
    # Process each audio file
    for file_path in audio_files:
        file_path = Path(file_path)
        logger.info(f"Processing {file_path}")
        
        file_chunks = []
        if should_chunk:
            # Chunk the audio file
            file_chunks = chunk_audio_file(str(file_path), max_chunk_size)
        else:
            file_chunks = [str(file_path)]
        
        # Process each chunk
        chunk_transcripts = []
        for chunk in file_chunks:
            chunk_path = Path(chunk)
            # Transcribe the chunk based on model type
            if model_type == "whisper-1":
                transcript = transcribe_with_whisper1(str(chunk_path), config, output_config)
            elif model_type == "4o-transcribe":
                transcript = transcribe_with_4o(str(chunk_path), config, output_config)
            else:
                logger.error(f"Unknown model type: {model_type}")
                continue
            
            if transcript:
                chunk_transcripts.append(transcript)
                
                # Save individual transcription to received_transcriptions directory
                save_individual_transcription(transcript, 
                                          str(file_path) if chunk_path == file_path else str(chunk_path), 
                                          str(RECEIVED_DIR), 
                                          model_type)
            
            # If chunks are in a temp directory, clean up
            if should_chunk and chunk_path != file_path:
                try:
                    chunk_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove temporary chunk file {chunk_path}: {str(e)}")
        
        # Combine chunk transcripts
        if chunk_transcripts:
            combined_transcript = "\n".join(chunk_transcripts)
            transcripts.append(combined_transcript)
    
    return transcripts

def save_transcriptions(transcripts, audio_files, model_type, output_file=None, append=False):
    """
    Save transcriptions to the database and optionally to a file.
    
    Args:
        transcripts: List of transcription texts
        audio_files: List of audio file paths corresponding to the transcripts
        model_type: The model type used for transcription
        output_file: Optional file path to also save as text file
        append: Whether to append to the file if saving to file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import database utilities
        sys.path.insert(0, str(PROJECT_ROOT))
        from db_utils import initialize_db, save_transcription
        
        # Initialize database
        initialize_db()
        
        # For backwards compatibility, also save to file if specified
        if output_file:
            mode = 'a' if append else 'w'
            with open(output_file, mode, encoding='utf-8') as f:
                # Add a timestamp if not appending (new file)
                if not append:
                    f.write(f"# Transcriptions {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                # Write each transcript with a separator
                for i, transcript in enumerate(transcripts):
                    f.write(f"\n--- Transcription {i+1} ---\n\n")
                    f.write(transcript)
                    f.write("\n\n")
            
            logger.info(f"Saved {len(transcripts)} transcriptions to file {output_file}")
        
        # Save each transcript to the database
        for i, transcript in enumerate(transcripts):
            # Get corresponding audio file, or use a placeholder
            audio_file = audio_files[i] if i < len(audio_files) else None
            
            if audio_file:
                # Get file duration if possible
                try:
                    duration = calculate_duration(str(audio_file))
                except:
                    duration = None
                
                # Get filename from path
                filename = Path(audio_file).name
                audio_path = str(audio_file)
                
                # Save to database
                save_transcription(
                    content=transcript,
                    filename=filename,
                    audio_path=audio_path,
                    model_type=model_type,
                    duration_seconds=duration
                )
            else:
                # Save to database without audio file information
                save_transcription(
                    content=transcript,
                    model_type=model_type
                )
        
        logger.info(f"Saved {len(transcripts)} transcriptions to database")
        return True
    except Exception as e:
        logger.error(f"Error saving transcriptions: {str(e)}")
        traceback.print_exc()
        return False

def move_to_processed(file_path, processed_dir):
    """Move a file to the processed directory."""
    # Convert paths to Path objects
    file_path = Path(file_path)
    processed_dir = Path(processed_dir)
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False
    
    try:
        # Create processed directory if it doesn't exist
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the destination path
        processed_path = processed_dir / file_path.name
        
        # If the file already exists in the processed directory, add a timestamp
        if processed_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            processed_path = processed_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        
        # Move the file
        shutil.move(str(file_path), str(processed_path))
        logger.info(f"Moved {file_path} to {processed_path}")
        return True
    except Exception as e:
        logger.error(f"Error moving file {file_path} to processed directory: {str(e)}")
        return False

async def main(model_type=None):
    """Main function to run the transcription process."""
    try:
        # Load configurations
        transcribe_config, output_config, model_capabilities = load_config()
        
        # Override model type if provided
        if model_type:
            transcribe_config["model_type"] = model_type
        
        # Get directories from main config
        downloads_dir = DOWNLOADS_DIR
        processed_dir = PROCESSED_DIR
        output_file = Path(main_config.get("output_file", str(PACKAGE_DIR / "transcription.txt")))
        
        # Check for valid model type
        model_type = transcribe_config["model_type"]
        if model_type not in ["whisper-1", "4o-transcribe"]:
            logger.error(f"Invalid model type for this script: {model_type}")
            logger.error("This script only supports 'whisper-1' and '4o-transcribe' models.")
            logger.error("Use local_whisper.py for local transcription or run setup_transcribe_model.py to change model type.")
            sys.exit(1)
        
        # Ensure the processed directory exists
        if not ensure_processed_directory(processed_dir):
            sys.exit(1)
        
        # Find audio files to transcribe
        audio_files = find_audio_files(downloads_dir)
        
        if not audio_files:
            logger.info(f"No audio files found in {downloads_dir}")
            return
        
        logger.info(f"Found {len(audio_files)} audio files to transcribe")
        
        # Transcribe the audio files
        transcripts = await transcribe_audio_files(audio_files, transcribe_config, output_config)
        
        if not transcripts:
            logger.warning("No transcriptions produced")
            return
        
        # Save the transcriptions to database and optionally to file
        if save_transcriptions(
            transcripts, 
            audio_files,
            model_type,
            output_file if output_config.get("save_to_file", True) else None,
            output_config.get("append_output", False)
        ):
            # Move processed files
            for file_path in audio_files:
                move_to_processed(file_path, processed_dir)
        
    except Exception as e:
        logger.error(f"Error in transcription process: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Transcribe audio files using OpenAI API")
    parser.add_argument("--model_type", help="Specify the model type to use")
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(args.model_type)) 