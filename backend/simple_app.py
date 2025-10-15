import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import speech_recognition as sr
from pydub import AudioSegment
import json
from datetime import datetime
import logging
import subprocess

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS properly - allow all origins for development
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'm4a', 'flac'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure FFmpeg path
ffmpeg_path = r"C:\Users\manik\Downloads\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ["PATH"]
    AudioSegment.ffmpeg = ffmpeg_path
    AudioSegment.converter = ffmpeg_path
    logger.info(f"✅ FFmpeg configured: {ffmpeg_path}")
else:
    logger.warning("⚠️ FFmpeg not found at specified path, trying system PATH")

# Configure Gemini Pro
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY not found in environment variables")
    # For development, you can set it directly here:
    # GEMINI_API_KEY = "your_gemini_api_key_here"
    # Or prompt for it:
    print("🔑 Please enter your Gemini Pro API key: ")
    GEMINI_API_KEY = input().strip()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    logger.info("✅ Gemini Pro configured successfully")
except Exception as e:
    logger.error(f"❌ Gemini Pro configuration failed: {e}")
    model = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def convert_audio_to_wav(audio_path):
    """Convert any audio file to WAV format using FFmpeg"""
    try:
        logger.info(f"Converting {audio_path} to WAV...")
        
        wav_path = audio_path.rsplit('.', 1)[0] + '_converted.wav'
        
        # Try different ffmpeg commands
        try:
            cmd = [ffmpeg_path, '-i', audio_path, '-ac', '1', '-ar', '16000', '-y', wav_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except:
            # Fallback to system ffmpeg
            cmd = ['ffmpeg', '-i', audio_path, '-ac', '1', '-ar', '16000', '-y', wav_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg conversion failed: {result.stderr}")
        
        if not os.path.exists(wav_path):
            raise Exception("Converted WAV file was not created")
            
        logger.info("✅ Audio conversion successful")
        return wav_path
        
    except Exception as e:
        raise Exception(f"Audio conversion failed: {str(e)}")

def transcribe_audio_speech_recognition(audio_path):
    """Transcribe audio using Google Speech Recognition"""
    try:
        logger.info("🎙️ Starting audio transcription...")
        
        recognizer = sr.Recognizer()
        wav_path = convert_audio_to_wav(audio_path)
        
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        
        # Clean up
        if os.path.exists(wav_path):
            os.remove(wav_path)
        
        logger.info(f"✅ Transcription completed: {len(text.split())} words")
        return text
        
    except sr.UnknownValueError:
        raise Exception("Speech recognition could not understand the audio")
    except sr.RequestError as e:
        raise Exception(f"Speech recognition service error: {e}")
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")

def generate_summary_with_gemini(transcript):
    """Generate meeting summary using Gemini Pro"""
    if not model:
        raise Exception("Gemini Pro model not configured")
    
    try:
        logger.info("🧠 Generating AI summary with Gemini Pro...")
        
        prompt = f"""
        Analyze this meeting transcript and provide structured output:

        TRANSCRIPT:
        {transcript}

        Provide JSON with:
        - summary: brief overview
        - key_decisions: list of decisions
        - action_items: list with task, owner, deadline, priority
        - next_steps: list of next steps
        - meeting_metrics: total_decisions, total_action_items, key_topics

        Be specific and extract real content from the transcript.
        """

        response = model.generate_content(prompt)
        response_text = response.text
        
        # Clean JSON response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        summary_data = json.loads(response_text)
        
        # Ensure required fields
        if 'meeting_metrics' not in summary_data:
            summary_data['meeting_metrics'] = {}
        summary_data["meeting_metrics"]["total_decisions"] = len(summary_data.get("key_decisions", []))
        summary_data["meeting_metrics"]["total_action_items"] = len(summary_data.get("action_items", []))
        summary_data["meeting_metrics"]["key_topics"] = summary_data.get("meeting_metrics", {}).get("key_topics", ["General Discussion"])
        
        logger.info("✅ AI summary generated successfully")
        return summary_data
        
    except Exception as e:
        logger.error(f"Gemini Pro error: {e}")
        # Fallback summary
        return {
            "summary": "Generated summary: " + (transcript[:200] + "..." if len(transcript) > 200 else transcript),
            "key_decisions": ["Review meeting notes for decisions"],
            "action_items": [{
                "task": "Review and extract action items from transcript",
                "owner": "Team", 
                "deadline": "ASAP",
                "priority": "High"
            }],
            "next_steps": ["Review complete transcript"],
            "meeting_metrics": {
                "total_decisions": 1,
                "total_action_items": 1,
                "key_topics": ["Meeting Discussion"]
            }
        }

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_audio():
    """Handle audio file upload and processing"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(audio_file.filename):
            return jsonify({
                'error': f'File type not supported. Use: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
            }), 400
        
        # Check file size
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        
        if file_size > 25 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 25MB'}), 400
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_{timestamp}.mp3"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        logger.info(f"📁 Processing: {filename} ({file_size / 1024 / 1024:.2f} MB)")
        
        # Process the file
        transcript = transcribe_audio_speech_recognition(filepath)
        summary_data = generate_summary_with_gemini(transcript)
        
        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)
        
        logger.info("✅ Processing completed successfully")
        
        return jsonify({
            'success': True,
            'transcript': transcript,
            'summary': summary_data,
            'filename': filename,
            'processing_time': datetime.now().isoformat(),
            'word_count': len(transcript.split())
        })
        
    except Exception as e:
        if 'filepath' in locals() and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        logger.error(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'gemini_pro': '✅ Configured' if model else '❌ Not configured',
            'backend': '✅ Running',
            'cors': '✅ Enabled'
        },
        'supported_formats': list(app.config['ALLOWED_EXTENSIONS']),
        'max_file_size': '25MB'
    })

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

if __name__ == '__main__':
    print("🚀 Meeting Summarizer API Starting...")
    print(f"🔑 Gemini Pro: {'✅ Ready' if model else '❌ Need API Key'}")
    print(f"🌐 Server: http://localhost:5000")
    print("📝 Upload audio files to: http://localhost:5000/api/upload")
    print("💡 Health check: http://localhost:5000/api/health")
    print("🔧 CORS enabled for: http://localhost:3000")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)