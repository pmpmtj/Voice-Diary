import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import json
import datetime
from pathlib import Path

from .db_config import get_db_url

logger = logging.getLogger(__name__)

# Connection pool for reusing database connections
connection_pool = None

def initialize_db():
    """Initialize database and create necessary tables if they don't exist"""
    global connection_pool
    
    try:
        # Initialize connection pool
        db_url = get_db_url()
        connection_pool = pool.SimpleConnectionPool(1, 10, db_url)
        
        # Create tables
        create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def get_connection():
    """Get a connection from the pool"""
    global connection_pool
    
    if connection_pool is None:
        initialize_db()
    
    return connection_pool.getconn()

def return_connection(conn):
    """Return a connection to the pool"""
    global connection_pool
    
    if connection_pool is not None:
        connection_pool.putconn(conn)

def create_tables():
    """Create necessary tables if they don't exist"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Create transcriptions table
        cur.execute("""
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
        )
        """)
        
        # Create categories table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create processed_files table to track processed audio files
        cur.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            transcription_id INTEGER REFERENCES transcriptions(id)
        )
        """)
        
        # Create optimize_transcriptions table to store processed/optimized transcription content
        cur.execute("""
        CREATE TABLE IF NOT EXISTS optimize_transcriptions (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            original_transcription_id INTEGER REFERENCES transcriptions(id),
            metadata JSONB
        )
        """)
        
        # Create index on transcriptions.created_at for faster date-based queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at)
        """)
        
        # Create index on processed_files.filename for faster lookups
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_processed_files_filename ON processed_files(filename)
        """)
        
        # Create index on optimize_transcriptions.created_at
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_optimize_transcriptions_created_at ON optimize_transcriptions(created_at)
        """)
        
        # Create index on optimize_transcriptions.original_transcription_id
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_optimize_transcriptions_original_id ON optimize_transcriptions(original_transcription_id)
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        raise
    finally:
        if conn:
            return_connection(conn)

def save_transcription(content, filename=None, audio_path=None, model_type=None, 
                      duration_seconds=None, category=None, metadata=None):
    """
    Save a transcription to the database
    
    Args:
        content (str): The transcription text
        filename (str, optional): Original audio filename
        audio_path (str, optional): Path to the original audio file
        model_type (str, optional): The model used for transcription
        duration_seconds (float, optional): Duration of the audio in seconds
        category (str, optional): Category name for the transcription
        metadata (dict, optional): Additional metadata for the transcription
        
    Returns:
        int: ID of the inserted record or None if error
    """
    conn = None
    category_id = None
    transcription_id = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Get category ID if provided
        if category:
            # Create category if it doesn't exist
            cur.execute("""
            INSERT INTO categories (name) 
            VALUES (%s) 
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """, (category,))
            category_id = cur.fetchone()[0]
        
        # Convert metadata to JSONB if provided
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Insert transcription
        cur.execute("""
        INSERT INTO transcriptions 
        (content, filename, audio_path, model_type, duration_seconds, category_id, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (content, filename, audio_path, model_type, duration_seconds, category_id, metadata_json))
        
        transcription_id = cur.fetchone()[0]
        
        # Record the processed file if filename is provided
        if filename and audio_path:
            cur.execute("""
            INSERT INTO processed_files 
            (filename, file_path, status, transcription_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (filename) DO UPDATE SET 
            processed_at = CURRENT_TIMESTAMP, 
            status = EXCLUDED.status,
            transcription_id = EXCLUDED.transcription_id
            """, (filename, audio_path, 'completed', transcription_id))
        
        conn.commit()
        logger.info(f"Saved transcription with ID: {transcription_id}")
        return transcription_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving transcription: {str(e)}")
        return None
    finally:
        if conn:
            return_connection(conn)

def get_transcription(transcription_id):
    """Retrieve a transcription by ID"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT t.*, c.name as category_name
        FROM transcriptions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.id = %s
        """, (transcription_id,))
        
        result = cur.fetchone()
        return result
    except Exception as e:
        logger.error(f"Error retrieving transcription: {str(e)}")
        return None
    finally:
        if conn:
            return_connection(conn)

def get_latest_transcriptions(limit=10):
    """Retrieve the latest transcriptions"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT t.*, c.name as category_name
        FROM transcriptions t
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.created_at DESC
        LIMIT %s
        """, (limit,))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving latest transcriptions: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)

def get_transcriptions_by_date_range(start_date, end_date):
    """Retrieve transcriptions within a date range"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT t.*, c.name as category_name
        FROM transcriptions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.created_at BETWEEN %s AND %s
        ORDER BY t.created_at DESC
        """, (start_date, end_date))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving transcriptions by date range: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)

def close_all_connections():
    """Close all database connections"""
    global connection_pool
    
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        logger.info("All database connections closed")

def save_optimized_transcription(content, original_transcription_id=None, metadata=None):
    """
    Save an optimized transcription to the optimize_transcriptions table
    
    Args:
        content (str): The optimized transcription text
        original_transcription_id (int, optional): ID of the original transcription
        metadata (dict, optional): Additional metadata for the transcription
        
    Returns:
        int: ID of the inserted record or None if error
    """
    conn = None
    optimized_transcription_id = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Convert metadata to JSONB if provided
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Insert optimized transcription
        cur.execute("""
        INSERT INTO optimize_transcriptions 
        (content, original_transcription_id, metadata)
        VALUES (%s, %s, %s)
        RETURNING id
        """, (content, original_transcription_id, metadata_json))
        
        optimized_transcription_id = cur.fetchone()[0]
        
        conn.commit()
        logger.info(f"Saved optimized transcription with ID: {optimized_transcription_id}")
        return optimized_transcription_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving optimized transcription: {str(e)}")
        return None
    finally:
        if conn:
            return_connection(conn)

def get_latest_optimized_transcriptions(limit=10):
    """Retrieve the latest optimized transcriptions"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT ot.*, t.content as original_content 
        FROM optimize_transcriptions ot
        LEFT JOIN transcriptions t ON ot.original_transcription_id = t.id
        ORDER BY ot.created_at DESC
        LIMIT %s
        """, (limit,))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving latest optimized transcriptions: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)

def get_optimized_transcriptions_by_date(date_str):
    """
    Retrieve optimized transcriptions from the database for a specific date
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        list: List of optimized transcription records
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Format the query to get all records for the given date
        # Using date_trunc to compare just the date portion
        cur.execute("""
        SELECT ot.*, t.content as original_content 
        FROM optimize_transcriptions ot
        LEFT JOIN transcriptions t ON ot.original_transcription_id = t.id
        WHERE DATE_TRUNC('day', ot.created_at) = DATE_TRUNC('day', %s::timestamp)
        ORDER BY ot.created_at
        """, (date_str,))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving optimized transcriptions by date: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)
