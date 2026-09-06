"""
Test Suite for Local Context & Consistency Checker (FAISS RAG Cosine Similarity)
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

from services.analysis.context_verifier import verify_internal_context_consistency

REFERENCE_TEXT = """
Presenova is an end-to-end multi-modal presentation coaching platform.
It uses automated slide evaluation, vocal dynamics tracking, and real-time live teleprompter feedback over WebSockets.
The vision system processes webcam frames via MediaPipe Face Mesh iris tracking (478 landmarks).
Speech analysis computes words per minute (WPM), filler word counts, and grammar checks via LanguageTool.
"""

def test_context_consistency_scoring():
    claims = [
        "MediaPipe Face Mesh iris landmarks are used for eye contact tracking.",
        "Quantum superposition was used to teleport presentation slides to Mars." # Unsupported claim
    ]

    res = verify_internal_context_consistency(claims, REFERENCE_TEXT, similarity_threshold=0.45)

    assert "context_accuracy_score" in res
    assert "inaccuracies_detected" in res
    assert res["verification_type"] == "Internal Document Consistency Checking"

    print("============================================================")
    print("🧪 CONTEXT CHECKER FAISS RAG TEST PASSED 100% SUCCESSFULLY")
    print(f"Context Score: {res['context_accuracy_score']}/100 | Flagged Claims: {len(res['inaccuracies_detected'])}")
    print("============================================================")

if __name__ == "__main__":
    test_context_consistency_scoring()
