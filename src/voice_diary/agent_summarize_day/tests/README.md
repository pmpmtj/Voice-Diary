# Voice Diary - Agent Summarize Day Tests

This directory contains unit and integration tests for the `agent_summarize_day` module.

## Test Files

- **test_agent_summarize_day.py**: Unit tests for critical functions in agent_summarize_day.py
- **test_openai_integration.py**: Tests for OpenAI Assistant API integration functionality
- **test_summarize_day_integration.py**: Integration tests for the complete workflow
- **run_tests.py**: Python script to discover and run all tests
- **run_tests.bat**: Windows batch file to run tests

## Running Tests

### On Windows

1. Navigate to this directory
2. Double-click `run_tests.bat` or run it from the command line

### On any platform

```bash
# Navigate to the tests directory
cd src/voice_diary/agent_summarize_day/tests

# Run with Python
python run_tests.py
```

## Test Coverage

These tests cover:

1. **Configuration Loading**: Tests for loading and parsing config files correctly
2. **Date Handling**: Tests for date conversion and date range calculations
3. **OpenAI Integration**: Tests for the OpenAI Assistant API interactions (mocked)
4. **Transcription Processing**: Tests for correctly formatting transcriptions
5. **Error Handling**: Tests for handling various error conditions
6. **End-to-End Flow**: Integration tests for the complete summarization workflow

## Adding New Tests

To add new tests:

1. Create a new file named `test_*.py` in this directory
2. Write test classes that inherit from `unittest.TestCase`
3. The test runner will automatically discover and run your new tests

## Mocking Strategy

These tests use Python's `unittest.mock` to avoid making actual API calls or database queries during testing. Key aspects that are mocked:

- Database queries through `get_transcriptions_by_date_range`
- File I/O operations
- OpenAI API client interactions
- Configuration file loading

This ensures tests can run quickly and reliably without dependencies on external services. 