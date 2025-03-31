"""
Supabase client utility for the subtitle generator app.
This module handles storage for subtitle files using Supabase Storage.
"""

import os
import logging
import uuid
from dotenv import load_dotenv
import re
import json

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

# Constants for storage
STORAGE_BUCKET_NAME = "subtitle_files"

def create_storage_if_not_exist():
    """
    Create the necessary storage bucket in Supabase if it doesn't exist.
    This is executed when the app starts.
    """
    if not supabase:
        logger.warning("Supabase client not available, skipping storage bucket creation")
        return
        
    try:
        # Try to get buckets to check if our bucket exists
        logger.info("Checking Supabase storage buckets...")
        
        try:
            # List buckets to see if ours exists
            buckets = supabase.storage.list_buckets()
            bucket_exists = any(bucket.name == STORAGE_BUCKET_NAME for bucket in buckets)
            
            if not bucket_exists:
                # Create new bucket for subtitle files
                supabase.storage.create_bucket(STORAGE_BUCKET_NAME, {"public": False})
                logger.info(f"Created storage bucket: {STORAGE_BUCKET_NAME}")
            else:
                logger.info(f"Storage bucket {STORAGE_BUCKET_NAME} already exists")
                
        except Exception as bucket_error:
            logger.error(f"Error checking/creating storage bucket: {bucket_error}")
            raise
            
        logger.info("Supabase storage checked/created")
    except Exception as e:
        logger.error(f"Error setting up Supabase storage: {e}")
        # We'll continue anyway and let the app work without Supabase if there's an issue

def upload_subtitle_file(file_content, file_format, original_filename, metadata=None):
    """
    Upload a subtitle file to Supabase Storage.
    
    Args:
        file_content: The content of the subtitle file
        file_format: Format extension (srt, vtt, txt)
        original_filename: Original filename for reference
        metadata: Additional metadata to store with the file
        
    Returns:
        A dictionary with file_id and download_url or None if upload failed
    """
    if not supabase:
        logger.warning("Supabase client not available, skipping file upload")
        return None
        
    try:
        # Generate a unique ID for the file
        file_id = str(uuid.uuid4())
        
        # Create a filename with the correct extension
        storage_filename = f"{file_id}.{file_format}"
        
        # Prepare metadata to store with the file
        file_metadata = {
            "original_filename": original_filename,
            "format": file_format,
            "created_at": "",  # Will be set by Supabase
            "auto_delete": True  # Flag to indicate this file should be deleted after download
        }
        
        # Add any additional metadata
        if metadata:
            file_metadata.update(metadata)
            
        # Convert metadata to JSON string
        metadata_json = json.dumps(file_metadata)
        
        # Upload file to storage
        result = supabase.storage.from_(STORAGE_BUCKET_NAME).upload(
            storage_filename,
            file_content.encode('utf-8'),
            {"content-type": f"text/{file_format}", "x-upsert": "true", "metadata": metadata_json}
        )
        
        # Get public URL (will need signed URLs for private buckets)
        file_url = supabase.storage.from_(STORAGE_BUCKET_NAME).get_public_url(storage_filename)
        
        return {
            "file_id": file_id,
            "storage_filename": storage_filename,
            "download_url": file_url
        }
    except Exception as e:
        logger.error(f"Error uploading file to Supabase storage: {e}")
        return None

def get_subtitle_file(file_id, file_format):
    """
    Get a subtitle file from Supabase Storage.
    
    Args:
        file_id: The unique ID of the file
        file_format: The file format extension
        
    Returns:
        The file content as a string or None if not found
    """
    if not supabase:
        logger.warning("Supabase client not available, cannot retrieve file")
        return None
        
    try:
        # Construct the filename
        storage_filename = f"{file_id}.{file_format}"
        
        # Download the file
        result = supabase.storage.from_(STORAGE_BUCKET_NAME).download(storage_filename)
        
        # Decode the content
        content = result.decode('utf-8')
        
        return content
    except Exception as e:
        logger.error(f"Error downloading file from Supabase storage: {e}")
        return None

def delete_subtitle_file(file_id, file_format):
    """
    Delete a subtitle file from Supabase Storage.
    
    Args:
        file_id: The unique ID of the file
        file_format: The file format extension
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not supabase:
        logger.warning("Supabase client not available, cannot delete file")
        return False
        
    try:
        # Construct the filename
        storage_filename = f"{file_id}.{file_format}"
        
        # Delete the file
        supabase.storage.from_(STORAGE_BUCKET_NAME).remove([storage_filename])
        
        logger.info(f"Deleted file from storage: {storage_filename}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file from Supabase storage: {e}")
        return False