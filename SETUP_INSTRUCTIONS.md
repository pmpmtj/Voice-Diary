# On-the-Fly Reception Setup Instructions

This document provides step-by-step instructions to set up and run the On-the-Fly Reception feature for the Voice Diary project.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database (configured in .env file)
- OpenAI API key set as an environment variable (`OPENAI_API_KEY`)
- Gmail API credentials (for email functionality)

## Required Python Packages

Install the required packages:

```bash
pip install python-dotenv psycopg2-binary requests google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Note: This script uses direct API calls to OpenAI instead of the OpenAI Python client library, which avoids compatibility issues with different versions of the OpenAI library.

## Setup Steps

### 1. Environment Configuration

Ensure your `.env` file in the project root contains the PostgreSQL database connection string:

```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

### 2. Gmail API Setup (Optional - Only needed if you want to send emails)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to 'APIs & Services' > 'Library'
   - Search for 'Gmail API' and enable it
4. Create OAuth credentials:
   - Go to 'APIs & Services' > 'Credentials'
   - Click 'Create Credentials' > 'OAuth client ID'
   - Select 'Desktop app' as application type
   - Download the JSON file and rename it to `credentials_gmail.json`
   - Place it in the project root directory (same level as scheduler.py)

### 3. Check On-the-Fly Configuration

Ensure the `on_the_fly_config.json` file in the `on_the_fly` directory contains the following:

```json
{
  "prompt": "You are an assistant that summarizes journal entries. Please review the following transcription entries and create a concise, organized summary that captures the key points, important events, and notable thoughts. Format the summary in a clear, readable way.\n\nHere are the entries:\n\n{entries}",
  "send_email": true,
  "recipient": "pmpmtj@gmail.com",
  "subject": "This is a summary of the entries for the requested date",
  "lookup_date_range": ["250330"],
  "output_directory": "on_the_fly_report",
  "output_file_name": "250330-report"
}
```

You can modify the settings as needed:
- Change `send_email` to `false` to disable email sending
- Adjust `lookup_date_range` to query different dates (single date or range: `["250330", "250331"]`)
- Customize the `prompt` to change how the summary is generated

### 4. Set OpenAI API Key

Set your OpenAI API key as an environment variable:

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

**Windows Command Prompt:**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Linux/macOS:**
```bash
export OPENAI_API_KEY=your-api-key-here
```

For persistence, you can also add the OpenAI API key to your `.env` file:

```
OPENAI_API_KEY=your-api-key-here
```

### 5. Run the Script

Execute the on-the-fly reception script:

```bash
python on_the_fly/on_the_fly_reception.py
```

## Output

The script will:

1. Query entries from the database based on the date range in config
2. Process them with OpenAI's LLM
3. Save the output to a text file in the specified directory
4. Optionally send an email with the report (if credentials are set up)

## Troubleshooting

### Database Connection Issues

If you see a database connection error:
- Check that the PostgreSQL server is running
- Verify that the connection string in the `.env` file is correct
- Make sure the database and table exist (the table should be named `optimize_transcriptions`)

The script requires an `optimize_transcriptions` table with the following structure:
```sql
CREATE TABLE IF NOT EXISTS optimize_transcriptions (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

The script will:
1. Extract the date and time from the `created_at` column
2. Look for entries with a date that matches the date range in your config file
3. If date/time data exists in the `metadata` field, it will use that instead

Date format in your config file should be in the format YYMMDD (e.g., "250330" for March 30, 2025).

If your entries have no results, check that:
1. There are entries in the database with matching dates in the `created_at` column
2. The `optimize_transcriptions` table has the correct structure

### Gmail Authentication Issues

If you see "Gmail credentials file not found" warning:
- Make sure `credentials_gmail.json` is in the project root directory
- For testing, you can set `send_email` to `false` in the config to bypass email sending

### OpenAI API Key Issues

If you see "OpenAI API key not found" error:
- Make sure you've set the `OPENAI_API_KEY` environment variable or added it to your `.env` file
- Check that the key is valid and has sufficient quota

## Additional Information

- The script uses the same database and model as the main scheduler pipeline
- It operates independently of the scheduler and can be run at any time
- All operations are logged to `on_the_fly/logs/on_the_fly.log` 