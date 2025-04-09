"""
Integration tests for the transcribe_raw_audio module.

This module contains examples of tests that simulate more realistic interactions,
particularly for API access. These tests still use mocks but in a way that mimics 
the real API behavior more closely.

Note: These tests are meant as examples and are marked to be skipped by default.
To run them, remove the @unittest.skip decorator.
"""

import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json
import tempfile

# Import the module to test
from voice_diary.transcribe_raw_audio.transcribe_raw_audio import (
    transcribe_audio_file,
    process_audio_files
)


class TestOpenAIIntegration(unittest.TestCase):
    """Test case for OpenAI API integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample audio data
        self.sample_audio_data = b'mock audio data'
        
        # Create a sample transcription response
        self.sample_transcription = {
            "text": "This is a sample transcription from the OpenAI API."
        }

    @unittest.skip("Example test that demonstrates how to test OpenAI API integration")
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.calculate_duration')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.time')
    def test_openai_api_integration(self, mock_time, mock_calculate_duration):
        """Test OpenAI API integration with a realistic mock."""
        # Configure mocks
        mock_calculate_duration.return_value = 60.0  # 1 minute audio
        mock_time.time.side_effect = [100.0, 110.0]  # 10 seconds elapsed
        
        # Create a temporary audio file for testing
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(self.sample_audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Create a mock OpenAI client that mimics the real API behavior
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = self.sample_transcription["text"]
            mock_client.audio.transcriptions.create.return_value = mock_response
            
            # Call the function with our mock client
            result = transcribe_audio_file(mock_client, temp_file_path)
            
            # Assertions
            self.assertEqual(result, self.sample_transcription["text"])
            mock_client.audio.transcriptions.create.assert_called_once()
            
            # Verify the API was called with correct parameters
            call_args = mock_client.audio.transcriptions.create.call_args
            self.assertEqual(call_args[1]['model'], 'whisper-1')
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    @unittest.skip("Example test that demonstrates end-to-end processing")
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.calculate_duration')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.datetime')
    @patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.db_save_transcription')
    def test_process_audio_files_integration(self, mock_db_save, mock_datetime, mock_calculate_duration):
        """Test processing multiple audio files in an end-to-end scenario."""
        # Configure mocks
        mock_calculate_duration.return_value = 60.0
        
        # Create mock datetime object
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2023-01-01 12:00:00"
        mock_now.isoformat.return_value = "2023-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now
        
        # Create temporary audio files
        temp_files = []
        try:
            for i in range(2):
                with tempfile.NamedTemporaryFile(suffix=f'_test{i}.mp3', delete=False) as temp_file:
                    temp_file.write(self.sample_audio_data)
                    temp_files.append(Path(temp_file.name))
            
            # Create a temporary output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a mock OpenAI client
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.text = self.sample_transcription["text"]
                mock_client.audio.transcriptions.create.return_value = mock_response
                
                # Create a mock for save_transcription
                with patch('voice_diary.transcribe_raw_audio.transcribe_raw_audio.save_transcription', return_value=True) as mock_save:
                    # Call the function
                    result = process_audio_files(mock_client, temp_files, temp_dir, "output.txt")
                    
                    # Assertions
                    self.assertTrue(result)
                    self.assertEqual(mock_client.audio.transcriptions.create.call_count, 2)
                    self.assertEqual(mock_db_save.call_count, 2)
                    mock_save.assert_called_once()
        
        finally:
            # Clean up the temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main() 