"""Shared fixtures for database utility tests."""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
import importlib

@pytest.fixture(scope="function")
def mock_db_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    
    # Setup cursor.fetchone and fetchall with sensible defaults
    cursor.fetchone.return_value = (1,)
    cursor.fetchall.return_value = []
    
    return conn, cursor

@pytest.fixture(scope="function")
def mock_connection_pool():
    """Create a mock connection pool."""
    mock_pool = MagicMock()
    
    # Setup patching
    with patch('voice_diary.db_utils.db_manager.connection_pool', mock_pool):
        yield mock_pool

@pytest.fixture(scope="function")
def mock_db_config():
    """Mock the database configuration."""
    mock_config = {
        'database': {
            'default_url': 'postgresql://test:test@localhost/testdb'
        },
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'log_file': 'test_db_utils.log',
            'max_size_bytes': 1048576,
            'backup_count': 3
        }
    }
    
    # Reset module cache to ensure fresh imports
    if 'voice_diary.db_utils.db_config' in sys.modules:
        del sys.modules['voice_diary.db_utils.db_config']
    
    # Patch the CONFIG variable
    with patch('voice_diary.db_utils.db_config.CONFIG', mock_config):
        yield mock_config

@pytest.fixture(scope="function")
def environment_variables():
    """Setup and teardown environment variables."""
    # Store original values
    original_values = {}
    test_vars = {
        'DATABASE_URL': 'postgresql://test:test@localhost/testdb',
    }
    
    # Set test values
    for var, value in test_vars.items():
        if var in os.environ:
            original_values[var] = os.environ[var]
        os.environ[var] = value
    
    # Provide fixture
    yield test_vars
    
    # Restore original values
    for var in test_vars:
        if var in original_values:
            os.environ[var] = original_values[var]
        else:
            del os.environ[var] 