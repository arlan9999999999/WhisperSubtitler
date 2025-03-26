import os
import logging
import tempfile
import uuid
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import whisper_utils
import subtitle_formatter

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
        
        # Store the result in session
        session['transcription_result'] = result
        
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

@app.route('/clear', methods=['POST'])
def clear_session():
    # Clear session data and remove temporary files
    if 'file_path' in session:
        try:
            os.remove(session['file_path'])
        except Exception as e:
            logger.warning(f"Error removing temp file: {str(e)}")
    
    session.clear()
    return jsonify({'status': 'success', 'message': 'Session cleared'})

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': f'File too large. Maximum allowed size is {MAX_CONTENT_LENGTH / (1024 * 1024)}MB'}), 413

if __name__ == "__main__":
    # Create temp folder if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
