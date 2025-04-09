#!/usr/bin/env python3
"""
Test error handling in agent_summarize_day module.

These tests specifically focus on testing error handling scenarios.
"""

import unittest
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Adjust path to import from the correct location without modifying sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from voice_diary.agent_summarize_day.agent_summarize_day import (
    load_config,
    load_openai_config,
    load_prompts,
    setup_logging,
    process_with_openai_assistant
)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in voice_diary agent_summarize_day module."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample transcriptions
        self.test_transcriptions = [
            {
                "id": 1,
                "content": "Test content",
                "created_at": MagicMock()
            }
        ]

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.CONFIG_PATH")
    @patch("builtins.open")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_load_config_file_not_found(self, mock_logger, mock_open, mock_config_path):
        """Test handling of missing config file."""
        # Setup the mock
        mock_open.side_effect = FileNotFoundError("Config file not found")
        mock_config_path.is_file.return_value = True

        # Test the function
        with self.assertRaises(SystemExit):
            load_config()
        
        # Verify the log message
        mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.CONFIG_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_load_config_json_error(self, mock_logger, mock_json_load, mock_file, mock_config_path):
        """Test handling of malformed JSON in config file."""
        # Setup the mock
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_config_path.is_file.return_value = True

        # Test the function
        with self.assertRaises(SystemExit):
            load_config()
        
        # Verify the log message
        mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OPENAI_CONFIG_PATH")
    @patch("builtins.open")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_load_openai_config_file_not_found(self, mock_logger, mock_open, mock_config_path):
        """Test handling of missing OpenAI config file."""
        # Setup the mock
        mock_open.side_effect = FileNotFoundError("OpenAI config file not found")
        mock_config_path.is_file.return_value = True

        # Test the function
        with self.assertRaises(SystemExit):
            load_openai_config()
        
        # Verify the log message
        mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.PROMPTS_PATH")
    @patch("builtins.open")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_load_prompts_file_not_found(self, mock_logger, mock_open, mock_prompts_path):
        """Test handling of missing prompts file."""
        # Setup the mock
        mock_open.side_effect = FileNotFoundError("Prompts file not found")
        mock_prompts_path.is_file.return_value = True

        # Test the function
        with self.assertRaises(SystemExit):
            load_prompts()
        
        # Verify the log message
        mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.PROMPTS_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_load_prompts_yaml_error(self, mock_logger, mock_yaml_load, mock_file, mock_prompts_path):
        """Test handling of malformed YAML in prompts file."""
        # Setup the mock
        mock_yaml_load.side_effect = Exception("Invalid YAML")
        mock_prompts_path.is_file.return_value = True

        # Test the function
        with self.assertRaises(SystemExit):
            load_prompts()
        
        # Verify the log message
        mock_logger.error.assert_called()

    # @patch("voice_diary.agent_summarize_day.agent_summarize_day.LOG_DIR")
    # @patch("voice_diary.agent_summarize_day.agent_summarize_day.logging")
    # @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    # @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_openai_config")
    # def test_setup_logging_error(self, mock_load_openai_config, mock_logger, mock_logging, mock_log_dir):
    #     """Test handling of logging setup errors."""
    #     # Setup the mock
    #     handler_mock = MagicMock()
    #     handler_mock.side_effect = PermissionError("Permission denied")
    #     mock_logging.handlers.RotatingFileHandler = handler_mock
    #     
    #     # Mock openai config
    #     mock_load_openai_config.return_value = {
    #         "logging": {
    #             "log_level": "INFO",
    #             "openai_usage_log_file": "openai_usage.log"
    #         }
    #     }
    #     
    #     # Mock logger to avoid actual errors
    #     mock_logger.handlers = []
    #     mock_logger.addHandler.return_value = None
    #     
    #     # Test the function
    #     try:
    #         # The function should not raise an exception even if file handlers fail
    #         setup_logging({"logging": {"log_level": "INFO"}})
    #         # If we get here, the function handled the error
    #         self.assertTrue(True)
    #     except Exception:
    #         self.fail("setup_logging raised an exception when it should have handled the error")
    #     
    #     # Verify the log message
    #     mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.format_transcriptions_for_llm")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OpenAI")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_process_with_openai_assistant_api_error(self, mock_logger, mock_openai, mock_format_llm):
        """Test handling of OpenAI API errors."""
        # Setup mocks
        mock_format_llm.return_value = "Formatted content"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.beta.assistants.create.side_effect = Exception("API Error")
        
        # Test the function
        config = {
            "openai_config": {
                "api_key": "test_key",
                "model": "gpt-4"
            }
        }
        
        result = process_with_openai_assistant(
            self.test_transcriptions,
            "Test prompt {journal_content}",
            config
        )
        
        # Verify the result and log
        self.assertIsNone(result)
        mock_logger.error.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.format_transcriptions_for_llm")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.logger")
    def test_process_with_openai_assistant_no_api_key(self, mock_logger, mock_format_llm):
        """Test handling of missing OpenAI API key."""
        # Setup mocks
        mock_format_llm.return_value = "Formatted content"
        
        # Test with missing API key
        config = {
            "openai_config": {
                "api_key": "",  # Empty API key
                "model": "gpt-4"
            }
        }
        
        # Mock environment to ensure no API key is available
        with patch.dict(os.environ, {}, clear=True):
            result = process_with_openai_assistant(
                self.test_transcriptions,
                "Test prompt {journal_content}",
                config
            )
        
        # Verify the result and log
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("No OpenAI API key found. Set it in the config file or as an environment variable.")


if __name__ == '__main__':
    unittest.main() 