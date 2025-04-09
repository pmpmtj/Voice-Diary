#!/usr/bin/env python3
"""
Tests for OpenAI integration in agent_summarize_day module.

These tests focus on the OpenAI Assistant API interactions.
They use mocking to avoid actual API calls during testing.
"""

import unittest
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Adjust path to import from the correct location without modifying sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from voice_diary.agent_summarize_day.agent_summarize_day import process_with_openai_assistant


class TestOpenAIIntegration(unittest.TestCase):
    """Tests for OpenAI integration in agent_summarize_day module."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Sample transcriptions data
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
        
        # Sample prompt template
        self.prompt_template = "Test prompt template with {journal_content}"
        
        # Sample OpenAI config
        self.openai_config = {
            "openai_config": {
                "api_key": "test_key",
                "model": "gpt-4o",
                "temperature": 0.2,
                "save_usage_stats": True,
                "thread_id": None,  # Test creating new thread
                "assistant_id": None,  # Test creating new assistant
                "thread_retention_days": 30
            },
            "logging": {
                "log_level": "INFO",
                "openai_usage_log_file": "test_openai_usage.log"
            }
        }
        
        # Sample with existing thread and assistant
        self.openai_config_existing = {
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

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.format_transcriptions_for_llm")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OpenAI")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OPENAI_CONFIG_PATH")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_process_with_openai_assistant_new_thread_assistant(
        self, mock_json_dump, mock_file, mock_config_path, mock_openai, mock_format_llm
    ):
        """Test processing with new thread and assistant creation."""
        # Setup mocks
        mock_format_llm.return_value = "Formatted journal content"
        
        # Mock OpenAI client and its methods
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock assistant creation
        mock_assistant = MagicMock()
        mock_assistant.id = "new_assistant_id"
        mock_client.beta.assistants.create.return_value = mock_assistant
        
        # Mock thread creation
        mock_thread = MagicMock()
        mock_thread.id = "new_thread_id"
        mock_client.beta.threads.create.return_value = mock_thread
        
        # Mock thread messages
        mock_message = MagicMock()
        mock_client.beta.threads.messages.create.return_value = mock_message
        
        # Mock run creation and status
        mock_run = MagicMock()
        mock_run.id = "test_run_id"
        mock_client.beta.threads.runs.create.return_value = mock_run
        
        # Mock run status
        mock_run_status = MagicMock()
        mock_run_status.status = "completed"
        # Create a usage property that supports attribute access
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_run_status.usage = mock_usage
        mock_client.beta.threads.runs.retrieve.return_value = mock_run_status
        
        # Mock messages list
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_content = MagicMock()
        mock_content.text = MagicMock()
        mock_content.text.value = "Test summarized content"
        mock_message.content = [mock_content]
        mock_messages.data = [mock_message]
        mock_client.beta.threads.messages.list.return_value = mock_messages
        
        # Prevent the actual file writing since MagicMock isn't JSON serializable
        mock_json_dump.side_effect = lambda obj, f, indent: None
        
        # Mock logging to avoid errors
        with patch('voice_diary.agent_summarize_day.agent_summarize_day.logging.getLogger'):
            # Test function
            result = process_with_openai_assistant(
                self.test_transcriptions, 
                self.prompt_template,
                self.openai_config
            )
        
        # Assertions
        self.assertEqual(result, "Test summarized content")
        mock_format_llm.assert_called_once_with(self.test_transcriptions)
        mock_client.beta.assistants.create.assert_called_once()
        mock_client.beta.threads.create.assert_called_once()
        mock_client.beta.threads.messages.create.assert_called_once()
        mock_client.beta.threads.runs.create.assert_called_once()
        mock_client.beta.threads.messages.list.assert_called_once()
        
        # Check that config was updated
        self.assertEqual(self.openai_config["openai_config"]["assistant_id"], "new_assistant_id")
        self.assertEqual(self.openai_config["openai_config"]["thread_id"], "new_thread_id")
        mock_json_dump.assert_called()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.format_transcriptions_for_llm")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OpenAI")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.time.sleep")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.datetime")
    def test_process_with_openai_assistant_existing(
        self, mock_datetime, mock_sleep, mock_openai, mock_format_llm
    ):
        """Test processing with existing thread and assistant."""
        # Setup mocks
        mock_format_llm.return_value = "Formatted journal content"
        
        # Create a mock datetime.now() that returns a fixed date
        mock_now = datetime(2024, 4, 5, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        # Also make sure datetime.fromtimestamp returns a reasonable date
        mock_datetime.fromtimestamp.return_value = datetime(2024, 4, 4, 12, 0, 0)  # 1 day old
        
        # Mock OpenAI client and its methods
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock assistant retrieval
        mock_assistant = MagicMock()
        mock_client.beta.assistants.retrieve.return_value = mock_assistant
        
        # Mock thread retrieval
        mock_thread = MagicMock()
        # Use integer timestamp with 1 day old date
        mock_thread.created_at = int(datetime(2024, 4, 4, 12, 0, 0).timestamp())
        mock_client.beta.threads.retrieve.return_value = mock_thread
        
        # Mock thread messages
        mock_message = MagicMock()
        mock_client.beta.threads.messages.create.return_value = mock_message
        
        # Mock run creation and status
        mock_run = MagicMock()
        mock_run.id = "test_run_id"
        mock_client.beta.threads.runs.create.return_value = mock_run
        
        # Mock run status changes from in_progress to completed
        # Create status objects that each have their own usage property
        status1 = MagicMock()
        status1.status = "in_progress"
        
        status2 = MagicMock()
        status2.status = "in_progress"
        
        status3 = MagicMock()
        status3.status = "completed"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        status3.usage = mock_usage
        
        mock_client.beta.threads.runs.retrieve.side_effect = [status1, status2, status3]
        
        # Mock messages list
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_content = MagicMock()
        mock_content.text = MagicMock()
        mock_content.text.value = "Test summarized content"
        mock_message.content = [mock_content]
        mock_messages.data = [mock_message]
        mock_client.beta.threads.messages.list.return_value = mock_messages
        
        # Mock logging to avoid errors
        with patch('voice_diary.agent_summarize_day.agent_summarize_day.logging.getLogger'):
            # Test function
            result = process_with_openai_assistant(
                self.test_transcriptions, 
                self.prompt_template,
                self.openai_config_existing
            )
        
        # Assertions
        self.assertEqual(result, "Test summarized content")
        mock_format_llm.assert_called_once_with(self.test_transcriptions)
        mock_client.beta.assistants.retrieve.assert_called_once_with("test_assistant_id")
        mock_client.beta.threads.retrieve.assert_called_once_with("test_thread_id")
        mock_client.beta.threads.messages.create.assert_called_once()
        mock_client.beta.threads.runs.create.assert_called_once()
        
        # Sleep should be called at least once for polling
        mock_sleep.assert_called()
        
        # Status retrieve should be called multiple times for polling
        self.assertGreater(mock_client.beta.threads.runs.retrieve.call_count, 1)
        
        mock_client.beta.threads.messages.list.assert_called_once()

    @patch("voice_diary.agent_summarize_day.agent_summarize_day.format_transcriptions_for_llm")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.OpenAI")
    @patch("voice_diary.agent_summarize_day.agent_summarize_day.datetime")
    def test_process_with_openai_assistant_run_failed(self, mock_datetime, mock_openai, mock_format_llm):
        """Test handling of failed OpenAI runs."""
        # Setup mocks
        mock_format_llm.return_value = "Formatted journal content"
        
        # Create a mock datetime.now() that returns a fixed date
        mock_now = datetime(2024, 4, 5, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        # Also make sure datetime.fromtimestamp returns a reasonable date
        mock_datetime.fromtimestamp.return_value = datetime(2024, 4, 4, 12, 0, 0)  # 1 day old
        
        # Mock OpenAI client and its methods
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock assistant retrieval
        mock_assistant = MagicMock()
        mock_client.beta.assistants.retrieve.return_value = mock_assistant
        
        # Mock thread retrieval
        mock_thread = MagicMock()
        mock_thread.created_at = int(datetime(2024, 4, 4, 12, 0, 0).timestamp())
        mock_client.beta.threads.retrieve.return_value = mock_thread
        
        # Mock thread messages
        mock_message = MagicMock()
        mock_client.beta.threads.messages.create.return_value = mock_message
        
        # Mock run creation and status
        mock_run = MagicMock()
        mock_run.id = "test_run_id"
        mock_client.beta.threads.runs.create.return_value = mock_run
        
        # Mock run status as failed
        mock_run_status = MagicMock()
        mock_run_status.status = "failed"
        mock_client.beta.threads.runs.retrieve.return_value = mock_run_status
        
        # Mock logging to avoid errors
        with patch('voice_diary.agent_summarize_day.agent_summarize_day.logging.getLogger'):
            # Test function
            result = process_with_openai_assistant(
                self.test_transcriptions, 
                self.prompt_template,
                self.openai_config_existing
            )
        
        # Assertions
        self.assertIsNone(result)  # Should return None on failure
        mock_format_llm.assert_called_once_with(self.test_transcriptions)
        mock_client.beta.assistants.retrieve.assert_called_once_with("test_assistant_id")
        mock_client.beta.threads.retrieve.assert_called_once_with("test_thread_id")
        mock_client.beta.threads.messages.create.assert_called_once()
        mock_client.beta.threads.runs.create.assert_called_once()
        mock_client.beta.threads.runs.retrieve.assert_called_once()
        
        # Messages list should not be called after run failure
        mock_client.beta.threads.messages.list.assert_not_called()


if __name__ == '__main__':
    unittest.main() 