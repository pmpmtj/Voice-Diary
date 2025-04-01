# Voice Diary V3

A comprehensive voice diary system that automates the process of transcribing audio recordings, optimizing transcriptions, and generating summarized journal entries from voice notes.

## Overview

Voice Diary V3 is a pipeline-based system that:

1. Downloads audio files from Google Drive
2. Transcribes audio using OpenAI Whisper
3. Optimizes transcriptions to clean and structure the content
4. Generates summarized journal entries
5. Stores data in a PostgreSQL database

The system runs on a configurable schedule to automatically process new voice recordings.

## System Requirements

- Windows 10/11
- Python 3.9+
- PostgreSQL 12+
- FFmpeg (for audio processing)
- Google Drive API credentials

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Voice-Diary-V3-PG.git
cd Voice-Diary-V3-PG
```

### 2. Set Up a Virtual Environment

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

Follow the instructions in [DATABASE_SETUP.md](DATABASE_SETUP.md) to:
- Install PostgreSQL
- Create the required database
- Set up environment variables

### 5. Google Drive Setup

1. Create a Google Cloud project and enable Drive API
2. Create OAuth credentials and download the credentials JSON file
3. Place the credentials in the `gdrive_downloader/gdrive_credentials/` directory

## Configuration

### Main Configuration

Edit `config.json` to configure:
- `runs_per_day`: Number of times the system runs per day (set to 0 to run once and exit)

### Environment Variables

Create a `.env` file with:
```
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/transcriptions
```

## Directory Structure

- `db_utils/`: Database utilities and management
- `gdrive_downloader/`: Google Drive file downloading functionality
- `transcribe_audio/`: Audio transcription using OpenAI Whisper
- `optimize_transcription/`: Transcription cleaning and processing
- `create_journal_of_the_day/`: Journal entry generation
- `summarized_entries/`: Output directory for final journal entries

## Usage

### Running the System

To start the system with the configured schedule:

```bash
python scheduler.py
```

### System Flow

1. **Download from Google Drive**: 
   - The system connects to Google Drive and downloads new audio files
   - Files are saved to `gdrive_downloader/downloads/`

2. **Transcribe Audio**:
   - Downloaded audio files are transcribed using OpenAI's Whisper
   - Transcriptions are saved to `transcribe_audio/received_transcriptions/`

3. **Optimize Transcription**:
   - Transcriptions are processed to clean and structure the content
   - Optimized transcriptions are saved to `optimize_transcription/processed_transcriptions/`

4. **Process Ongoing Entries**:
   - The system generates summarized journal entries from the processed transcriptions
   - Final entries are saved to `summarized_entries/`

5. **Database Storage**:
   - All data is stored in the PostgreSQL database for long-term retention and querying

## Monitoring

The system generates log files for monitoring:
- `scheduler.log`: Main scheduler activity log
- Various module-specific logs in their respective directories

## Troubleshooting

### Common Issues

1. **Google Drive Authentication Issues**:
   - Check credentials in the `gdrive_downloader/gdrive_credentials/` directory
   - Ensure OAuth scopes are correctly configured

2. **Transcription Failures**:
   - Verify that FFmpeg is installed and available in the system PATH
   - Check audio file formats and permissions

3. **Database Connection Issues**:
   - Verify PostgreSQL service is running
   - Check database credentials in the `.env` file

### Reset Pipeline State

To reset the pipeline state:
```bash
del pipeline_state.json
```

## Development

### Adding New Features

1. Follow the modular design pattern of the existing components
2. Add new functionality in a dedicated module directory
3. Update the main scheduler to include your new components in the pipeline

### Database Schema Modifications

Use the `db_utils/setup_database.py` script to add or modify database tables.

## License

[Your license information here]

## Acknowledgements

- OpenAI Whisper for transcription
- Google Drive API for file management
- PostgreSQL for database storage 