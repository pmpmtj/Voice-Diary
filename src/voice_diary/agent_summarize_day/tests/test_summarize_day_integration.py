#!/usr/bin/env python3
"""
Integration tests for the summarize_day function.

These tests verify the complete workflow but mock external dependencies.
"""

import unittest
import json
import sys
import os
import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY

# Adjust path to import from the correct location without modifying sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from voice_diary.agent_summarize_day.agent_summarize_day import summarize_day


class TestSummarizeDayIntegration(unittest.TestCase):
    """Integration tests for the summarize_day function."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Sample configuration
        self.test_config = {
            "paths": {
                "summarized_file": "test_output.txt"
            },
            "logging": {
                "log_level": "INFO",
                "summarize_day_log_file": "test_log.log",
                "summarize_day_max_size_bytes": 1048576,
                "summarize_day_backup_count": 3
            },
            "output": {
                "date_format": "%Y-%m-%d"
            },
            "date_range": [20240401, 20240401]  # Single day
        }
        
        # Sample OpenAI config
        self.test_openai_config = {
            "openai_config": {
                "api_key": "test_key",
                "model": "gpt-4o",
                "temperature": 0.2,
                "save_usage_stats": True,
                "thread_id": "test_thread_id",
                "thread_created_at": "2024-04-05T06:19:08.534882",
                "assistant_id": "test_assistant_id",
                "thread_retention_days": 30
            },
            "logging": {
                "log_level": "INFO",
                "openai_usage_log_file": "test_openai_usage.log"
            }
        }
        
        # Sample prompts
        self.test_prompts = {
            "prompts": {
                "summarize_prompt": {
                    "template": "Test summarize prompt {journal_content}"
                },
                "assistant_instructions": {
                    "template": "Test assistant instructions"
                }
            }
        }
        
        # Sample transcriptions
        self.test_transcriptions = [
            {
                "id": 1,
                "content": "Test transcription content 1",
                "created_at": datetime(2024, 4, 1, 10, 0, 0)
            },
            {
                "id": 2,
                "content": "Test transcription content 2",
                "created_at": datetime(2024, 4, 1, 14, 30, 0)
            }
        ]

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.Path.mkdir")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_openai_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_prompts")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.get_transcriptions_by_date_range")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.process_with_openai_assistant")
    @patch("builtins.open", new_callable=mock_open)
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.setup_logging")
    def test_summarize_day_successful(
        self, mock_setup_logging, mock_logger, mock_file, mock_process_openai, mock_get_transcriptions, 
        mock_load_prompts, mock_load_openai_config, mock_load_config, mock_mkdir
    ):
        """Test successful summarization workflow."""
        # Configure mocks
        mock_load_config.return_value = self.test_config
        mock_load_openai_config.return_value = self.test_openai_config
        mock_load_prompts.return_value = self.test_prompts.get("prompts", {})
        mock_get_transcriptions.return_value = self.test_transcriptions
        mock_process_openai.return_value = "Test summarized content"
        
        # Run function
        result = summarize_day()
        
        # Assertions
        self.assertTrue(result)
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(self.test_config)
        mock_load_openai_config.assert_called_once()
        mock_load_prompts.assert_called_once()
        
        # Verify date range handling
        mock_get_transcriptions.assert_called_once()
        # Get the first argument (start_date) of the first call
        start_date = mock_get_transcriptions.call_args[0][0]
        self.assertEqual(start_date.year, 2024)
        self.assertEqual(start_date.month, 4)
        self.assertEqual(start_date.day, 1)
        self.assertEqual(start_date.hour, 0)
        self.assertEqual(start_date.minute, 0)
        self.assertEqual(start_date.second, 0)
        
        # Get the second argument (end_date) of the first call
        end_date = mock_get_transcriptions.call_args[0][1]
        self.assertEqual(end_date.year, 2024)
        self.assertEqual(end_date.month, 4)
        self.assertEqual(end_date.day, 1)
        self.assertEqual(end_date.hour, 23)
        self.assertEqual(end_date.minute, 59)
        self.assertEqual(end_date.second, 59)
        
        # Verify OpenAI processing
        mock_process_openai.assert_called_once()
        self.assertEqual(mock_process_openai.call_args[0][0], self.test_transcriptions)
        
        # Verify file writing
        mock_mkdir.assert_called_once()
        mock_file.assert_called_once_with("test_output.txt", 'w', encoding='utf-8')
        mock_file().write.assert_any_call("=== Diary Summary: 2024-04-01 ===\n\n")
        mock_file().write.assert_any_call("Test summarized content")

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.get_transcriptions_by_date_range")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.setup_logging")
    def test_summarize_day_no_transcriptions(
        self, mock_setup_logging, mock_logger, mock_get_transcriptions, mock_load_config
    ):
        """Test behavior when no transcriptions are found."""
        # Configure mocks
        mock_load_config.return_value = self.test_config
        mock_get_transcriptions.return_value = []  # No transcriptions
        
        # Run function
        result = summarize_day()
        
        # Assertions
        self.assertFalse(result)
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(self.test_config)
        mock_get_transcriptions.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.Path.mkdir")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_openai_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_prompts")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.get_transcriptions_by_date_range")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.process_with_openai_assistant")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.setup_logging")
    def test_summarize_day_openai_failure(
        self, mock_setup_logging, mock_logger, mock_process_openai, mock_get_transcriptions, 
        mock_load_prompts, mock_load_openai_config, mock_load_config, mock_mkdir
    ):
        """Test behavior when OpenAI processing fails."""
        # Configure mocks
        mock_load_config.return_value = self.test_config
        mock_load_openai_config.return_value = self.test_openai_config
        mock_load_prompts.return_value = self.test_prompts.get("prompts", {})
        mock_get_transcriptions.return_value = self.test_transcriptions
        mock_process_openai.return_value = None  # Simulating OpenAI failure
        
        # Run function
        result = summarize_day()
        
        # Assertions
        self.assertFalse(result)
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(self.test_config)
        mock_load_openai_config.assert_called_once()
        mock_load_prompts.assert_called_once()
        mock_get_transcriptions.assert_called_once()
        mock_process_openai.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.Path.mkdir")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_openai_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_prompts")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.get_transcriptions_by_date_range")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.process_with_openai_assistant")
    @patch("builtins.open")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.setup_logging")
    def test_summarize_day_file_error(
        self, mock_setup_logging, mock_logger, mock_open, mock_process_openai, mock_get_transcriptions, 
        mock_load_prompts, mock_load_openai_config, mock_load_config, mock_mkdir
    ):
        """Test behavior when file writing fails."""
        # Configure mocks
        mock_load_config.return_value = self.test_config
        mock_load_openai_config.return_value = self.test_openai_config
        mock_load_prompts.return_value = self.test_prompts.get("prompts", {})
        mock_get_transcriptions.return_value = self.test_transcriptions
        mock_process_openai.return_value = "Test summarized content"
        mock_open.side_effect = IOError("Test file error")  # Simulate file write error
        
        # Run function
        result = summarize_day()
        
        # Assertions
        self.assertFalse(result)
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(self.test_config)
        mock_load_openai_config.assert_called_once()
        mock_load_prompts.assert_called_once()
        mock_get_transcriptions.assert_called_once()
        mock_process_openai.assert_called_once()
        mock_open.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.Path.mkdir")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_openai_config")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_prompts")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.get_transcriptions_by_date_range")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.process_with_openai_assistant")
    @patch("builtins.open", new_callable=mock_open)
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.setup_logging")
    def test_summarize_day_date_range(
        self, mock_setup_logging, mock_logger, mock_file, mock_process_openai, mock_get_transcriptions, 
        mock_load_prompts, mock_load_openai_config, mock_load_config, mock_mkdir
    ):
        """Test with a multi-day date range."""
        # Create config with date range
        config_with_range = self.test_config.copy()
        config_with_range["date_range"] = [20240401, 20240403]  # 3-day range
        
        # Configure mocks
        mock_load_config.return_value = config_with_range
        mock_load_openai_config.return_value = self.test_openai_config
        mock_load_prompts.return_value = self.test_prompts.get("prompts", {})
        mock_get_transcriptions.return_value = self.test_transcriptions
        mock_process_openai.return_value = "Test summarized content for multiple days"
        
        # Run function
        result = summarize_day()
        
        # Assertions
        self.assertTrue(result)
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(config_with_range)
        
        # Verify date range handling
        start_date = mock_get_transcriptions.call_args[0][0]
        self.assertEqual(start_date.day, 1)
        
        end_date = mock_get_transcriptions.call_args[0][1]
        self.assertEqual(end_date.day, 3)
        
        # Verify file writing with date range header
        mock_file().write.assert_any_call("=== Diary Summary: 2024-04-01 to 2024-04-03 ===\n\n")
        mock_file().write.assert_any_call("Test summarized content for multiple days")


if __name__ == '__main__':
    unittest.main() 