"""
Mock test data for transcribe_raw_audio tests.

This module contains mock data structures used for testing.
"""

# Mock configuration for testing
MOCK_CONFIG = {
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s",
        "log_file": "transcribe_raw_audio.log",
        "max_size_bytes": 1048576,
        "backup_count": 3
    },
    "transcriptions_dir": "test/path/to/transcriptions",
    "output_file": "transcription_output.txt"
}

# Mock Google Drive configuration for testing
MOCK_GDRIVE_CONFIG = {
    "downloads_path": {
        "downloads_dir": "test/path/to/downloads"
    },
    "audio_file_types": {
        "include": [".m4a", ".mp3", ".wav", ".ogg"]
    }
}

# Mock transcription response from OpenAI
MOCK_TRANSCRIPTION_RESPONSE = "This is a sample transcription result from the mock OpenAI API."

# Mock audio files metadata
MOCK_AUDIO_FILES_METADATA = [
    {
        "filename": "20230101_120000_audio.mp3",
        "creation_time": "2023-01-01T12:00:00",
        "duration": 60.5,
        "size_bytes": 2097152  # 2MB
    },
    {
        "filename": "recording_20230102_150000.wav",
        "creation_time": "2023-01-02T15:00:00",
        "duration": 120.2,
        "size_bytes": 5242880  # 5MB
    },
    {
        "filename": "voice_note.m4a",
        "creation_time": "2023-01-03T09:15:00",
        "duration": 45.0,
        "size_bytes": 1048576  # 1MB
    }
] 