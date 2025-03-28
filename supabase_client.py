"""
Supabase client utility for the subtitle generator app.
This module handles the connection to Supabase and provides
functions for interacting with the database.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase client if credentials are available
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = None

if url and key:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        supabase = None
else:
    logger.warning("Supabase URL or key not provided. Supabase features disabled.")

def create_tables_if_not_exist():
    """
    Create the necessary tables in Supabase if they don't exist.
    This is executed when the app starts.
    """
    # This function will check and create tables using SQL
    # For simplicity, we'll rely on Supabase's interface for table creation
    # The tables should be created in the Supabase dashboard before using this app
    pass

def save_transcription(file_name, original_language, model_used, task_type, format_type, content_preview):
    """
    Save a transcription record to the database.
    
    Args:
        file_name: Original file name
        original_language: Detected or selected language
        model_used: Whisper model size used (tiny, base, etc.)
        task_type: "transcribe" or "translate"
        format_type: "srt", "vtt", or "txt"
        content_preview: Short preview of the transcription content
    
    Returns:
        The ID of the inserted record or None if an error occurred
    """
    if not supabase:
        logger.warning("Supabase client not available, skipping save_transcription")
        return None
        
    try:
        # Truncate preview to avoid too large records
        if content_preview and len(content_preview) > 1000:
            content_preview = content_preview[:997] + "..."
            
        response = supabase.table("transcriptions").insert({
            "file_name": file_name,
            "language": original_language,
            "model": model_used,
            "task": task_type,
            "format": format_type,
            "preview": content_preview,
            "created_at": "now()"  # Supabase will convert this to the current timestamp
        }).execute()
        
        if len(response.data) > 0:
            return response.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"Error saving transcription to Supabase: {e}")
        return None

def get_recent_transcriptions(limit=10):
    """
    Get recent transcriptions from the database.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of transcription records, ordered by creation date (newest first)
    """
    if not supabase:
        logger.warning("Supabase client not available, returning empty transcription list")
        return []
        
    try:
        response = supabase.table("transcriptions") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Error retrieving transcriptions from Supabase: {e}")
        return []

def get_transcription_by_id(transcription_id):
    """
    Get a specific transcription by ID.
    
    Args:
        transcription_id: The ID of the transcription to retrieve
        
    Returns:
        The transcription record or None if not found
    """
    if not supabase:
        logger.warning("Supabase client not available, cannot retrieve transcription")
        return None
        
    try:
        response = supabase.table("transcriptions") \
            .select("*") \
            .eq("id", transcription_id) \
            .execute()
        
        if len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error retrieving transcription from Supabase: {e}")
        return None