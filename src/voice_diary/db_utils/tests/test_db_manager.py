"""Unit tests for db_manager module."""
import unittest
from unittest.mock import patch, MagicMock, call
import json
import psycopg2
from psycopg2 import pool

class TestDbManager(unittest.TestCase):
    """Tests for the db_manager module functionality."""
    
    @patch('voice_diary.db_utils.db_manager.get_db_url')
    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('voice_diary.db_utils.db_manager.create_tables')
    def test_initialize_db_success(self, mock_create_tables, mock_pool, mock_get_db_url):
        """Test successful database initialization."""
        # Setup mocks
        mock_get_db_url.return_value = 'postgresql://user:pass@localhost/testdb'
        mock_pool.return_value = MagicMock()
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import initialize_db
        result = initialize_db()
        
        # Verify the function executed correctly
        self.assertTrue(result)
        mock_get_db_url.assert_called_once()
        mock_pool.assert_called_once_with(1, 10, 'postgresql://user:pass@localhost/testdb')
        mock_create_tables.assert_called_once()

    @patch('voice_diary.db_utils.db_manager.get_db_url')
    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_initialize_db_failure(self, mock_pool, mock_get_db_url):
        """Test database initialization failure."""
        # Setup mocks to simulate failure
        mock_get_db_url.return_value = 'postgresql://user:pass@localhost/testdb'
        mock_pool.side_effect = Exception("Connection error")
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import initialize_db
        result = initialize_db()
        
        # Verify the function handled the error correctly
        self.assertFalse(result)
        
    @patch('voice_diary.db_utils.db_manager.connection_pool')
    def test_get_connection(self, mock_connection_pool):
        """Test getting a connection from the pool."""
        # Setup mock
        mock_conn = MagicMock()
        mock_connection_pool.getconn.return_value = mock_conn
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import get_connection
        result = get_connection()
        
        # Verify result
        self.assertEqual(result, mock_conn)
        mock_connection_pool.getconn.assert_called_once()

    @patch('voice_diary.db_utils.db_manager.connection_pool')
    def test_return_connection(self, mock_connection_pool):
        """Test returning a connection to the pool."""
        # Setup mock
        mock_conn = MagicMock()
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import return_connection
        return_connection(mock_conn)
        
        # Verify function call
        mock_connection_pool.putconn.assert_called_once_with(mock_conn)

    @patch('voice_diary.db_utils.db_manager.get_connection')
    @patch('voice_diary.db_utils.db_manager.return_connection')
    def test_create_tables(self, mock_return_connection, mock_get_connection):
        """Test table creation functionality."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import create_tables
        create_tables()
        
        # Verify cursor executed the expected SQL statements
        self.assertEqual(mock_cursor.execute.call_count, 8)  # 4 CREATE TABLE + 4 CREATE INDEX statements
        mock_conn.commit.assert_called_once()
        mock_return_connection.assert_called_once_with(mock_conn)

    @patch('voice_diary.db_utils.db_manager.get_connection')
    @patch('voice_diary.db_utils.db_manager.return_connection')
    def test_save_transcription(self, mock_return_connection, mock_get_connection):
        """Test saving a transcription."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [(42,)]  # transcription_id
        
        # Test data
        content = "Test transcription"
        filename = "test.wav"
        audio_path = "/path/to/test.wav"
        metadata = {"key": "value"}
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import save_transcription
        result = save_transcription(
            content=content,
            filename=filename,
            audio_path=audio_path,
            model_type="whisper",
            duration_seconds=30.5,
            metadata=metadata
        )
        
        # Verify results
        self.assertEqual(result, 42)  # Should return the transcription_id
        self.assertEqual(mock_cursor.execute.call_count, 1)  # Just the transcription insert
        mock_conn.commit.assert_called_once()
        mock_return_connection.assert_called_once_with(mock_conn)

    @patch('voice_diary.db_utils.db_manager.get_connection')
    @patch('voice_diary.db_utils.db_manager.return_connection')
    def test_get_latest_transcriptions(self, mock_return_connection, mock_get_connection):
        """Test retrieving latest transcriptions."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetched data
        mock_transcriptions = [
            {"id": 1, "content": "Test 1", "created_at": "2023-01-01"},
            {"id": 2, "content": "Test 2", "created_at": "2023-01-02"}
        ]
        mock_cursor.fetchall.return_value = mock_transcriptions
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import get_latest_transcriptions
        result = get_latest_transcriptions(limit=2)
        
        # Verify results
        self.assertEqual(result, mock_transcriptions)
        mock_cursor.execute.assert_called_once()
        mock_cursor.execute.assert_called_with(unittest.mock.ANY, (2,))
        mock_return_connection.assert_called_once_with(mock_conn)

    @patch('voice_diary.db_utils.db_manager.connection_pool')
    def test_close_all_connections(self, mock_connection_pool):
        """Test closing all database connections."""
        # Import and call the function
        from voice_diary.db_utils.db_manager import close_all_connections
        close_all_connections()
        
        # Verify all connections were closed
        mock_connection_pool.closeall.assert_called_once()

    @patch('voice_diary.db_utils.db_manager.get_connection')
    @patch('voice_diary.db_utils.db_manager.return_connection')
    def test_save_optimized_transcription(self, mock_return_connection, mock_get_connection):
        """Test saving an optimized transcription."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (42,)  # Return ID
        
        # Test data
        content = "Optimized transcription"
        original_id = 10
        metadata = {"structured": True, "topics": ["topic1", "topic2"]}
        
        # Import and call the function
        from voice_diary.db_utils.db_manager import save_optimized_transcription
        result = save_optimized_transcription(
            content=content,
            original_transcription_id=original_id,
            metadata=metadata
        )
        
        # Verify results
        self.assertEqual(result, 42)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_return_connection.assert_called_once_with(mock_conn)

if __name__ == '__main__':
    unittest.main() 