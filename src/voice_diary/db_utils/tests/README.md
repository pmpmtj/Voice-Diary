# Database Utilities Tests

This directory contains unit tests for the Voice Diary database utilities.

## Prerequisites

Before running the tests, make sure you have:

1. Set up a virtual environment and installed the required packages
2. Run the setup script to ensure all dependencies are installed

## Running the Tests

### 1. Set Up the Test Environment

First, run the setup script to ensure all test dependencies are installed:

```bash
python -m voice_diary.db_utils.tests.setup_test_env
```

This will:
- Check and install required test packages
- Create test configuration files if needed

If you encounter issues with the tests, you can use the `--fix` option to automatically fix common problems:

```bash
python -m voice_diary.db_utils.tests.setup_test_env --fix
```

### 2. Run the Tests

To run all tests with pytest (recommended):

```bash
python -m voice_diary.db_utils.tests.run_tests
```

Or use unittest directly:

```bash
python -m voice_diary.db_utils.tests.run_tests --unittest
```

### 3. Run Individual Test Files

To run a specific test file:

```bash
# For pytest
pytest src/voice_diary/db_utils/tests/test_db_config.py -v

# For unittest
python -m unittest src.voice_diary.db_utils.tests.test_db_config
```

## Troubleshooting

### Missing Dependencies

If you're missing test dependencies, run:

```bash
pip install pytest pytest-cov psycopg2-binary
```

### Import Errors

If you encounter import errors when running tests, make sure:
- The project root directory is in your PYTHONPATH
- You're running tests from the project root directory

### Logging Assertion Errors

If you see errors related to logging assertions (like `mock_info.assert_any_call` failing), this is usually due to how the logging module is being mocked. The tests use direct patching of the logger instance returned by `logging.getLogger()` instead of patching the logging methods themselves.

### JSON Object Type Errors

If you see errors about "JSON object must be str, bytes or bytearray, not MagicMock", this usually means a mock is being passed to the json parser. Make sure to use `io.StringIO()` objects with proper JSON strings when mocking file operations.

### Database Setup Failures

Tests use mocked database connections, but if you want to run integration tests with a real database:
1. Set the DATABASE_URL environment variable
2. Modify the tests to use real connections instead of mocks

## Test Organization

- **test_db_config.py**: Tests for configuration loading and setup
- **test_db_manager.py**: Tests for database connection and operations
- **test_setup_database.py**: Tests for database initialization
- **conftest.py**: Shared pytest fixtures
- **test_data/**: Directory containing test data files 