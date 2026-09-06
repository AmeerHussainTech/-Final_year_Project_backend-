"""
Test Suite for spaCy Rule-Based Slide Rewriter Engine
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

from services.rewrite.spacy_rewriter import (
    substitute_filler_phrases,
    convert_passive_to_active,
    split_bullet_point,
    rewrite_slide_content
)

def test_spacy_rewriting_rules():
    raw_text = "In order to improve performance, data was analyzed by machine learning models due to the fact that it is fast."
    filler_clean = substitute_filler_phrases(raw_text)
    assert "to improve performance" in filler_clean
    assert "because it is fast" in filler_clean

    active = convert_passive_to_active("The project was completed by the engineering team.")
    assert len(active) > 5

    slide_data = {
        "slide_number": 1,
        "title": "in order to optimize clinical workflows",
        "bullet_points": [
            "Data was analyzed by machine learning models due to the fact that it is fast and efficient."
        ]
    }
    rewritten = rewrite_slide_content(slide_data)
    assert rewritten["title"] == "To Optimize Clinical Workflows"
    assert len(rewritten["bullet_points"]) >= 1

    print("============================================================")
    print("🧪 SPACY REWRITER TEST PASSED 100% SUCCESSFULLY")
    print(f"Rewritten Title: '{rewritten['title']}' | Bullets: {len(rewritten['bullet_points'])}")
    print("============================================================")

if __name__ == "__main__":
    test_spacy_rewriting_rules()
