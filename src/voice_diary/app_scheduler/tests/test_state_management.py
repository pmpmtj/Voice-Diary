"""Unit tests for state management functions in app_scheduler module."""
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import tempfile
import os
from pathlib import Path

# Import the module under test
from voice_diary.app_scheduler.app_scheduler import update_pipeline_state

class TestStateManagement(unittest.TestCase):
    """Tests for the state management functions."""
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_update_pipeline_state(self, mock_json_dump, mock_file):
        """Test updating the pipeline state file."""
        test_state_file = "test_state.json"
        test_updates = {
            "last_run_time": "2023-07-15T12:00:00.000000",
            "last_run_status": "success"
        }
        
        # Call the function
        update_pipeline_state(test_state_file, test_updates)
        
        # Verify file was opened correctly
        mock_file.assert_called_once_with(test_state_file, 'w')
        
        # Verify json.dump was called with the correct parameters
        file_handle = mock_file()
        mock_json_dump.assert_called_once_with(test_updates, file_handle, indent=2)
    
    @patch('builtins.open')
    @patch('voice_diary.app_scheduler.app_scheduler.logger')
    def test_update_pipeline_state_error(self, mock_logger, mock_open):
        """Test error handling when updating the pipeline state file."""
        mock_open.side_effect = Exception("Test error")
        
        # Call function with parameters
        with self.assertRaises(Exception):
            update_pipeline_state("test_state.json", {"test": "data"})
        
        # Verify error was logged
        mock_logger.error.assert_called()
    
    def test_update_pipeline_state_real_file(self):
        """Test updating state to a real temporary file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # Test data
            test_updates = {
                "last_run_time": "2023-07-15T12:00:00.000000",
                "last_run_status": "success"
            }
            
            # Update the state file
            update_pipeline_state(temp_file_path, test_updates)
            
            # Read the file and verify its contents
            with open(temp_file_path, 'r') as f:
                saved_state = json.load(f)
            
            self.assertEqual(saved_state, test_updates)
            
        finally:
            # Clean up - delete temporary file
            os.unlink(temp_file_path)

if __name__ == '__main__':
    unittest.main() 