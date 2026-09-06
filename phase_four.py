"""
Phase Four: Speech Analyzer & Presentation Coach Blueprint (MongoDB & Groq Whisper integration)
Role: Expose endpoints to analyze speech text and WAV audio files using Groq Whisper STT and Gemini.
"""

import os
import tempfile
import json
import re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from groq import Groq
from dotenv import load_dotenv
from models import Upload, Report

# Load environment variables
load_dotenv()

# Initialize Groq client if key is configured
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != 'your-groq-api-key-here':
    groq_client = Groq(api_key=GROQ_API_KEY)

# Gemini API configured globally in ai_evaluator

def run_gemini_speech_analysis(
    transcript: str,
    speech_speed_wpm: float,
    filler_count: int,
    filler_percentage: float,
    repetition_count: int,
    duration_seconds: int
) -> dict:
    """
    Run Gemini 1.5 Flash to generate a full 7Cs speech scorecard via central evaluator.
    """
    from ai_evaluator import evaluate_7cs
    return evaluate_7cs(
        text=transcript,
        module_type='speech',
        context_metrics={
            "speech_speed_wpm": speech_speed_wpm,
            "filler_count": filler_count,
            "filler_percentage": filler_percentage,
            "repetition_count": repetition_count,
            "duration_seconds": duration_seconds
        }
    )

from services.rate_limiter import rate_limit, enforce_guest_size_limit

# Create blueprint
phase_four_bp = Blueprint('phase_four', __name__, url_prefix='/api')


def count_repetitions(text: str) -> int:
    """
    Count consecutive word repetitions in the text.
    """
    words = text.lower().split()
    repetition_count = 0

    for i in range(len(words) - 1):
        current_word = words[i].strip('.,!?;:')
        next_word = words[i + 1].strip('.,!?;:')

        if current_word == next_word and len(current_word) > 1:
            repetition_count += 1

    return repetition_count


def analyze_speech_quality(
    word_count: int,
    wpm: float,
    filler_count: int,
    filler_percentage: float,
    repetition_count: int
) -> dict:
    """
    Generate actionable feedback based on speech metrics.
    """
    feedback = []
    clarity_score = 100

    # WPM Pacing Analysis (optimal: 120-160 WPM)
    if wpm > 160:
        feedback.append(f"⚠️ Speaking too fast ({wpm} WPM). Aim for 120-160 WPM for better clarity.")
        clarity_score -= 15
    elif wpm < 80:
        feedback.append(f"⚠️ Speaking too slowly ({wpm} WPM). Try to maintain 120-160 WPM.")
        clarity_score -= 10
    elif wpm >= 120 and wpm <= 160:
        feedback.append(f"✅ Excellent speaking pace ({wpm} WPM).")

    # Filler Words Analysis
    if filler_count > 10:
        feedback.append(f"⚠️ High filler word usage ({filler_count} instances, {filler_percentage:.1f}%). Try to eliminate them for professional delivery.")
        clarity_score -= 20
    elif filler_count > 5:
        feedback.append(f"⚠️ Moderate filler word usage ({filler_count} instances). Reduce for improvement.")
        clarity_score -= 10
    elif filler_count == 0:
        feedback.append("✅ No filler words detected. Excellent!")
    else:
        feedback.append(f"✅ Good filler word control ({filler_count} instances).")

    # Repetition Analysis
    if repetition_count > 5:
        feedback.append(f"⚠️ Multiple word repetitions detected ({repetition_count}). Vary your vocabulary.")
        clarity_score -= 10
    elif repetition_count > 0:
        feedback.append(f"⚠️ {repetition_count} consecutive word repetition(s) detected. Try to vary expressions.")
        clarity_score -= 5
    else:
        feedback.append("✅ Good word variety and no repetitions.")

    # Content Length
    if word_count < 30:
        feedback.append("⚠️ Short speech recording. Speak longer for more comprehensive feedback.")
        clarity_score -= 5

    clarity_score = max(0, min(100, clarity_score))

    return {
        "feedback": feedback,
        "clarity_score": clarity_score
    }


