import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import json

from voice_diary.db_utils.db_config import get_db_url

# Ensure logging is configured
logger = logging.getLogger(__name__)

# Connection pool for reusing database connections
connection_pool = None

def initialize_db():
    """Initialize database and create necessary tables if they don't exist"""
    global connection_pool

    try:
        # Initialize connection pool
        db_url = get_db_url()
        logger.info(f"Initializing database with connection URL: {db_url}")
        
        # Test connection before creating pool
        logger.info("Testing direct database connection...")
        try:
            test_conn = psycopg2.connect(db_url)
            logger.info("Direct connection test successful")
            logger.info(f"PostgreSQL server version: {test_conn.server_version}")
            test_conn.close()
        except Exception as conn_error:
            logger.error(f"Direct connection test failed: {str(conn_error)}")
            return False
        
        # Create connection pool
        logger.info("Creating connection pool...")
        connection_pool = pool.SimpleConnectionPool(1, 10, db_url)
        logger.info("Connection pool created successfully")
        
        # Create tables
        create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Print more detailed traceback for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        
        # Create vd_transcriptions table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS vd_transcriptions (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            filename TEXT,
            audio_path TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            duration_seconds FLOAT,
            metadata JSONB
        )
        """)
        
        # Create index on transcriptions.created_at for faster date-based queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_vd_transcriptions_created_at ON vd_transcriptions(created_at)
        """)
        
        # Create vd_day_summaries table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS vd_day_summaries (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            summary_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            filename TEXT,
            date_range_start TIMESTAMP WITH TIME ZONE,
            date_range_end TIMESTAMP WITH TIME ZONE
        )
        """)
        
        # Create index on summary_date for faster queries
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_vd_day_summaries_date ON vd_day_summaries(summary_date)
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
                      duration_seconds=None, metadata=None):
    """
    Save a transcription to the database
    
    Args:
        content (str): The transcription text
        filename (str, optional): Original audio filename
        audio_path (str, optional): Path to the original audio file
        duration_seconds (float, optional): Duration of the audio in seconds
        metadata (dict, optional): Additional metadata for the transcription
        
    Returns:
        int: ID of the inserted record or None if error
    """
    conn = None
    transcription_id = None
    
    try:
        logger.info("Getting database connection for save_transcription...")
        conn = get_connection()
        
        if conn is None:
            logger.error("Failed to get connection from pool")
            return None
            
        logger.info("Creating cursor for database operation...")
        cur = conn.cursor()
        
        # Convert metadata to JSONB if provided
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Log what we're inserting
        logger.info(f"Inserting transcription: filename={filename}, audio_path={audio_path}")
        
        # Insert transcription
        cur.execute("""
        INSERT INTO vd_transcriptions 
        (content, filename, audio_path, duration_seconds, metadata)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """, (content, filename, audio_path, duration_seconds, metadata_json))
        
        transcription_id = cur.fetchone()[0]
        
        logger.info(f"Committing transaction for transcription ID: {transcription_id}")
        conn.commit()
        logger.info(f"Saved transcription with ID: {transcription_id}")
        return transcription_id
        
    except Exception as e:
        if conn:
            logger.error(f"Rolling back transaction due to error: {str(e)}")
            conn.rollback()
        logger.error(f"Error saving transcription: {str(e)}")
        # Print more detailed traceback for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    finally:
        if conn:
            logger.debug("Returning connection to pool")
            return_connection(conn)

def get_transcription(transcription_id):
    """Retrieve a transcription by ID"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT t.*
        FROM vd_transcriptions t
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
        SELECT t.*
        FROM vd_transcriptions t
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
        SELECT t.*
        FROM vd_transcriptions t
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

def save_day_summary(content, start_date=None, end_date=None, filename=None):
    """
    Save a day summary to the database
    
    Args:
        content (str): The summarized content
        start_date (datetime, optional): Start date of the summary period
        end_date (datetime, optional): End date of the summary period
        filename (str, optional): Path to the summary file
        
    Returns:
        int: ID of the inserted record or None if error
    """
    conn = None
    summary_id = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Insert summary
        cur.execute("""
        INSERT INTO vd_day_summaries 
        (content, summary_date, filename, date_range_start, date_range_end)
        VALUES (%s, CURRENT_TIMESTAMP, %s, %s, %s)
        RETURNING id
        """, (content, filename, start_date, end_date))
        
        summary_id = cur.fetchone()[0]
        
        conn.commit()
        logger.info(f"Saved day summary with ID: {summary_id}")
        return summary_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving day summary: {str(e)}")
        return None
    finally:
        if conn:
            return_connection(conn)

def get_day_summaries_by_date_range(start_date, end_date, limit=10):
    """
    Retrieve day summaries within a date range
    
    Args:
        start_date (datetime): Start date for the query
        end_date (datetime): End date for the query
        limit (int, optional): Maximum number of records to return
        
    Returns:
        list: List of day summary records as dictionaries
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT *
        FROM vd_day_summaries
        WHERE summary_date BETWEEN %s AND %s
        ORDER BY summary_date DESC
        LIMIT %s
        """, (start_date, end_date, limit))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving day summaries by date range: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)

def get_latest_day_summaries(limit=5):
    """
    Retrieve the most recent day summaries
    
    Args:
        limit (int, optional): Maximum number of records to return
        
    Returns:
        list: List of day summary records as dictionaries
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
        SELECT *
        FROM vd_day_summaries
        ORDER BY summary_date DESC
        LIMIT %s
        """, (limit,))
        
        results = cur.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error retrieving latest day summaries: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)

def check_summary_exists(start_date, end_date):
    """
    Check if a summary already exists for a specific date range
    
    Args:
        start_date (datetime): Start date for the query
        end_date (datetime): End date for the query
        
    Returns:
        bool: True if a summary exists, False otherwise
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Check for exact date range match
        cur.execute("""
        SELECT COUNT(*)
        FROM vd_day_summaries
        WHERE date_range_start = %s AND date_range_end = %s
        """, (start_date, end_date))
        
        count = cur.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"Error checking for existing summaries: {str(e)}")
        return False
    finally:
        if conn:
            return_connection(conn)
