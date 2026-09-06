"""
Test Suite for Analyzer Scikit-Learn RandomForestRegressor Models
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

from nlp_module.scoring_model import score_text_offline

SAMPLE_TEXT = """
Artificial Intelligence in Healthcare: A Strategic Implementation Plan.
Slide 1: Executive Overview.
Machine learning models analyze clinical imagery to detect early-stage anomalies.
Our pilot program achieved high precision across 500 patient diagnostic cases.
"""

def test_sklearn_scoring():
    scores, seven_cs, feats = score_text_offline(SAMPLE_TEXT)

    assert "overall_score" in scores
    assert "Structure" in scores
    assert "Clarity" in scores
    assert "Clear" in seven_cs
    assert feats["word_count"] > 10

    print("============================================================")
    print("🧪 ANALYZER SKLEARN SCORING TEST PASSED 100% SUCCESSFULLY")
    print(f"Overall Predicted Score: {scores['overall_score']}/100 | Clarity: {scores['Clarity']}/100")
    print("============================================================")

if __name__ == "__main__":
    test_sklearn_scoring()
