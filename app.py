import os
import logging
import tempfile
import uuid
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
import whisper_utils
import subtitle_formatter
import supabase_client  # Import Supabase client

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'avi', 'mov', 'flac', 'ogg', 'm4a', 'webm'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Check if Supabase is properly configured
SUPABASE_CONFIGURED = bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    # Get available whisper models
    models = whisper_utils.get_available_models()
    
    # Get supported languages
    languages = whisper_utils.get_supported_languages()
    
    return render_template('index.html', models=models, languages=languages)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Create a unique filename and save the file
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(file_path)
        
        # Store file details in session
        session['file_path'] = file_path
        session['original_filename'] = original_filename
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': original_filename,
            'status': 'ready'
        })
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Get parameters from request
        model_name = request.form.get('model', 'base')
        language = request.form.get('language', None)
        task = request.form.get('task', 'transcribe')  # 'transcribe' or 'translate'
        
        # Check if file path exists in session
        if 'file_path' not in session:
            return jsonify({'error': 'No file has been uploaded'}), 400
        
        file_path = session['file_path']
        
        # Update status to processing
        response = {'status': 'processing'}
        
        # Process the file with Whisper
        logger.info(f"Starting transcription with model: {model_name}, language: {language}, task: {task}")
        result = whisper_utils.transcribe_audio(file_path, model_name, language, task)
        
        # Store the result and processing parameters in session for later use
        session['transcription_result'] = result
        session['model_name'] = model_name
        session['task'] = task
        
        return jsonify({
            'status': 'completed',
            'message': 'Transcription completed successfully',
            'preview': result['text'][:500] + ('...' if len(result['text']) > 500 else '')
        })
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': f'An error occurred during transcription: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_subtitles():
    try:
        # Check if transcription result exists in session
        if 'transcription_result' not in session:
            return jsonify({'error': 'No transcription found. Please transcribe a file first.'}), 400
        
        # Get format from request
        subtitle_format = request.form.get('format', 'srt')
        
        # Get original filename from session
        original_filename = session.get('original_filename', 'subtitles')
        base_filename = os.path.splitext(original_filename)[0]
        
        # Format the subtitles
        result = session['transcription_result']
        
        if subtitle_format == 'srt':
            content, output_filename = subtitle_formatter.to_srt(result, base_filename)
            mimetype = 'text/plain'
        elif subtitle_format == 'vtt':
            content, output_filename = subtitle_formatter.to_vtt(result, base_filename)
            mimetype = 'text/vtt'
        elif subtitle_format == 'txt':
            content, output_filename = subtitle_formatter.to_txt(result, base_filename)
            mimetype = 'text/plain'
        else:
            return jsonify({'error': f'Unsupported subtitle format: {subtitle_format}'}), 400
        
        # Upload to Supabase storage if configured
        supabase_file_info = None
        if SUPABASE_CONFIGURED:
            try:
                # Get language info from result
                detected_language = result.get('language', 'unknown')
                model_name = session.get('model_name', 'base')
                task = session.get('task', 'transcribe')
                
                # Additional metadata for the file
                metadata = {
                    "language": detected_language,
                    "model": model_name,
                    "task": task
                }
                
                # Upload to Supabase storage
                supabase_file_info = supabase_client.upload_subtitle_file(
                    file_content=content,
                    file_format=subtitle_format,
                    original_filename=original_filename,
                    metadata=metadata
                )
                
                if supabase_file_info:
                    # Store file ID in session to allow deletion after download
                    session['last_uploaded_file_id'] = supabase_file_info['file_id']
                    session['last_uploaded_file_format'] = subtitle_format
                    logger.info(f"File uploaded to Supabase storage: {supabase_file_info['storage_filename']}")
                
            except Exception as se:
                logger.error(f"Supabase storage error: {str(se)}")
                # Continue with download even if Supabase fails
        
        # Create temporary file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(content.encode('utf-8'))
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=output_filename,
            mimetype=mimetype
        )
    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': f'An error occurred during subtitle generation: {str(e)}'}), 500

@app.route('/download-complete', methods=['POST'])
def download_complete():
    """
    Endpoint to call after a download is complete to trigger deletion of the file from Supabase.
    """
    if not SUPABASE_CONFIGURED:
        return jsonify({'status': 'skipped', 'message': 'Supabase not configured'}), 200
        
    try:
        # Check if we have a file to delete
        file_id = session.get('last_uploaded_file_id')
        file_format = session.get('last_uploaded_file_format')
        
        if not file_id or not file_format:
            return jsonify({'status': 'skipped', 'message': 'No file to delete'}), 200
            
        # Delete the file from Supabase storage
        success = supabase_client.delete_subtitle_file(file_id, file_format)
        
        if success:
            # Clear the file info from session
            session.pop('last_uploaded_file_id', None)
            session.pop('last_uploaded_file_format', None)
            
            return jsonify({
                'status': 'success', 
                'message': 'File deleted from cloud storage after download'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to delete file from cloud storage'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in download complete callback: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_session():
    # Clear session data and remove temporary files
    if 'file_path' in session:
        try:
            os.remove(session['file_path'])
        except Exception as e:
            logger.warning(f"Error removing temp file: {str(e)}")
    
    # Delete any stored files from Supabase if they exist
    if SUPABASE_CONFIGURED and 'last_uploaded_file_id' in session:
        try:
            file_id = session.get('last_uploaded_file_id')
            file_format = session.get('last_uploaded_file_format')
            if file_id and file_format:
                supabase_client.delete_subtitle_file(file_id, file_format)
                logger.info(f"Deleted file from Supabase storage during session clear: {file_id}.{file_format}")
        except Exception as e:
            logger.warning(f"Error removing Supabase file during session clear: {str(e)}")
    
    session.clear()
    return jsonify({'status': 'success', 'message': 'Session cleared'})

@app.route('/subtitle/<file_id>.<format>')
def download_from_storage(file_id, format):
    """
    Download a file directly from Supabase storage and then delete it.
    """
    if not SUPABASE_CONFIGURED:
        return jsonify({'error': 'Supabase storage not configured'}), 400
        
    try:
        # Get the file content from Supabase
        content = supabase_client.get_subtitle_file(file_id, format)
        
        if not content:
            return jsonify({'error': 'File not found in storage'}), 404
            
        # Determine the mimetype
        if format == 'srt':
            mimetype = 'application/x-subrip'
        elif format == 'vtt':
            mimetype = 'text/vtt'
        else:
            mimetype = 'text/plain'
            
        # Create a temporary file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(content.encode('utf-8'))
        temp_file.close()
        
        # Set filename
        filename = f"subtitle.{format}"
            
        # Schedule file for deletion after download
        session['last_downloaded_file_id'] = file_id
        session['last_downloaded_file_format'] = format
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        logger.error(f"Error downloading file from storage: {str(e)}")
        return jsonify({'error': f'An error occurred while retrieving the file: {str(e)}'}), 500
        
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': f'File too large. Maximum allowed size is {MAX_CONTENT_LENGTH / (1024 * 1024)}MB'}), 413

# Context processor to add global variables to templates
@app.context_processor
def inject_global_vars():
    """Inject global variables into all templates."""
    return {
        'SUPABASE_CONFIGURED': SUPABASE_CONFIGURED
    }

# Initialize Supabase storage if needed
if SUPABASE_CONFIGURED:
    try:
        supabase_client.create_storage_if_not_exist()
        logger.info("Supabase storage checked/created")
    except Exception as e:
        logger.error(f"Error initializing Supabase storage: {str(e)}")

if __name__ == "__main__":
    # Create temp folder if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