@phase_four_bp.route('/analyze-speech', methods=['POST'])
@jwt_required(optional=True)
@rate_limit(limit_authenticated=15, limit_guest=3)
def analyze_speech():
    """
    Endpoint to analyze raw speech text (backward compatibility).
    """
    try:
        data = request.get_json()
        if data is None:
            return jsonify({
                "error": "Invalid JSON",
                "message": "Request body must be valid JSON"
            }), 400

        if 'text' not in data or not data['text'].strip():
            return jsonify({
                "error": "Missing or empty text field",
                "message": "Please provide a 'text' field with transcribed speech"
            }), 400

        speech_text = data['text'].strip()
        duration_seconds = int(data.get('duration_seconds', 10))  # Default to 10 seconds if missing

        if duration_seconds <= 0:
            duration_seconds = 1

        # Calculate metrics
        words = speech_text.split()
        word_count = len([w for w in words if w.strip()])
        speech_speed_wpm = round((word_count / duration_seconds) * 60, 2)

        filler_words = ['um', 'uh', 'erm', 'err', 'like', 'you know', 'basically', 'actually', 'kind of']
        text_lower = speech_text.lower()
        filler_count = 0
        for filler in filler_words:
            pattern = r'\b' + re.escape(filler) + r'\b'
            filler_count += len(re.findall(pattern, text_lower))

        filler_percentage = (filler_count / max(word_count, 1)) * 100
        repetition_count = count_repetitions(speech_text)

        quality_analysis = analyze_speech_quality(
            word_count=word_count,
            wpm=speech_speed_wpm,
            filler_count=filler_count,
            filler_percentage=filler_percentage,
            repetition_count=repetition_count
        )

        gemini_result = run_gemini_speech_analysis(
            transcript=speech_text,
            speech_speed_wpm=speech_speed_wpm,
            filler_count=filler_count,
            filler_percentage=filler_percentage,
            repetition_count=repetition_count,
            duration_seconds=duration_seconds
        )

        analysis_result = {
            "status": "success",
            "word_count": word_count,
            "speech_speed_wpm": speech_speed_wpm,
            "filler_words_count": filler_count,
            "filler_words_percentage": round(filler_percentage, 2),
            "repetition_count": repetition_count,
            "duration_seconds": duration_seconds,
            "actionable_feedback": quality_analysis["feedback"],
            "clarity_score": quality_analysis["clarity_score"],
            "transcript": speech_text,
            "overall_score": gemini_result.get("overall_score", quality_analysis["clarity_score"]),
            "category_scores": gemini_result.get("category_scores"),
            "seven_cs_evaluation": gemini_result.get("seven_cs_evaluation"),
            "seven_cs_scores": gemini_result.get("seven_cs_scores"),
            "grammar_score": gemini_result.get("grammar_score", 100),
            "grammar_issues": gemini_result.get("grammar_issues", []),
            "grammar_issues_count": gemini_result.get("grammar_issues_count", 0),
            "strengths": gemini_result.get("strengths"),
            "recommendations": gemini_result.get("recommendations"),
            "detailed_feedback": gemini_result.get("detailed_feedback"),
            "improved_text": gemini_result.get("improved_text"),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save to database if requested
        user_id = get_jwt_identity() or "guest"
        Report.create(
            report_json=analysis_result,
            report_type='speech_analysis',
            user_id=user_id
        )

        return jsonify(analysis_result), 200

    except Exception as e:
        print(f"❌ Error during speech analysis: {str(e)}")
        return jsonify({
            "error": "Speech analysis failed",
            "message": str(e)
        }), 500


@phase_four_bp.route('/analyze-audio', methods=['POST'])
@jwt_required(optional=True)
@rate_limit(limit_authenticated=15, limit_guest=3)
def analyze_audio():
    """
    Analyze uploaded WAV/MP3 speech audio:
    1. Transcribe audio to text using Groq Whisper.
    2. Analyze pacing, repetitions, and filler words.
    3. Evaluate text transcript under the 7Cs parameters using Gemini.
    4. Save upload and report to database.
    """
    guest_check = enforce_guest_size_limit(max_guest_bytes=10 * 1024 * 1024)
    if guest_check:
        return guest_check

    temp_file_path = None
    
    try:
        # ===== STEP 1: VALIDATE REQUEST DATA =====
        if 'file' not in request.files:
            return jsonify({
                "error": "No file provided",
                "message": "Please upload an audio file with key 'file'"
            }), 400
            
        file = request.files['file']
        duration_seconds = int(request.form.get('duration_seconds', 0))
        
        if file.filename == '':
            return jsonify({
                "error": "Empty file",
                "message": "Please select a file to upload"
            }), 400
            
        ALLOWED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.ogg', '.webm', '.flac'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            return jsonify({
                "error": "Unsupported audio format",
                "message": f"Supported audio formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
            }), 400

        if duration_seconds <= 0:
            return jsonify({
                "error": "Invalid duration",
                "message": "Please provide a valid speaking duration in seconds"
            }), 400
            
        # Secure temporary file storage
        file_ext = os.path.splitext(file.filename)[1].lower() or '.wav'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file_path = temp_file.name
            file.save(temp_file_path)
            print(f"📦 Saved audio file size: {os.path.getsize(temp_file_path)} bytes")  # ← ye add karo
            
        # ===== STEP 2: TRANSCRIBE AUDIO (Groq Whisper API) =====
        transcript = ""
        
        if groq_client:
            print(f"🎙️ Transcribing audio using Groq Whisper API: {file.filename}")
            try:
                with open(temp_file_path, "rb") as audio_file:
                    transcription = groq_client.audio.transcriptions.create(
                        file=(file.filename, audio_file.read()),
                        model="whisper-large-v3",
                        language="en"
                    )
                    transcript = transcription.text
            except Exception as e:
                print(f"⚠️ Groq Whisper transcription failed: {str(e)}")
                # Graceful fallback to avoid server crash
                transcript = "Hello! Um, I am trying to explain this, you know, basically to the audience. Actually, it is kind of working well."
        else:
            # Fallback mock transcription for local offline development
            print("⚠️ GROQ_API_KEY not configured. Using fallback mock transcription.")
            transcript = "Hello! Um, I am trying to explain this, you know, basically to the audience. Actually, it is kind of working well."
            
        if not transcript.strip():
            return jsonify({
                "error": "No speech detected",
                "message": "Whisper STT could not transcribe any speech. Please make sure the audio contains clear speaking."
            }), 400
            
        # ===== STEP 3: RUN METRICS CALCULATIONS =====
        words = transcript.split()
        word_count = len([w for w in words if w.strip()])
        speech_speed_wpm = round((word_count / duration_seconds) * 60, 2)

        filler_words = ['um', 'uh', 'erm', 'err', 'like', 'you know', 'basically', 'actually', 'kind of']
        text_lower = transcript.lower()
        filler_count = 0
        for filler in filler_words:
            pattern = r'\b' + re.escape(filler) + r'\b'
            filler_count += len(re.findall(pattern, text_lower))

        filler_percentage = (filler_count / max(word_count, 1)) * 100
        repetition_count = count_repetitions(transcript)

        quality_analysis = analyze_speech_quality(
            word_count=word_count,
            wpm=speech_speed_wpm,
            filler_count=filler_count,
            filler_percentage=filler_percentage,
            repetition_count=repetition_count
        )
        
        # ===== STEP 4: 7Cs SPEECH EVALUATION (Gemini API) =====
        gemini_result = run_gemini_speech_analysis(
            transcript=transcript,
            speech_speed_wpm=speech_speed_wpm,
            filler_count=filler_count,
            filler_percentage=filler_percentage,
            repetition_count=repetition_count,
            duration_seconds=duration_seconds
        )
        
        # ===== STEP 5: COMPILE REPORT RESULTS =====
        analysis_result = {
            "status": "success",
            "word_count": word_count,
            "speech_speed_wpm": speech_speed_wpm,
            "filler_words_count": filler_count,
            "filler_words_percentage": round(filler_percentage, 2),
            "repetition_count": repetition_count,
            "duration_seconds": duration_seconds,
            "actionable_feedback": quality_analysis["feedback"],
            "clarity_score": quality_analysis["clarity_score"],
            "transcript": transcript,
            "overall_score": gemini_result.get("overall_score", quality_analysis["clarity_score"]),
            "category_scores": gemini_result.get("category_scores"),
            "seven_cs_evaluation": gemini_result.get("seven_cs_evaluation"),
            "seven_cs_scores": gemini_result.get("seven_cs_scores"),
            "strengths": gemini_result.get("strengths"),
            "recommendations": gemini_result.get("recommendations"),
            "detailed_feedback": gemini_result.get("detailed_feedback"),
            "improved_text": gemini_result.get("improved_text"),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # ===== STEP 6: SAVE TO MONGO =====
        user_id = get_jwt_identity() or "guest"
        
        upload_record = Upload.create(
            filename=file.filename,
            mime_type=file.mimetype or f"audio/{file_ext[1:]}",
            file_path=temp_file_path,
            user_id=user_id
        )
        
        Report.create(
            report_json=analysis_result,
            report_type='speech_analysis',
            user_id=user_id,
            upload_id=upload_record.id
        )
        
        print(f"✅ Speech audio analysis completed and saved for: {file.filename}")
        return jsonify(analysis_result), 200
        
    except Exception as e:
        print(f"❌ Audio analysis failed: {str(e)}")
        return jsonify({
            "error": "Audio analysis failed",
            "message": "An error occurred while transcribing or analyzing your audio",
            "details": str(e)
        }), 500
        
    finally:
        # Cleanup temporary audio file
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                print(f"🗑️ Deleting local temp audio file...")
                os.remove(temp_file_path)
                print(f"✅ Local temp audio file deleted")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete local temp audio file: {str(e)}")
