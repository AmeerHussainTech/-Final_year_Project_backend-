"""HTTP endpoints for the Viva Question Generator feature."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from services.download_service import (
    MAX_UPLOAD_BYTES,
    validate_upload_size,
)
from services.question_generator import generate_viva_questions
from services.rate_limiter import rate_limit
from services.text_extractor import (
    get_extension,
    is_allowed_for_analysis,
    validate_file_content,
)

logger = logging.getLogger(__name__)

question_generator_bp = Blueprint(
    'question_generator', __name__, url_prefix='/api/questions'
)


def _error(message: str, status: int):
    return jsonify({'success': False, 'message': message}), status


@question_generator_bp.errorhandler(RequestEntityTooLarge)
def handle_upload_too_large(_exception):
    return _error(
        f'File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.',
        413,
    )


def _save_validated_upload(file_storage, original_filename: str) -> str:
    """Persist an upload to an OS temp file, then validate size and signature.

    Mirrors the same pattern used in routes/presentation_rewriter.py.
    """
    extension = get_extension(original_filename)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension or '.upload') as stream:
            temporary_path = stream.name
        file_storage.save(temporary_path)
        validate_upload_size(os.path.getsize(temporary_path))
        validate_file_content(temporary_path, original_filename)
        return temporary_path
    except Exception:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning('[routes/question_generator] Could not remove rejected upload.')
        raise


@question_generator_bp.route('/generate', methods=['POST'])
def generate_questions():
    """Generate viva/thesis-defense questions from an uploaded PPTX or PDF.

    Accepts multipart/form-data with:
        - file (required): PPTX or PDF file
        - num_questions (optional, default 10): Number of questions to generate

    Returns JSON with questions, summary, and processing time.
    """
    temporary_path = None
    started = datetime.now(timezone.utc)
    try:
        # ── Size check on Content-Length header ────────────────────────
        if request.content_length and request.content_length > MAX_UPLOAD_BYTES:
            return _error(
                f'File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.',
                413,
            )

        # ── Validate file presence ─────────────────────────────────────
        file_storage = request.files.get('file')
        if file_storage is None:
            return _error('No file uploaded. Send multipart/form-data with field "file".', 400)

        original_filename = file_storage.filename or ''
        if not original_filename:
            return _error('No file selected.', 400)

        if not is_allowed_for_analysis(original_filename):
            ext = get_extension(original_filename)
            return _error(
                f'Unsupported file type "{ext}". Please upload a .pptx or .pdf file.',
                400,
            )

        # ── Read optional num_questions ────────────────────────────────
        try:
            num_questions = int(request.form.get('num_questions', 10))
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except (TypeError, ValueError):
            num_questions = 10

        # ── Save and validate upload ───────────────────────────────────
        temporary_path = _save_validated_upload(file_storage, original_filename)
        logger.info(
            '[routes/question_generator] Received %r (%s bytes) for %d questions.',
            original_filename, os.path.getsize(temporary_path), num_questions,
        )

        # ── Generate questions ─────────────────────────────────────────
        result = generate_viva_questions(
            file_path=temporary_path,
            original_filename=original_filename,
            num_questions=num_questions,
        )

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()

        if not result.get('success', False):
            return jsonify(result), 400

        response = {
            'success': True,
            'questions': result['questions'],
            'summary': result['summary'],
            'processing_time': result.get('processing_time', f'{elapsed:.2f} seconds'),
            'message': f"Generated {result['summary']['total_questions']} viva questions successfully.",
        }

        return jsonify(response), 200

    except ValueError as exc:
        logger.warning('[routes/question_generator] Validation error: %s', exc)
        return _error(str(exc), 400)
    except RuntimeError as exc:
        logger.error('[routes/question_generator] Processing error: %s', exc)
        return _error('Question generation is temporarily unavailable. Please try again.', 502)
    except Exception:
        logger.exception('[routes/question_generator] Unexpected processing error.')
        return _error('Unexpected error during question generation.', 500)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning(
                    '[routes/question_generator] Could not remove temporary upload %r.',
                    temporary_path,
                )

