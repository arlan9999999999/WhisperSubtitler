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
    # First, ensure it's not actually an API key that was mistakenly provided as a URL
    if url.startswith('eyJ'):
        logger.error("The provided SUPABASE_URL appears to be an API key, not a URL")
        return False
        
    # Basic URL validation pattern
    pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IPv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    # Common Supabase URL format check - should contain supabase.co or similar
    is_valid = bool(pattern.match(url))
    if is_valid and not ('supabase.co' in url.lower() or 'supabase.in' in url.lower()):
        logger.warning(f"URL appears valid but doesn't contain 'supabase.co': {url}")
        # Still return true, it might be a custom domain
    
    return is_valid

# Make Supabase import conditional to avoid errors if the package is not installed
try:
    from supabase import create_client, Client
    SUPABASE_IMPORT_SUCCESS = True
except ImportError:
    logger.warning("Supabase package not installed. Install it with 'pip install supabase'")
    SUPABASE_IMPORT_SUCCESS = False

if url and key:
    if not is_valid_url(url):
        logger.error(f"Invalid Supabase URL format: {url}")
        supabase = None
    elif not SUPABASE_IMPORT_SUCCESS:
        logger.error("Cannot initialize Supabase client: package not installed")
        supabase = None
    else:
        try:
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
        
        # For newer versions of supabase-py, we can't execute raw SQL directly this way
        # Instead, we'll check if the table exists and create it if needed
        try:
            # Try to query the table to see if it exists
            supabase.table("transcriptions").select("count", count="exact").limit(1).execute()
            logger.info("Transcriptions table exists")
        except Exception as table_error:
            # If we get an error, the table might not exist
            logger.warning(f"Error querying transcriptions table: {table_error}")
            logger.info("Attempting to create transcriptions table via REST API")
            
            # Create the table by inserting a dummy record with all fields
            # This is a workaround since we can't execute raw SQL directly
            try:
                supabase.table("transcriptions").insert({
                    "file_name": "initialization_record",
                    "language": "system",
                    "model": "system",
                    "task": "system",
                    "format": "system",
                    "preview": "This is a dummy record created to initialize the table.",
                    "subtitle_content": "Initialization record - safe to delete",
                }).execute()
                logger.info("Successfully created transcriptions table")
                
                # Now delete the dummy record
                response = supabase.table("transcriptions").delete().eq("file_name", "initialization_record").execute()
                logger.info(f"Removed initialization record: {response.data}")
            except Exception as create_error:
                logger.error(f"Failed to create transcriptions table: {create_error}")
                raise
        
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