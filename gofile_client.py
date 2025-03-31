"""
Gofile client utility for the subtitle generator app.
This module handles storage for subtitle files using Gofile.io API.
"""
import os
import json
import requests
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gofile API constants
GOFILE_API_URL = "https://api.gofile.io"
GOFILE_ACCOUNT_TOKEN = os.environ.get("GOFILE_ACCOUNT_TOKEN", "zlIFYhO5jHt5kVnN6Orit3jM0hEZA8LX")

def get_server():
    """
    Get the best Gofile server to upload files to.
    
    Returns:
        The server URL or None if request failed
    """
    try:
        response = requests.get(f"{GOFILE_API_URL}/getServer")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "ok":
                return data["data"]["server"]
        logger.error(f"Failed to get server: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Error getting server: {str(e)}")
        return None

def upload_subtitle_file(file_content, file_format, original_filename, metadata=None):
    """
    Upload a subtitle file to Gofile.io Storage.
    
    Args:
        file_content: The content of the subtitle file
        file_format: Format extension (srt, vtt, txt)
        original_filename: Original filename for reference
        metadata: Additional metadata to store with the file
        
    Returns:
        A dictionary with file_id and download_url or None if upload failed
    """
    try:
        # Get the best server for upload
        server = get_server()
        if not server:
            logger.error("Failed to get server for upload")
            return None
        
        # Create temporary file for upload
        base_filename = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        output_filename = f"{base_filename}.{file_format}"
        
        # Prepare the files and data for upload
        files = {
            'file': (output_filename, file_content, f'text/{file_format}')
        }
        
        data = {
            'token': GOFILE_ACCOUNT_TOKEN,
            'folderId': 'createFolder',
            'folderName': 'subtitles_temp',
            'description': json.dumps(metadata) if metadata else ''
        }
        
        # Make the upload request
        upload_url = f"https://{server}.gofile.io/uploadFile"
        response = requests.post(upload_url, files=files, data=data)
        
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "ok":
                file_id = data["data"]["fileId"]
                file_url = data["data"]["downloadPage"]
                direct_link = data["data"]["downloadLink"]
                
                logger.info(f"File uploaded successfully: {file_id}")
                return {
                    "file_id": file_id,
                    "download_url": file_url,
                    "direct_link": direct_link
                }
            else:
                logger.error(f"Upload failed: {data.get('status')}: {data.get('message', 'Unknown error')}")
        else:
            logger.error(f"Upload failed with status code {response.status_code}: {response.text}")
        
        return None
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return None

def delete_subtitle_file(file_id):
    """
    Delete a subtitle file from Gofile.io Storage.
    
    Args:
        file_id: The unique ID of the file
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        url = f"{GOFILE_API_URL}/deleteContent"
        data = {
            "token": GOFILE_ACCOUNT_TOKEN,
            "contentId": file_id
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "ok":
                logger.info(f"File {file_id} deleted successfully")
                return True
            else:
                logger.error(f"Delete failed: {data.get('status')}: {data.get('message', 'Unknown error')}")
        else:
            logger.error(f"Delete failed with status code {response.status_code}: {response.text}")
        
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False