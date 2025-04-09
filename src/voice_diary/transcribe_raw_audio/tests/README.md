# Transcribe Raw Audio Test Suite

This directory contains unit tests for the `transcribe_raw_audio` module which is responsible for transcribing audio files using OpenAI's Whisper API.

## Test Files

- `test_transcribe_raw_audio.py`: Tests for the main functionalities of the module
- `test_error_handling.py`: Tests for error handling and edge cases
- `test_integration.py`: Integration tests with more realistic API interactions (skipped by default)
- `test_data.py`: Mock data used in tests
- `run_tests.py`: Script to run all tests

## Running Tests

To run all tests, execute the following command from the project root:

```bash
python -m src.voice_diary.transcribe_raw_audio.tests.run_tests
```

Or run individual test files:

```bash
python -m unittest src.voice_diary.transcribe_raw_audio.tests.test_transcribe_raw_audio
python -m unittest src.voice_diary.transcribe_raw_audio.tests.test_error_handling
```

To run the integration tests (which are skipped by default), you'll need to modify the test file to remove the `@unittest.skip` decorators:

```bash
python -m unittest src.voice_diary.transcribe_raw_audio.tests.test_integration
```

## Test Coverage

The tests cover the following critical functions:

1. Configuration loading and validation
   - `load_config`
   - `get_downloads_dir_from_gdrive_config`
   - `get_audio_extensions_from_gdrive_config`

2. OpenAI client initialization
   - `get_openai_client`

3. Audio file processing
   - `calculate_duration`
   - `get_audio_files`
   - `transcribe_audio_file`
   - `save_transcription`
   - `process_audio_files`

4. Error handling and edge cases
   - Missing audio extensions
   - Empty file lists
   - Empty transcription text
   - IO errors
   - Non-existent directories

## Implementation Notes

The test suite uses Python's built-in `unittest` framework and mocks to isolate the code being tested:

1. **Mocking External Dependencies**: We mock external dependencies like file system operations, API calls, and logger functions.

2. **Test Structure**: Each test follows the Arrange-Act-Assert pattern:
   - **Arrange**: Set up test fixtures and mocks
   - **Act**: Call the function being tested
   - **Assert**: Verify the function behaved as expected

3. **Error Handling**: For error cases, we verify that:
   - The function returns the expected value (`None`, `False`, etc.)
   - The function logs appropriate messages
   - The function doesn't proceed further when it should stop

4. **Integration Tests**: These tests demonstrate more realistic testing scenarios:
   - Creating temporary files for testing
   - Simulating API responses more realistically
   - Testing end-to-end workflows

## Testing Challenges

Some components can be challenging to test due to their nature:

1. **System Exit Functions**: Functions that call `sys.exit()` terminate the running process, making them difficult to test in a normal test flow.

2. **External API Calls**: Functions that call external APIs like OpenAI need proper mocking.

3. **File System Operations**: Functions that interact with the file system need careful mocking to avoid actual file operations during tests.

## Dependencies

The tests use the standard Python `unittest` module and mock objects to avoid actual API calls or file system access during testing. 