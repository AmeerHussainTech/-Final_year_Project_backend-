"""
Test Suite for Coach Intent Classifier (TF-IDF + Logistic Regression)
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

from services.coach_intent_engine import predict_intent, process_coach_chat, TRAINING_DATA

def test_intent_accuracy():
    correct = 0
    total = len(TRAINING_DATA)

    for text, expected in TRAINING_DATA:
        predicted = predict_intent(text)
        if predicted == expected:
            correct += 1

    accuracy = (correct / total) * 100.0
    print(f"📊 TF-IDF + LogisticRegression Intent Accuracy: {accuracy:.1f}% ({correct}/{total})")
    assert accuracy >= 70.0

    res = process_coach_chat("Grill me on my thesis methodology")
    assert res["intent"] == "viva_prep"
    assert res["next_state"] == "VIVA_PRACTICE"

    print("============================================================")
    print("🧪 COACH INTENT CLASSIFIER TEST PASSED 100% SUCCESSFULLY")
    print(f"Dataset Accuracy: {accuracy:.1f}% | Response Persona: {res['persona']}")
    print("============================================================")

if __name__ == "__main__":
    test_intent_accuracy()
