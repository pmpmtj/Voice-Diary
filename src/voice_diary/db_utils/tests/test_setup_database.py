"""Unit tests for setup_database module."""
import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import io
import logging

class TestSetupDatabase(unittest.TestCase):
    """Tests for the setup_database module functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Save original stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create string IO objects to capture output
        self.stdout_capture = io.StringIO()
        self.stderr_capture = io.StringIO()
        
        # Redirect stdout and stderr
        sys.stdout = self.stdout_capture
        sys.stderr = self.stderr_capture
        
        # Reset the module cache to ensure clean imports
        if 'voice_diary.db_utils.setup_database' in sys.modules:
            del sys.modules['voice_diary.db_utils.setup_database']

    def tearDown(self):
        """Restore original stdout and stderr."""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    @patch('voice_diary.db_utils.db_manager.initialize_db')
    @patch('os.environ.get')
    @patch('sys.exit')
    def test_main_successful_setup(self, mock_exit, mock_environ_get, mock_initialize_db):
        """Test successful database setup."""
        # Setup mocks
        mock_environ_get.return_value = 'postgresql://user:pass@localhost/testdb'
        mock_initialize_db.return_value = True
        
        # Mock the logger directly
        mock_logger = MagicMock()
        
        # Import and run the function
        with patch.dict('sys.modules', {'voice_diary.db_utils.db_config': MagicMock()}):
            with patch('logging.getLogger', return_value=mock_logger):
                from voice_diary.db_utils.setup_database import main
                main()
        
        # Verify function calls
        mock_environ_get.assert_any_call('DATABASE_URL')
        mock_initialize_db.assert_called()
        mock_exit.assert_not_called()  # Should not exit on success
        
        # Check for success messages in logging
        mock_logger.info.assert_any_call("Database setup completed successfully!")
    
    @patch('voice_diary.db_utils.db_manager.initialize_db')
    @patch('os.environ.get')
    @patch('sys.exit')
    def test_main_failed_setup(self, mock_exit, mock_environ_get, mock_initialize_db):
        """Test failed database setup."""
        # Setup mocks
        mock_environ_get.return_value = 'postgresql://user:pass@localhost/testdb'
        mock_initialize_db.return_value = False
        
        # Mock the logger directly
        mock_logger = MagicMock()
        
        # Import and run the function
        with patch.dict('sys.modules', {'voice_diary.db_utils.db_config': MagicMock()}):
            with patch('logging.getLogger', return_value=mock_logger):
                from voice_diary.db_utils.setup_database import main
                main()
        
        # Verify function calls
        mock_environ_get.assert_any_call('DATABASE_URL')
        mock_initialize_db.assert_called()
        mock_exit.assert_called_with(1)  # Should exit with error code 1
        
        # Check for error message in logging
        mock_logger.error.assert_called_with("Database setup failed.")
    
    @patch('voice_diary.db_utils.db_manager.initialize_db')
    @patch('os.environ.get')
    @patch('builtins.input')
    @patch('sys.exit')
    def test_main_no_database_url_continue(self, mock_exit, mock_input, 
                                          mock_environ_get, mock_initialize_db):
        """Test setup when DATABASE_URL is missing but user continues."""
        # Setup mocks to return None only for DATABASE_URL but not other calls
        def side_effect(key):
            if key == 'DATABASE_URL':
                return None
            return 'default'
            
        mock_environ_get.side_effect = side_effect
        mock_input.return_value = 'y'  # User chooses to continue
        mock_initialize_db.return_value = True
        
        # Mock the logger directly
        mock_logger = MagicMock()
        
        # Import and run the function
        with patch.dict('sys.modules', {'voice_diary.db_utils.db_config': MagicMock()}):
            with patch('logging.getLogger', return_value=mock_logger):
                from voice_diary.db_utils.setup_database import main
                main()
        
        # Verify function calls
        mock_environ_get.assert_any_call('DATABASE_URL')
        mock_input.assert_called_once_with("Do you want to continue anyway? (y/n): ")
        mock_initialize_db.assert_called()
        mock_exit.assert_not_called()
        
        # Check for warning and success messages
        mock_logger.warning.assert_any_call("DATABASE_URL environment variable not found.")
        mock_logger.info.assert_any_call("Database setup completed successfully!")
    
    @patch('os.environ.get')
    @patch('builtins.input')
    @patch('sys.exit')
    def test_main_no_database_url_abort(self, mock_exit, mock_input, mock_environ_get):
        """Test setup when DATABASE_URL is missing and user aborts."""
        # Setup mocks to return None only for DATABASE_URL but not other calls
        def side_effect(key):
            if key == 'DATABASE_URL':
                return None
            return 'default'
            
        mock_environ_get.side_effect = side_effect
        mock_input.return_value = 'n'  # User chooses to abort
        
        # Force sys.exit to raise an exception instead of exiting
        mock_exit.side_effect = SystemExit(1)
        
        # Mock the logger directly
        mock_logger = MagicMock()
        
        # Import and run the function
        with patch.dict('sys.modules', {'voice_diary.db_utils.db_config': MagicMock()}):
            with patch('logging.getLogger', return_value=mock_logger):
                from voice_diary.db_utils.setup_database import main
                with self.assertRaises(SystemExit):
                    main()
        
        # Verify function calls
        mock_environ_get.assert_any_call('DATABASE_URL')
        mock_input.assert_called_once_with("Do you want to continue anyway? (y/n): ")
        mock_exit.assert_called_with(1)  # Should exit with error code 1
        
        # Check for warning message
        mock_logger.warning.assert_any_call("DATABASE_URL environment variable not found.")

if __name__ == '__main__':
    unittest.main() 