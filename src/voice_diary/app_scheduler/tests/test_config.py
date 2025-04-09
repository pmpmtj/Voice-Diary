"""Unit tests for configuration-related functions in app_scheduler module."""
import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import sys
from pathlib import Path

# Import the module under test
from voice_diary.app_scheduler.app_scheduler import load_config, validate_config, CONFIG_FILE

class TestConfigFunctions(unittest.TestCase):
    """Tests for the configuration handling functions."""
    
    @patch('voice_diary.app_scheduler.app_scheduler.CONFIG_FILE')
    @patch('builtins.open', new_callable=mock_open, 
           read_data='{"scheduler": {"runs_per_day": 4, "daily_task_hour": 16, "daily_task_minute": 30}}')
    def test_load_config_success(self, mock_file, mock_config_file):
        """Test successful config loading."""
        # Set up the mock to show that file exists
        mock_config_file.exists.return_value = True
        
        # Call the function
        config = load_config()
        
        # Assert the config was loaded correctly
        self.assertIn('scheduler', config)
        self.assertEqual(config['scheduler']['runs_per_day'], 4)
        self.assertEqual(config['scheduler']['daily_task_hour'], 16)
        self.assertEqual(config['scheduler']['daily_task_minute'], 30)
        
        # Verify open was called with the correct parameters
        mock_file.assert_called_once_with(mock_config_file, 'r', encoding='utf-8')
    
    @patch('voice_diary.app_scheduler.app_scheduler.CONFIG_FILE')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_load_config_file_not_found(self, mock_exit, mock_print, mock_config_file):
        """Test handling when config file is not found."""
        # Set up the mock to show that file does not exist
        mock_config_file.exists.return_value = False
        
        # Call the function
        try:
            load_config()
        except SystemExit:
            pass  # Expected to exit, catch the exception
        
        # Assert that print and exit were called at least once
        self.assertTrue(mock_print.called)
        mock_exit.assert_called_with(1)
    
    @patch('voice_diary.app_scheduler.app_scheduler.CONFIG_FILE')
    @patch('builtins.open', new_callable=mock_open, read_data='{"no_scheduler_section": {}}')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_load_config_missing_section(self, mock_print, mock_exit, mock_file, mock_config_file):
        """Test handling when scheduler section is missing in config."""
        # Set up the mock to show that file exists
        mock_config_file.exists.return_value = True
        
        # Call the function
        try:
            load_config()
        except SystemExit:
            pass  # Expected to exit, catch the exception
        
        # Function should call sys.exit due to missing 'scheduler' section
        mock_exit.assert_called_with(1)
        self.assertTrue(mock_print.called)
    
    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = {'scheduler': {'runs_per_day': 4}}
        # Should not raise any exception
        validate_config(config)
    
    def test_validate_config_missing_runs_per_day(self):
        """Test config validation with missing runs_per_day."""
        config = {'scheduler': {}}
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("Missing 'runs_per_day'", str(context.exception))
    
    def test_validate_config_invalid_runs_per_day_type(self):
        """Test config validation with invalid runs_per_day type."""
        config = {'scheduler': {'runs_per_day': 'not_a_number'}}
        with self.assertRaises(ValueError) as context:
            validate_config(config)
        self.assertIn("runs_per_day must be a number", str(context.exception))

if __name__ == '__main__':
    unittest.main() 