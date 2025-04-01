# Voice Diary V3

A comprehensive voice diary system that automates the process of transcribing audio recordings, optimizing transcriptions, and generating summarized journal entries from voice notes.

## Overview

Voice Diary V3 is a pipeline-based system that:

1. Downloads audio files from Google Drive
2. Transcribes audio using OpenAI Whisper
3. Optimizes transcriptions to clean and structure the content
4. Generates summarized journal entries
5. Stores data in a PostgreSQL database
6. Emails journal summaries to specified recipients
7. Allows on-demand generation of reports for specific date ranges

The system runs on a configurable schedule to automatically process new voice recordings.

## System Requirements

- Windows 10/11
- Python 3.9+
- PostgreSQL 12+
- FFmpeg (for audio processing)
- Google Drive API credentials
- Gmail API credentials (for email functionality)

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

### 6. Gmail API Setup (for Email Functionality)

1. In the same Google Cloud project, enable the Gmail API
2. Create OAuth credentials for Desktop application
3. Download the credentials JSON file and rename it to `credentials_gmail.json`
4. Place it in the `send_email/config/` directory
5. Configure your email settings in `send_email/config/email_config.json`

## Configuration

### Main Configuration

Edit `config.json` to configure:
- `runs_per_day`: Number of times the system runs per day (set to 0 to run once and exit)

### Email Configuration

Edit `send_email/config/email_config.json` to configure:
- Email recipients
- Subject lines
- Message templates
- Whether to enable email sending

### On-the-Fly Report Configuration

Edit `on_the_fly/config/on_the_fly_config.json` to configure:
- Date ranges for report generation
- Output directory and file name
- Email settings for reports
- Custom prompts for report generation

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
- `send_email/`: Email sending functionality using Gmail API
- `on_the_fly/`: On-demand report generation for specific date ranges

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

5. **Email Summaries**:
   - Journal summaries are sent via email to configured recipients
   - Uses Gmail API for secure and reliable delivery

6. **Database Storage**:
   - All data is stored in the PostgreSQL database for long-term retention and querying

### On-Demand Report Generation

To generate reports for specific date ranges outside the regular schedule:

```bash
python on_the_fly/on_the_fly_reception.py
```

This will:
1. Query the database for entries in the specified date range
2. Process the entries using a custom prompt template
3. Save the report to the configured output directory
4. Optionally email the report to specified recipients

## Monitoring

The system generates log files for monitoring:
- `scheduler.log`: Main scheduler activity log
- `on_the_fly/logs/on_the_fly.log`: On-demand report generation logs
- Various module-specific logs in their respective directories

## Troubleshooting

### Common Issues

1. **Google Drive Authentication Issues**:
   - Check credentials in the `gdrive_downloader/gdrive_credentials/` directory
   - Ensure OAuth scopes are correctly configured

2. **Gmail Authentication Issues**:
   - Check credentials in the `send_email/config/` directory
   - Verify that required Gmail API scopes are enabled

3. **Transcription Failures**:
   - Verify that FFmpeg is installed and available in the system PATH
   - Check audio file formats and permissions

4. **Database Connection Issues**:
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
- Gmail API for email functionality
- PostgreSQL for database storage 