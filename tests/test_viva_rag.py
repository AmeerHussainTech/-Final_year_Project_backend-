"""
Unit Test Suite for Local FAISS RAG Viva Question Generator
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

from services.viva_rag_engine import generate_viva_questions_rag, chunk_text, extract_key_terms

SAMPLE_TEXT = """
Presenova is an end-to-end multi-modal presentation coaching platform.
It uses automated slide evaluation, vocal dynamics tracking, and real-time live teleprompter feedback over WebSockets.
The system features a microservices architecture built with Flask, Flask-SocketIO, OpenCV, and MediaPipe.
Eye contact scoring is computed using MediaPipe Face Mesh iris landmarks (478 total: 468 base + 10 iris refinement).
Vocal delivery analysis computes words per minute (WPM), filler word ratios, and LanguageTool grammar evaluation.
Academic viva question generation utilizes passage retrieval and template synthesis to grill researchers on methodology.
"""

def test_chunking_and_extraction():
    chunks = chunk_text(SAMPLE_TEXT, target_word_count=50)
    assert len(chunks) >= 1
    assert "text" in chunks[0]

    terms = extract_key_terms(SAMPLE_TEXT)
    assert len(terms) > 0
    print(f"✅ Extracted Key Terms: {terms[:5]}")

def test_rag_viva_generation():
    result = generate_viva_questions_rag(
        file_path="mock_presentation.pptx",
        extracted_text=SAMPLE_TEXT,
        original_filename="mock_presentation.pptx",
        num_questions=5
    )

    assert result["success"] is True
    assert len(result["questions"]) > 0
    q = result["questions"][0]
    assert "id" in q
    assert "question" in q
    assert "difficulty" in q
    assert "prep_tip" in q

    print("============================================================")
    print("🧪 VIVA RAG GENERATOR TEST PASSED 100% SUCCESSFULLY")
    print(f"Generated {len(result['questions'])} Questions | Engine: {result['summary']['retrieval_engine']}")
    print("============================================================")

if __name__ == "__main__":
    test_chunking_and_extraction()
    test_rag_viva_generation()
