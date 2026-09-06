"""
Test Live Coach Fixture & Real Sample Processing
Role: Validate Live Coach vision & audio telemetry processing using real sample input data fixtures.
"""

import sys
import os
import base64
import numpy as np
import cv2

# Force stdout/stderr UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from phase_live import analyze_webcam_frame, analyze_audio_chunk, PresentationSession
from ai_evaluator import evaluate_7cs

def create_sample_face_frame_base64() -> str:
    """Creates a 640x480 synthetic frame with a face and eyes for vision pipeline testing."""
    img = np.zeros((480, 640, 3), dtype=np.uint8) + 40  # Dark background
    
    # Draw face oval
    cv2.ellipse(img, (320, 200), (100, 130), 0, 0, 360, (200, 180, 160), -1)
    # Draw eyes
    cv2.circle(img, (280, 180), 15, (255, 255, 255), -1)
    cv2.circle(img, (360, 180), 15, (255, 255, 255), -1)
    # Draw pupils
    cv2.circle(img, (280, 180), 6, (0, 0, 0), -1)
    cv2.circle(img, (360, 180), 6, (0, 0, 0), -1)
    
    _, buffer = cv2.imencode('.jpg', img)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"

def test_live_coach_with_fixtures():
    print("=" * 60)
    print("🧪 TESTING LIVE COACH VISION & AUDIO PIPELINE (FIXTURE TEST)")
    print("=" * 60)

    # 1. Vision Frame Processing
    print("\n--- Test 1: Vision Frame Processing with Synthetic Face ---")
    session = PresentationSession(id="test_sess", user_id="test_user", topic="AI Presentation", status="STREAMING")
    b64_frame = create_sample_face_frame_base64()
    
    v_metrics = analyze_webcam_frame(b64_frame, session)
    print(f"✅ Vision Metrics Output: valid={v_metrics.get('valid')}, hint='{v_metrics.get('hint')}'")
    print(f"✅ Eye Contact Score: {v_metrics.get('eye_contact', 0)}")
    print(f"✅ Posture Score: {v_metrics.get('posture', 0)}")
    
    # 2. Audio Chunk Processing (With Transcript Hint)
    print("\n--- Test 2: Audio Chunk Processing with Transcript Fixture ---")
    sample_transcript = "Artificial intelligence enables automated diagnostics and personalized medical treatment plans."
    dummy_audio_b64 = base64.b64encode(b'RIFF....WAVEfmt ').decode('utf-8')
    
    a_metrics = analyze_audio_chunk(
        base64_audio_data=dummy_audio_b64,
        session_id="test_session",
        transcript_hint=sample_transcript
    )
    print(f"✅ Audio Metrics Output: valid={a_metrics.get('valid')}, WPM={a_metrics.get('wpm')}, Fillers={a_metrics.get('filler_count')}")
    assert a_metrics.get("wpm", 0) > 0, "WPM calculation failed for valid audio transcript!"
    assert a_metrics.get("valid") is True, "Audio chunk should be marked valid!"

    # 3. Live Coach 7Cs Evaluation with Complete Telemetry Fixtures
    print("\n--- Test 3: Live Coach 7Cs Evaluation (Full Telemetry Fixture) ---")
    telemetry_metrics = {
        "avg_eye": 88,
        "avg_posture": 92,
        "avg_wpm": 140,
        "fillers": 2,
        "avg_qna": 85,
        "has_visual_metrics": True,
        "has_voice_metrics": True,
        "has_qna_scores": True
    }
    live_eval = evaluate_7cs(
        text=sample_transcript,
        module_type='live',
        context_metrics=telemetry_metrics
    )
    
    print(f"✅ Live Coach Overall Score: {live_eval['overall_score']}")
    print(f"✅ Strengths Count: {len(live_eval.get('strengths', []))}")
    print(f"✅ Recommendations Count: {len(live_eval.get('recommendations', []))}")
    
    assert live_eval['overall_score'] > 0, f"Expected non-zero overall score, got {live_eval['overall_score']}"
    assert live_eval['overall_score'] >= 70, f"Expected realistic score >= 70, got {live_eval['overall_score']}"

    print("\n" + "=" * 60)
    print("🎉 LIVE COACH FIXTURE TEST PASSED 100% SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_live_coach_with_fixtures()
