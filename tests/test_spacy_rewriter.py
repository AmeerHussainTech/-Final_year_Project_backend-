"""
Unit Test Suite for spaCy Rule-Based Slide Rewriter Engine
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

def test_filler_substitution():
    text = "In order to achieve high speed, we used FAISS due to the fact that it is fast."
    cleaned = substitute_filler_phrases(text)
    assert "to achieve high speed" in cleaned
    assert "because it is fast" in cleaned
    print("✅ Filler Substitution Test Passed!")

def test_bullet_splitting():
    long_bullet = "This is a very long bullet point that exceeds fifteen words in length and must be split into multiple smaller bullet points for slide scannability."
    split = split_bullet_point(long_bullet, max_words=15)
    assert len(split) >= 2
    print("✅ Bullet Splitting Test Passed!")

def test_slide_rewriting():
    slide = {
        "slide_number": 1,
        "title": "in order to optimize performance",
        "bullet_points": [
            "Data was vectorized by the system in order to improve speed due to the fact that it is efficient.",
            "Second bullet point that is concise."
        ]
    }
    result = rewrite_slide_content(slide)
    assert result["title"] == "To Optimize Performance"
    assert len(result["bullet_points"]) >= 2

    print("============================================================")
    print("🧪 SPACY REWRITER TEST PASSED 100% SUCCESSFULLY")
    print(f"Rewritten Title: '{result['title']}' | Bullets Count: {len(result['bullet_points'])}")
    print("============================================================")

if __name__ == "__main__":
    test_filler_substitution()
    test_bullet_splitting()
    test_slide_rewriting()
