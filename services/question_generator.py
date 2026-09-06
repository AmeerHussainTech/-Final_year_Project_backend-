"""
Viva Question Generator Service

Generates thesis-defense style viva questions from uploaded documents (PPTX/PDF).
Reuses the existing text_extractor for content extraction and the AI provider
abstraction layer for LLM interaction.

Usage:
    from services.question_generator import generate_viva_questions

    result = generate_viva_questions("path/to/file.pptx", "original_name.pptx", num_questions=10)
    # Returns: { "success": True, "questions": [...], "summary": {...}, ... }
"""

import json
import logging
import os
import time
from typing import Optional

from services.ai import get_provider
from services.ai.prompts import build_question_generation_prompt
from services.text_extractor import (
    get_all_text_for_analysis,
    get_extension,
    is_allowed_for_analysis,
)

logger = logging.getLogger(__name__)


def generate_viva_questions(
    file_path: str,
    original_filename: str,
    num_questions: int = 10,
) -> dict:
    """Generate viva/thesis-defense style questions from an uploaded document.

    Extracts text from the document, sends it to the AI provider with a
    specialised prompt, and returns structured questions with categories,
    difficulty levels, source references, and preparation tips.

    Args:
        file_path: Absolute path to the uploaded temporary file.
        original_filename: Original filename for extension detection.
        num_questions: Desired number of questions (default 10).

    Returns:
        A dict with the following structure on success:
            {"success": True, "questions": [...], "summary": {...},
             "processing_time": "X.XX seconds"}
        Or on failure:
            {"success": False, "message": "Error description"}
    """
    started = time.time()
    try:
        # ── Step 1: Validate file type ─────────────────────────────────
        ext = get_extension(original_filename)
        if not is_allowed_for_analysis(original_filename):
            return {
                "success": False,
                "message": f"Unsupported file type '{ext}'. Please upload a .pptx or .pdf file.",
            }

        # ── Step 2: Extract text ───────────────────────────────────────
        extracted_text = get_all_text_for_analysis(file_path, original_filename)
        if not extracted_text or len(extracted_text.strip()) < 20:
            return {
                "success": False,
                "message": "The uploaded document contains too little extractable text to generate meaningful questions.",
            }

        logger.info(
            "[question_generator] Extracted %d characters from '%s'.",
            len(extracted_text), original_filename,
        )

        # ── Step 3: Local FAISS RAG Question Generation ─────────────────
        from services.viva_rag_engine import generate_viva_questions_rag
        
        rag_result = generate_viva_questions_rag(
            file_path=file_path,
            extracted_text=extracted_text,
            original_filename=original_filename,
            num_questions=num_questions,
        )

        elapsed = time.time() - started
        if rag_result.get("success"):
            rag_result["processing_time"] = f"{elapsed:.2f} seconds"
            return rag_result
        else:
            return {
                "success": False,
                "message": rag_result.get("message", "Question generation failed."),
            }

    except ValueError as exc:
        logger.warning("[question_generator] Validation error: %s", exc)
        return {"success": False, "message": str(exc)}
    except RuntimeError as exc:
        logger.error("[question_generator] Processing error: %s", exc)
        return {
            "success": False,
            "message": "Question generation is temporarily unavailable. Please try again.",
        }
    except Exception:
        logger.exception("[question_generator] Unexpected error.")
        return {
            "success": False,
            "message": "An unexpected error occurred during question generation.",
        }

