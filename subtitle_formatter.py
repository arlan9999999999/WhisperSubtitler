import re
from datetime import timedelta

def format_timestamp(seconds, include_ms=True):
    """
    Convert seconds to SRT/VTT timestamp format.
    
    Args:
        seconds: Time in seconds
        include_ms: Whether to include milliseconds (True for SRT/VTT, False for simple display)
        
    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    
    if include_ms:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def to_srt(result, base_filename):
    """
    Convert Whisper result to SRT format.
    
    Args:
        result: Whisper transcription result
        base_filename: Base filename for the output
        
    Returns:
        Tuple of (content, output_filename)
    """
    segments = result.get("segments", [])
    output = []
    
    for i, segment in enumerate(segments):
        # Get start and end time
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        
        # Get text and clean up any special characters
        text = segment.get("text", "").strip()
        
        # Format as SRT
        output.append(f"{i+1}")
        output.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        output.append(f"{text}")
        output.append("")  # Empty line
    
    content = "\n".join(output)
    output_filename = f"{base_filename}.srt"
    
    return content, output_filename

def to_vtt(result, base_filename):
    """
    Convert Whisper result to WebVTT format.
    
    Args:
        result: Whisper transcription result
        base_filename: Base filename for the output
        
    Returns:
        Tuple of (content, output_filename)
    """
    segments = result.get("segments", [])
    output = ["WEBVTT", ""]  # VTT header
    
    for i, segment in enumerate(segments):
        # Get start and end time
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        
        # Convert timestamp format (VTT uses dots instead of commas)
        start_vtt = format_timestamp(start).replace(",", ".")
        end_vtt = format_timestamp(end).replace(",", ".")
        
        # Get text and clean up any special characters
        text = segment.get("text", "").strip()
        
        # Format as VTT
        output.append(f"{start_vtt} --> {end_vtt}")
        output.append(f"{text}")
        output.append("")  # Empty line
    
    content = "\n".join(output)
    output_filename = f"{base_filename}.vtt"
    
    return content, output_filename

def to_txt(result, base_filename):
    """
    Convert Whisper result to plain text format.
    
    Args:
        result: Whisper transcription result
        base_filename: Base filename for the output
        
    Returns:
        Tuple of (content, output_filename)
    """
    # Get the full text if available, otherwise concat segments
    if "text" in result:
        content = result["text"]
    else:
        segments = result.get("segments", [])
        content = "\n".join([segment.get("text", "").strip() for segment in segments])
    
    output_filename = f"{base_filename}.txt"
    
    return content, output_filename
