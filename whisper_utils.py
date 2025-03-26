import os
import logging
import tempfile
import subprocess
import whisper
import torch

# Configure logging
logger = logging.getLogger(__name__)

# Language code to full name mapping
LANGUAGE_MAP = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ar": "Arabic",
    "hi": "Hindi",
    "ko": "Korean",
    "tr": "Turkish",
    "pl": "Polish",
    "vi": "Vietnamese",
    "sv": "Swedish",
    "uk": "Ukrainian",
    "fa": "Persian"
}

def get_available_models():
    """Return a list of available Whisper models."""
    return {
        "tiny": "Tiny (fast, less accurate)",
        "base": "Base (balanced speed and accuracy)",
        "small": "Small (better accuracy, slower)",
        "medium": "Medium (good accuracy, slower)",
        "large": "Large (best accuracy, slowest)"
    }

def get_supported_languages():
    """Return a dictionary of supported languages."""
    return LANGUAGE_MAP

def extract_audio(video_path):
    """Extract audio from video file using FFmpeg."""
    try:
        audio_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        # Run FFmpeg to extract audio
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            audio_path
        ]
        
        logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"FFmpeg error: {result.stderr}")
        
        return audio_path
    
    except Exception as e:
        logger.error(f"Audio extraction error: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")

def transcribe_audio(file_path, model_name="base", language=None, task="transcribe"):
    """
    Transcribe audio or video file using Whisper model.
    
    Args:
        file_path: Path to audio or video file
        model_name: Whisper model to use (tiny, base, small, medium, large)
        language: Language code (optional, auto-detected if None)
        task: "transcribe" or "translate" (to English)
    
    Returns:
        Dictionary with transcription result
    """
    try:
        # Check if CUDA is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        # Handle video files - extract audio first
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in ['.mp4', '.avi', '.mov', '.webm']:
            logger.info(f"Extracting audio from video file: {file_path}")
            audio_path = extract_audio(file_path)
            logger.info(f"Audio extracted to: {audio_path}")
        else:
            audio_path = file_path
        
        # Load the Whisper model
        logger.info(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name, device=device)
        
        # Prepare options
        options = {
            "task": task,
        }
        
        if language:
            options["language"] = language
        
        # Run transcription
        logger.info(f"Starting transcription with options: {options}")
        result = model.transcribe(audio_path, **options)
        
        # Clean up the temporary audio file if extracted
        if audio_path != file_path:
            os.unlink(audio_path)
        
        logger.info("Transcription completed successfully")
        return result
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise Exception(f"Transcription failed: {str(e)}")
