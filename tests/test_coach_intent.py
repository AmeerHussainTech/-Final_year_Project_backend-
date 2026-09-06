"""
Unit Test Suite for Local AI Coach Intent Classifier & State Machine
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services.coach_intent_engine import process_coach_chat, predict_intent

def test_intent_classification():
    assert predict_intent("Hello Dr Vance") == "greeting"
    assert predict_intent("Is my text density too high for 6x6?") == "slide_feedback"
    assert predict_intent("Am I speaking too fast? What is my WPM?") == "pacing_question"
    assert predict_intent("Grill me on my thesis methodology") == "viva_prep"
    assert predict_intent("Did I use too many filler words like um?") == "disfluency_query"
    print("✅ Intent Classification Test Passed!")

def test_coach_chat_processing():
    res = process_coach_chat("Grill me on my research methodology", current_state="INIT")
    assert res["persona"] == "Dr. Alexander Vance"
    assert res["intent"] == "viva_prep"
    assert res["next_state"] == "VIVA_PRACTICE"
    assert len(res["recommendations"]) > 0
    assert "response" in res

    print("============================================================")
    print("🧪 COACH INTENT ENGINE TEST PASSED 100% SUCCESSFULLY")
    print(f"Persona: {res['persona']} | Detected Intent: {res['intent']}")
    print("============================================================")

if __name__ == "__main__":
    test_intent_classification()
    test_coach_chat_processing()
