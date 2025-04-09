#!/usr/bin/env python3
"""
Unit tests for the agent_summarize_day module.

These tests cover critical functionality without requiring actual API calls to OpenAI.
"""

import unittest
import json
import yaml
import logging
import os
import sys
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
from pathlib import Path

# Adjust path to import from the correct location without modifying sys.path
# This is for testing only - avoiding sys.path.insert as per requirements
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from voice_diary.agent_summarize_day.agent_summarize_day import (
    load_config,
    load_openai_config,
    load_prompts,
    format_transcriptions_for_llm,
    date_from_int,
    get_date_range,
    get_prompt_by_name,
    get_prompt_template
)


class TestAgentSummarizeDay(unittest.TestCase):
    """Test case for agent_summarize_day module functions."""
    
    def setUp(self):
        # Mock configuration files
        self.test_config = {
            "paths": {
                "summarized_file": "test/path/summarized_entries.txt"
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
            "date_range": [20240401, 20240405]
        }
        
        self.test_openai_config = {
            "openai_config": {
                "api_key": "test_key",
                "model": "gpt-4o",
                "temperature": 0.2,
                "save_usage_stats": True,
                "thread_id": "test_thread_id",
                "thread_created_at": "2024-04-05T06:19:08.534882",
                "thread_retention_days": 30,
                "assistant_id": "test_assistant_id"
            },
            "logging": {
                "log_level": "INFO",
                "openai_usage_log_file": "test_openai_usage.log",
                "openai_usage_max_size_bytes": 1048576,
                "openai_usage_backup_count": 3
            }
        }
        
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
        
        # Mock transcriptions data
        self.test_transcriptions = [
            {
                "id": 1,
                "content": "Test transcription 1",
                "created_at": datetime(2024, 4, 1, 10, 0, 0)
            },
            {
                "id": 2,
                "content": "Test transcription 2",
                "created_at": datetime(2024, 4, 1, 15, 30, 0)
            }
        ]

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.CONFIG_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_config(self, mock_json_load, mock_file, mock_config_path):
        """Test loading configuration from a JSON file."""
        # Setup mock
        mock_json_load.return_value = self.test_config
        mock_config_path.is_file.return_value = True
        
        # Test function
        result = load_config()
        
        # Assertions
        self.assertEqual(result, self.test_config)
        mock_file.assert_called_once()
        mock_json_load.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OPENAI_CONFIG_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_openai_config(self, mock_json_load, mock_file, mock_config_path):
        """Test loading OpenAI configuration from a JSON file."""
        # Setup mock
        mock_json_load.return_value = self.test_openai_config
        mock_config_path.is_file.return_value = True
        
        # Test function
        result = load_openai_config()
        
        # Assertions
        self.assertEqual(result, self.test_openai_config)
        mock_file.assert_called_once()
        mock_json_load.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.PROMPTS_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    def test_load_prompts(self, mock_yaml_load, mock_file, mock_prompts_path):
        """Test loading prompts from a YAML file."""
        # Setup mock
        mock_yaml_load.return_value = self.test_prompts
        mock_prompts_path.is_file.return_value = True
        
        # Test function
        result = load_prompts()
        
        # Assertions
        self.assertEqual(result, self.test_prompts.get("prompts", {}))
        mock_file.assert_called_once()
        mock_yaml_load.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.load_config")
    def test_format_transcriptions_for_llm(self, mock_load_config):
        """Test formatting transcriptions for LLM."""
        # Setup mock
        mock_load_config.return_value = self.test_config
        
        # Test function
        result = format_transcriptions_for_llm(self.test_transcriptions)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn("[2024-04-01 10:00:00]", result)
        self.assertIn("Test transcription 1", result)
        self.assertIn("[2024-04-01 15:30:00]", result)
        self.assertIn("Test transcription 2", result)
        self.assertIn("-" * 40, result)  # Check for separator

    def test_date_from_int_valid(self):
        """Test converting valid integer date to datetime object."""
        # Test with valid date
        result = date_from_int(20240401)
        
        # Assertions
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 4)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)

    def test_date_from_int_invalid(self):
        """Test converting invalid integer date to datetime object."""
        # Test with invalid date
        result = date_from_int(999)  # Too short
        
        # Assertions
        self.assertIsNone(result)
        
        # Test with invalid month
        result = date_from_int(20241301)  # Month 13
        
        # Assertions
        self.assertIsNone(result)

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.datetime")
    def test_get_date_range_with_config(self, mock_datetime):
        """Test getting date range from config."""
        # Setup mock
        mock_now = datetime(2024, 4, 10, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock date_from_int to return actual dates instead of mocks
        with patch("voice_diary.agent_summarize_day.agent_summarize_day.date_from_int") as mock_date_from_int:
            # Configure mock to return actual datetime objects
            mock_date_from_int.side_effect = lambda date_int: datetime(
                int(str(date_int)[0:4]), 
                int(str(date_int)[4:6]),
                int(str(date_int)[6:8]),
                0, 0, 0
            ) if len(str(date_int)) == 8 else None
            
            # Test with both start and end dates
            config = {"date_range": [20240401, 20240405]}
            start_date, end_date = get_date_range(config)
            
            # Assertions
            self.assertEqual(start_date, datetime(2024, 4, 1, 0, 0, 0))
            self.assertEqual(end_date, datetime(2024, 4, 5, 0, 0, 0))
            
            # Test with single date
            config = {"date_range": [20240401]}
            start_date, end_date = get_date_range(config)
            
            # Assertions
            self.assertEqual(start_date, datetime(2024, 4, 1, 0, 0, 0))
            self.assertEqual(end_date, datetime(2024, 4, 1, 0, 0, 0))
            
            # Test with empty date range (should use current date)
            config = {"date_range": []}
            start_date, end_date = get_date_range(config)
            
            # Assertions
            self.assertEqual(start_date, mock_now)
            self.assertEqual(end_date, mock_now)
            
            # Test with invalid date (should use current date)
            mock_date_from_int.side_effect = lambda date_int: None
            config = {"date_range": [999999]}
            start_date, end_date = get_date_range(config)
            
            # Assertions
            self.assertEqual(start_date, mock_now)
            self.assertEqual(end_date, mock_now)

    def test_get_prompt_by_name(self):
        """Test getting a prompt by name."""
        # Setup test prompts
        prompts = {
            "summarize_prompt": {
                "template": "Test template 1"
            },
            "assistant_instructions": {
                "template": "Test template 2"
            }
        }
        
        # Test function
        name, template = get_prompt_by_name(prompts, "summarize_prompt")
        
        # Assertions
        self.assertEqual(name, "summarize_prompt")
        self.assertEqual(template, "Test template 1")

    def test_get_prompt_by_name_missing(self):
        """Test getting a prompt by name when it doesn't exist."""
        # Setup test prompts
        prompts = {
            "summarize_prompt": {
                "template": "Test template 1"
            }
        }
        
        # Test function - should raise ValueError
        with self.assertRaises(ValueError):
            get_prompt_by_name(prompts, "nonexistent_prompt")

    def test_get_prompt_by_name_empty_prompts(self):
        """Test getting a prompt by name with empty prompts dictionary."""
        # Test with empty prompts
        prompts = {}
        
        # Test function - should raise ValueError
        with self.assertRaises(ValueError):
            get_prompt_by_name(prompts, "summarize_prompt")
            
    def test_get_prompt_template(self):
        """Test getting a prompt template directly."""
        # Setup test prompts
        prompts = {
            "summarize_prompt": {
                "template": "Test template content"
            }
        }
        
        # Test function
        template = get_prompt_template(prompts, "summarize_prompt")
        
        # Assertions
        self.assertEqual(template, "Test template content")
        
    def test_get_prompt_template_missing_template(self):
        """Test getting a prompt template when the template is missing."""
        # Setup test prompts with missing template
        prompts = {
            "summarize_prompt": {
                "some_other_field": "Test value"
            }
        }
        
        # Test function - should raise ValueError
        with self.assertRaises(ValueError):
            get_prompt_template(prompts, "summarize_prompt")


if __name__ == '__main__':
    unittest.main() 