"""Unit tests for interval calculation functions in app_scheduler module."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the module under test
from voice_diary.app_scheduler.app_scheduler import (
    calculate_interval_seconds,
    calculate_next_run_time,
    calculate_seconds_until_daily_task
)

class TestIntervalCalculations(unittest.TestCase):
    """Tests for the interval calculation functions."""
    
    def test_calculate_interval_seconds(self):
        """Test interval calculation with various inputs."""
        # Zero runs per day should return 0 (run once mode)
        self.assertEqual(calculate_interval_seconds(0), 0)
        
        # 4 runs per day = every 6 hours = 21600 seconds
        self.assertEqual(calculate_interval_seconds(4), 21600)
        
        # 24 runs per day = every hour = 3600 seconds
        self.assertEqual(calculate_interval_seconds(24), 3600)
        
        # 1 run per day = 86400 seconds
        self.assertEqual(calculate_interval_seconds(1), 86400)
    
    @patch('voice_diary.app_scheduler.app_scheduler.datetime')
    def test_calculate_next_run_time(self, mock_datetime):
        """Test next run time calculation."""
        # Set fixed "now" time for testing
        fixed_now = datetime(2023, 7, 15, 12, 0, 0)  # July 15, 2023, 12:00:00
        mock_datetime.now.return_value = fixed_now
        
        # Test with 1 hour interval (3600 seconds)
        next_run = calculate_next_run_time(3600)
        expected_next_run = fixed_now + timedelta(seconds=3600)
        self.assertEqual(next_run, expected_next_run)
        
        # Test with 4 hour interval (14400 seconds)
        next_run = calculate_next_run_time(14400)
        expected_next_run = fixed_now + timedelta(seconds=14400)
        self.assertEqual(next_run, expected_next_run)
    
    @patch('voice_diary.app_scheduler.app_scheduler.datetime')
    @patch('voice_diary.app_scheduler.app_scheduler.load_config')
    def test_calculate_seconds_until_daily_task_before_target(self, mock_load_config, mock_datetime):
        """Test calculation of seconds until daily task when current time is before target time."""
        # Mock config
        mock_config = {
            'scheduler': {
                'daily_task_hour': 17,
                'daily_task_minute': 30
            }
        }
        mock_load_config.return_value = mock_config
        
        # Set fixed "now" time for testing
        fixed_now = datetime(2023, 7, 15, 12, 0, 0)  # July 15, 2023, 12:00:00
        mock_datetime.now.return_value = fixed_now
        
        # Calculate seconds until 17:30 from 12:00
        # 5 hours and 30 minutes = 19800 seconds
        seconds = calculate_seconds_until_daily_task()
        self.assertEqual(seconds, 19800)
    
    @patch('voice_diary.app_scheduler.app_scheduler.datetime')
    @patch('voice_diary.app_scheduler.app_scheduler.load_config')
    def test_calculate_seconds_until_daily_task_after_target(self, mock_load_config, mock_datetime):
        """Test calculation of seconds until daily task when current time is after target time."""
        # Mock config
        mock_config = {
            'scheduler': {
                'daily_task_hour': 8,
                'daily_task_minute': 0
            }
        }
        mock_load_config.return_value = mock_config
        
        # Set fixed "now" time for testing
        fixed_now = datetime(2023, 7, 15, 20, 0, 0)  # July 15, 2023, 20:00:00 (8 PM)
        mock_datetime.now.return_value = fixed_now
        
        # Target time is 8:00 AM, current time is 8:00 PM
        # Should schedule for next day (12 + 8 = 20 hours = 72000 seconds)
        seconds = calculate_seconds_until_daily_task()
        expected_seconds = 12 * 3600  # 12 hours until 8 AM next day
        self.assertEqual(seconds, expected_seconds)
    
    @patch('voice_diary.app_scheduler.app_scheduler.datetime')
    @patch('voice_diary.app_scheduler.app_scheduler.load_config')
    def test_calculate_seconds_until_daily_task_fallback_values(self, mock_load_config, mock_datetime):
        """Test fallback values when config doesn't specify time."""
        # Mock config without time values
        mock_config = {'scheduler': {}}
        mock_load_config.return_value = mock_config
        
        # Set fixed "now" time for testing
        fixed_now = datetime(2023, 7, 15, 12, 0, 0)  # July 15, 2023, 12:00:00
        mock_datetime.now.return_value = fixed_now
        
        # Should use fallback values (23:55)
        seconds = calculate_seconds_until_daily_task()
        # From 12:00 to 23:55 = 11 hours and 55 minutes = 42900 seconds
        expected_seconds = (11 * 3600) + (55 * 60)
        self.assertEqual(seconds, expected_seconds)

if __name__ == '__main__':
    unittest.main() 