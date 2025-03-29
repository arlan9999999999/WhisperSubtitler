"""
Supabase client utility for the subtitle generator app.
This module handles the connection to Supabase and provides
functions for interacting with the database.
"""

import os
import logging
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase client if credentials are available
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = None

# Validate URL format
def is_valid_url(url):
    if not url:
        return False
    # Basic URL validation pattern
    pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IPv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))

if url and key:
    if not is_valid_url(url):
        logger.error(f"Invalid Supabase URL format: {url}")
        supabase = None
    else:
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
    if not supabase:
        logger.warning("Supabase client not available, skipping table creation")
        return
        
    try:
        # Check if the transcriptions table exists, if not create it
        logger.info("Checking Supabase tables...")
        
        # Use raw SQL to create the table if it doesn't exist
        query = """
        CREATE TABLE IF NOT EXISTS transcriptions (
            id BIGSERIAL PRIMARY KEY,
            file_name TEXT NOT NULL,
            language TEXT,
            model TEXT,
            task TEXT,
            format TEXT,
            preview TEXT,
            subtitle_content TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Execute the query
        supabase.table("transcriptions").execute(query)
        logger.info("Supabase tables checked/created")
    except Exception as e:
        logger.error(f"Error creating tables in Supabase: {e}")
        # We'll continue anyway and let the app work without Supabase if there's an issue

def save_transcription(file_name, original_language, model_used, task_type, format_type, content_preview, subtitle_content):
    """
    Save a transcription record to the database.
    
    Args:
        file_name: Original file name
        original_language: Detected or selected language
        model_used: Whisper model size used (tiny, base, etc.)
        task_type: "transcribe" or "translate"
        format_type: "srt", "vtt", or "txt"
        content_preview: Short preview of the transcription content
        subtitle_content: The complete subtitle content
    
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
            "subtitle_content": subtitle_content,
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