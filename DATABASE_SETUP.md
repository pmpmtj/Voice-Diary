# PostgreSQL Database Setup Guide

This guide provides instructions for setting up and initializing the PostgreSQL database for the transcription system.

## Table of Contents
1. [Installation](#installation)
2. [Database Creation](#database-creation)
3. [Environment Setup](#environment-setup)
4. [Database Schema](#database-schema)
5. [Testing Connection](#testing-connection)
6. [Troubleshooting](#troubleshooting)

## Installation

1. Download and install PostgreSQL for Windows:
   - Visit [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
   - Run the installer
   - Note down:
     - PostgreSQL superuser (postgres) password
     - Port number (default: 5432)

## Database Creation

### Using psql
```bash
# Open Command Prompt and connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE transcriptions;
```

### Using pgAdmin
1. Open pgAdmin
2. Right-click on "Databases"
3. Select "Create" → "Database"
4. Name it "transcriptions"

## Environment Setup

1. Set environment variable:
```bash
# Windows Command Prompt
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/transcriptions

# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/transcriptions"
```

2. Create `.env` file in project root:
```plaintext
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/transcriptions
```

## Database Schema

The database includes the following tables:

### Transcriptions Table
```sql
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    filename TEXT,
    audio_path TEXT,
    model_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_seconds FLOAT,
    category_id INTEGER,
    metadata JSONB
);
```

### Categories Table
```sql
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Processed Files Table
```sql
CREATE TABLE IF NOT EXISTS processed_files (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    transcription_id INTEGER REFERENCES transcriptions(id)
);
```

### Optimize Transcriptions Table
```sql
CREATE TABLE IF NOT EXISTS optimize_transcriptions (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    original_transcription_id INTEGER REFERENCES transcriptions(id),
    metadata JSONB
);
```

### Indices
```sql
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_processed_files_filename ON processed_files(filename);
CREATE INDEX IF NOT EXISTS idx_optimize_transcriptions_created_at ON optimize_transcriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_optimize_transcriptions_original_id ON optimize_transcriptions(original_transcription_id);
```

## Testing Connection

Create a test script (`test_db_connection.py`):
```python
import psycopg2
from db_utils.db_config import get_db_url

try:
    conn = psycopg2.connect(get_db_url())
    print("Database connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

## Troubleshooting

### Service Management
Check PostgreSQL service status:
```bash
# Check service status (Run Command Prompt as Administrator)
sc query postgresql

# Start service if needed
net start postgresql
```

### Reset Database
If you need to reset the database:
```sql
DROP DATABASE IF EXISTS transcriptions;
CREATE DATABASE transcriptions;
```

### Common Issues

1. **Service Not Running**
   - Check if PostgreSQL service is running in Windows Services
   - Start the service manually if needed

2. **Connection Refused**
   - Verify PostgreSQL is running
   - Check port number in connection string
   - Ensure firewall isn't blocking connection

3. **Authentication Failed**
   - Verify password in connection string
   - Check pg_hba.conf for authentication settings

### Important Notes

- Keep database credentials secure
- Never commit `.env` file to version control
- Ensure PostgreSQL service is running before application start
- Consider implementing database backup procedures for production

## Database Initialization

To initialize the database, run:
```bash
python db_utils/setup_database.py
```

This will:
1. Create the database if it doesn't exist
2. Create all necessary tables
3. Set up required indices
4. Initialize the connection pool

For additional database management functions, refer to `db_utils/db_manager.py`.

## Recent Updates

### Optimize Transcriptions Table
The `optimize_transcriptions` table has been added to store the optimized/processed content from transcriptions with a structured format. This table:

- Stores the entire output from the optimization process, which includes categorization, organized entries, to-do items, and projects
- References the original transcription via foreign key
- Can be queried by date to retrieve entries for a specific day
- Is used in the summarization process alongside file-based entries

The table design allows for efficient storage and retrieval of processed transcriptions while maintaining the relationship with the original transcription data. 