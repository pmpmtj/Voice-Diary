"""
Unit tests for error handling in the transcribe_raw_audio module.

This module contains tests for error handling and edge cases in transcribe_raw_audio.py.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Import the module to test
from voice_diary.transcribe_raw_audio.transcribe_raw_audio import (
    get_downloads_dir_from_gdrive_config,
    save_transcription,
    process_audio_files
)


class TestErrorHandling(unittest.TestCase):
    """Test case for error handling in transcribe_raw_audio module."""

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_get_downloads_dir_config_not_found(self, mock_logger, mock_path):
        """Test get_downloads_dir_from_gdrive_config when config file doesn't exist."""
        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value.resolve.return_value.parent.parent = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        # Call function
        result = get_downloads_dir_from_gdrive_config()
        
        # Assertions
        self.assertIsNone(result)
        mock_logger.warning.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_get_audio_files_dir_not_exists(self, mock_logger, mock_path):
        """Test get_audio_files when directory doesn't exist."""
        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        # Import the function to test inside the test to avoid early import issues
        from voice_diary.transcribe_raw_audio.transcribe_raw_audio import get_audio_files
        
        # Call function
        result = get_audio_files("non_existent_dir")
        
        # Assertions
        self.assertEqual(result, [])
        mock_logger.error.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_save_transcription_empty_text(self, mock_logger):
        """Test save_transcription with empty text."""
        # Call function
        result = save_transcription("", "output_dir", "output.txt")
        
        # Assertions
        self.assertFalse(result)
        mock_logger.warning.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.Path')
    @patch('builtins.open')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_save_transcription_io_error(self, mock_logger, mock_open, mock_path):
        """Test save_transcription when file write fails."""
        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        
        # Make open raise an exception
        mock_open.side_effect = Exception("IO Error")
        
        # Call function
        result = save_transcription("Text to save", "output_dir", "output.txt")
        
        # Assertions
        self.assertFalse(result)
        mock_logger.error.assert_called_once()

    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.logger')
    def test_process_audio_files_empty_list(self, mock_logger):
        """Test process_audio_files with empty file list."""
        # Call function
        result = process_audio_files(MagicMock(), [], "output_dir", "output.txt")
        
        # Assertions
        self.assertFalse(result)
        mock_logger.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main() 