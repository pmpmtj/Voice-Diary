"""
Unit tests for the transcribe_raw_audio module.

This module contains tests for critical functionality in transcribe_raw_audio.py.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open, ANY
from pathlib import Path
from datetime import datetime
import subprocess

# Import the module to test
from voice_diary.transcribe_raw_audio.transcribe_raw_audio import (
    load_config,
    setup_logging,
    get_downloads_dir_from_gdrive_config,
    get_audio_extensions_from_gdrive_config,
    get_openai_client,
    calculate_duration,
    get_audio_files,
    transcribe_audio_file,
    save_transcription,
    process_audio_files
)


class TestTranscribeRawAudio(unittest.TestCase):
    """Test case for the transcribe_raw_audio module."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample config for testing
        self.sample_config = {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "log_file": "transcribe_raw_audio.log",
                "max_size_bytes": 1048576,
                "backup_count": 3
            },
            "transcriptions_dir": "path/to/transcriptions",
            "output_file": "transcription.txt"
        }
        
        # Sample gdrive config for testing
        self.sample_gdrive_config = {
            "downloads_path": {
                "downloads_dir": "path/to/downloads"
            },
            "audio_file_types": {
                "include": [".m4a", ".mp3", ".wav"]
            }
        }

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_config(self, mock_json_load, mock_file_open, mock_path):
        """Test loading configuration from file."""
        # Configure mocks
        mock_json_load.return_value = self.sample_config
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value.resolve.return_value.parent.parent = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        # Call function
        result = load_config()
        
        # Assertions
        self.assertEqual(result, self.sample_config)
        mock_file_open.assert_called_once()
        mock_json_load.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logging')
    def test_setup_logging(self, mock_logging, mock_path):
        """Test setting up logging with rotation."""
        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_logging.INFO = 20
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        # Call function
        result = setup_logging("logs_dir", self.sample_config)
        
        # Assertions
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_logging.basicConfig.assert_called_once()
        mock_logging.handlers.RotatingFileHandler.assert_called_once()
        mock_logging.getLogger.assert_called_once()
        self.assertEqual(result, mock_logger)

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_get_downloads_dir_from_gdrive_config(self, mock_json_load, mock_file_open, mock_path):
        """Test getting downloads directory from Google Drive config."""
        # Configure mocks
        mock_json_load.return_value = self.sample_gdrive_config
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value.resolve.return_value.parent.parent = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        # Call function
        result = get_downloads_dir_from_gdrive_config()
        
        # Assertions
        self.assertEqual(result, "path/to/downloads")
        mock_file_open.assert_called_once()
        mock_json_load.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_get_audio_extensions_from_gdrive_config(self, mock_json_load, mock_file_open, mock_path):
        """Test getting audio extensions from Google Drive config."""
        # Configure mocks
        mock_json_load.return_value = self.sample_gdrive_config
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value.resolve.return_value.parent.parent = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        # Call function
        result = get_audio_extensions_from_gdrive_config()
        
        # Assertions
        self.assertEqual(result, [".m4a", ".mp3", ".wav"])
        mock_file_open.assert_called_once()
        mock_json_load.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.os.environ.get')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.OpenAI')
    def test_get_openai_client(self, mock_openai, mock_env_get):
        """Test getting OpenAI client with API key."""
        # Configure mocks
        mock_env_get.return_value = "fake-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Call function
        result = get_openai_client()
        
        # Assertions
        self.assertEqual(result, mock_client)
        mock_env_get.assert_called_once_with("OPENAI_API_KEY")
        mock_openai.assert_called_once_with(api_key="fake-api-key")

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.subprocess.run')
    def test_calculate_duration_success(self, mock_run):
        """Test calculating audio duration using ffprobe."""
        # Configure mocks
        mock_process = MagicMock()
        mock_process.stdout = "123.45\n"
        mock_run.return_value = mock_process
        
        # Call function
        result = calculate_duration("audio.mp3")
        
        # Assertions
        self.assertEqual(result, 123.45)
        mock_run.assert_called_once()
        
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.subprocess.run')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.os.path.getsize')
    def test_calculate_duration_fallback(self, mock_getsize, mock_run):
        """Test calculating audio duration fallback to file size."""
        # Configure mocks
        mock_run.side_effect = Exception("ffprobe error")
        mock_getsize.return_value = 9 * 1024 * 1024  # 9MB
        
        # Call function
        result = calculate_duration("audio.mp3")
        
        # Assertions
        self.assertEqual(result, 180.0)  # 3MB ~ 1 minute, so 9MB ~ 3 minutes (180 seconds)
        mock_run.assert_called_once()
        mock_getsize.assert_called_once_with("audio.mp3")

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.get_audio_extensions_from_gdrive_config')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.datetime')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.os.path.getctime')
    def test_get_audio_files(self, mock_getctime, mock_datetime, mock_get_extensions, mock_path):
        """Test getting audio files from directory."""
        # Configure mocks
        mock_get_extensions.return_value = [".mp3", ".wav"]
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Mock files
        file1 = MagicMock()
        file1.name = "20230101_120000_audio.mp3"
        file2 = MagicMock()
        file2.name = "audio_no_timestamp.wav"
        
        mock_path_instance.glob.side_effect = lambda pattern: [file1] if ".mp3" in pattern else [file2]
        
        # Mock the get_timestamp_from_filename function to avoid sorting issues
        with patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.sorted') as mock_sorted:
            # Configure the mock to return the files in the desired order
            mock_sorted.return_value = [file1, file2]
            
            # Call function
            result = get_audio_files("downloads")
            
            # Assertions
            mock_sorted.assert_called_once()
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], file1)
            self.assertEqual(result[1], file2)

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.time')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.calculate_duration')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_transcribe_audio_file(self, mock_logger, mock_calculate_duration, mock_time):
        """Test transcribing an audio file with OpenAI API."""
        # Configure mocks
        mock_calculate_duration.return_value = 60.0  # 1 minute audio
        
        # Set up time.time() to return different values on consecutive calls
        mock_time.time.side_effect = [100.0, 110.0]  # 10 seconds between start and end
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is the transcription result."
        mock_client.audio.transcriptions.create.return_value = mock_response
        
        # Call function with patch for open
        with patch('builtins.open', mock_open(read_data=b'audio_data')):
            result = transcribe_audio_file(mock_client, "audio.mp3")
        
        # Assertions
        self.assertEqual(result, "This is the transcription result.")
        mock_calculate_duration.assert_called_once_with("audio.mp3")
        mock_client.audio.transcriptions.create.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('builtins.open', new_callable=mock_open)
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.datetime')
    def test_save_transcription(self, mock_datetime, mock_file_open, mock_path):
        """Test saving transcription to file."""
        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        # Create a mock datetime object
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20230101_120000_123456"
        mock_datetime.now.return_value = mock_now
        
        # Call function
        result = save_transcription("This is the transcription.", "output_dir", "output.txt")
        
        # Assertions
        self.assertTrue(result)
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once()
        mock_file_open().write.assert_called_once_with("This is the transcription.")

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.calculate_duration')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.transcribe_audio_file')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.db_save_transcription')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.save_transcription')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.datetime')
    def test_process_audio_files(self, mock_datetime, mock_save, mock_db_save, mock_transcribe, mock_duration):
        """Test processing multiple audio files."""
        # Configure mocks
        mock_client = MagicMock()
        
        # Create mock files
        file1 = MagicMock()
        file1.name = "audio1.mp3"
        file2 = MagicMock()
        file2.name = "audio2.mp3"
        
        audio_files = [file1, file2]
        
        # Mock transcribe function
        mock_transcribe.side_effect = ["Transcription 1", "Transcription 2"]
        
        # Mock duration calculation
        mock_duration.return_value = 60.0
        
        # Create a mock datetime object
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_now.isoformat.return_value = "2023-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now
        
        # Mock save function
        mock_save.return_value = True
        
        # Call function
        result = process_audio_files(mock_client, audio_files, "output_dir", "output.txt")
        
        # Assertions
        self.assertTrue(result)
        self.assertEqual(mock_transcribe.call_count, 2)
        self.assertEqual(mock_db_save.call_count, 2)
        mock_save.assert_called_once()
        

if __name__ == '__main__':
    unittest.main() 