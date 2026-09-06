"""HTTP endpoints for the AI presentation rewriter."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file, url_for
from flask_jwt_extended import jwt_required
from werkzeug.exceptions import RequestEntityTooLarge

from services.download_service import (
    MAX_UPLOAD_BYTES,
    cleanup_old_files,
    ensure_download_folder,
    get_download_path,
    validate_upload_size,
)
from services.report_generator import load_report_for_pptx
from services.rewrite_engine import run_analysis_pipeline, run_rewrite_pipeline
from services.text_extractor import (
    get_extension,
    is_allowed_for_analysis,
    is_allowed_for_rewrite,
    validate_file_content,
)

logger = logging.getLogger(__name__)

presentation_rewriter_bp = Blueprint(
    'presentation_rewriter', __name__, url_prefix='/api/presentation-rewriter'
)
ensure_download_folder()


def _error(message: str, status: int):
    return jsonify({'success': False, 'message': message}), status


@presentation_rewriter_bp.errorhandler(RequestEntityTooLarge)
def handle_upload_too_large(_exception):
    return _error(f'File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.', 413)


def _save_validated_upload(file_storage, original_filename: str) -> str:
    """Persist an upload to an OS temp file, then validate size and signature."""
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
                logger.warning('[routes/rewriter] Could not remove rejected upload.')
        raise


VALID_MODES = {'quick', 'professional', 'academic'}
VALID_TONES = {'professional', 'academic', 'business', 'technical', 'executive', 'marketing', 'formal', 'simple_english'}


@presentation_rewriter_bp.route('/submit', methods=['POST'])
@jwt_required(optional=True)
def submit_presentation():
    """Accept a PPTX, rewrite supported text, and return a download URL.

    Query parameters:
        mode: Processing mode — quick | professional (default) | academic
        tone: Writing tone — professional (default) | academic | business | technical
              | executive | marketing | formal | simple_english
    """
    temporary_path = None
    started = datetime.now(timezone.utc)
    try:
        if request.content_length and request.content_length > MAX_UPLOAD_BYTES:
            return _error(f'File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.', 413)
        file_storage = request.files.get('file')
        if file_storage is None:
            return _error('No file uploaded. Send multipart/form-data with field "file".', 400)
        original_filename = file_storage.filename or ''
        if not original_filename:
            return _error('No file selected.', 400)
        if not is_allowed_for_rewrite(original_filename):
            return _error(
                f'File type "{get_extension(original_filename)}" cannot be rewritten. '
                'Only .pptx is supported for text-preserving rewrites. PDFs are analysis-only.', 400
            )

        # Read mode and tone from query/form parameters
        mode = (request.form.get('mode') or request.args.get('mode') or 'professional').lower().strip()
        tone = (request.form.get('tone') or request.args.get('tone') or 'professional').lower().strip()
        if mode not in VALID_MODES:
            return _error(f"Invalid mode '{mode}'. Valid modes: {', '.join(sorted(VALID_MODES))}", 400)
        if tone not in VALID_TONES:
            return _error(f"Invalid tone '{tone}'. Valid tones: {', '.join(sorted(VALID_TONES))}", 400)

        temporary_path = _save_validated_upload(file_storage, original_filename)
        logger.info(
            '[routes/rewriter] Received %r (%s bytes) [mode=%s, tone=%s].',
            original_filename, os.path.getsize(temporary_path), mode, tone,
        )
        result = run_rewrite_pipeline(temporary_path, original_filename, mode=mode, tone=tone)
        try:
            cleanup_old_files()
        except Exception:
            logger.warning('[routes/rewriter] Output cleanup failed.', exc_info=True)

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        download_url = url_for(
            'presentation_rewriter.download_improved_presentation',
            filename=result['output_filename'],
        )
        response = {
            'success': True,
            'download_url': download_url,
            'output_filename': result['output_filename'],
            'slides_processed': result['slides_processed'],
            'processing_time': f'{elapsed:.2f} seconds',
            'quality_scores': result['quality_scores'],
            'improvements': result['improvements'],
            'processing_steps': result['processing_steps'],
            'metadata': result.get('metadata', {}),
            'mode': result.get('mode', mode),
            'tone': result.get('tone', tone),
            'message': 'Presentation successfully improved by AI.',
        }

        # Include new platform data if available
        if result.get('final_assessment'):
            response['final_assessment'] = result['final_assessment']
        if result.get('executive_summary'):
            response['executive_summary'] = result['executive_summary']
        if result.get('analytics'):
            response['analytics'] = result['analytics']
        if result.get('recommendations'):
            response['recommendations'] = result['recommendations']
        if result.get('statistics'):
            response['statistics'] = result['statistics']

        # Persist report history to database so dashboard analysis count stays accurate
        try:
            from flask_jwt_extended import get_jwt_identity
            from models import Report
            user_id = get_jwt_identity() or 'guest'
            qs = result.get('quality_scores', {})
            report_json = {
                "overall_score": qs.get('overall_score', 85),
                "topic": original_filename,
                "presentation_title": original_filename,
                "slides_processed": result.get('slides_processed', 0),
                "category_scores": qs.get('category_scores', {}),
                "seven_cs_scores": qs.get('seven_cs_scores', {}),
                "improvements": result.get('improvements', []),
                "mode": mode,
                "tone": tone
            }
            Report.create(
                report_json=report_json,
                report_type='presentation_analysis',
                user_id=user_id
            )
            logger.info(f"[routes/rewriter] Saved Report for presentation rewrite ({original_filename}) to user {user_id}")
        except Exception as _re:
            logger.warning(f"[routes/rewriter] Could not save Report history: {_re}")

        return jsonify(response), 200
    except ValueError as exc:
        logger.warning('[routes/rewriter] Validation error: %s', exc)
        return _error(str(exc), 400)
    except RuntimeError as exc:
        logger.error('[routes/rewriter] Processing error: %s', exc)
        return _error('Presentation processing is temporarily unavailable. Please try again.', 502)
    except Exception:
        logger.exception('[routes/rewriter] Unexpected processing error.')
        return _error('Unexpected presentation processing error.', 500)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning('[routes/rewriter] Could not remove temporary upload %r.', temporary_path)


@presentation_rewriter_bp.route('/analyze', methods=['POST'])
@jwt_required(optional=True)
def analyze_presentation():
    """Analyze a PPTX or PDF without producing an output file."""
    temporary_path = None
    started = datetime.now(timezone.utc)
    try:
        if request.content_length and request.content_length > MAX_UPLOAD_BYTES:
            return _error(f'File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.', 413)
        file_storage = request.files.get('file')
        if file_storage is None:
            return _error('No file uploaded. Send multipart/form-data with field "file".', 400)
        original_filename = file_storage.filename or ''
        if not original_filename:
            return _error('No file selected.', 400)
        if not is_allowed_for_analysis(original_filename):
            return _error('Unsupported file type. Please upload a .pptx or .pdf file.', 400)

        temporary_path = _save_validated_upload(file_storage, original_filename)
        result = run_analysis_pipeline(temporary_path, original_filename)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        return jsonify({
            'success': True,
            'quality_scores': result['quality_scores'],
            'slides_analysed': result.get('slides_analysed'),
            'processing_steps': result['processing_steps'],
            'processing_time': f'{elapsed:.2f} seconds',
            'message': 'Quality analysis complete.',
        }), 200
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception:
        logger.exception('[routes/rewriter] Analysis error.')
        return _error('Presentation analysis failed.', 500)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                logger.warning('[routes/rewriter] Could not remove temporary analysis upload.')


@presentation_rewriter_bp.route('/download/<filename>', methods=['GET'])
def download_improved_presentation(filename: str):
    """Serve only generated, validated PPTX output files."""
    try:
        path = get_download_path(filename)
        return send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path),
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            max_age=0,
        )
    except FileNotFoundError:
        return _error('File not found or has expired. Please resubmit the presentation.', 404)
    except Exception:
        logger.exception('[routes/rewriter] Download error.')
        return _error('Download failed.', 500)


# ─── Progress Tracking (poll-based) ────────────────────────────────────────
# In-memory map: filename -> progress dict. Written by the pipeline,
# read by the frontend polling endpoint.
_progress_map: dict[str, dict] = {}


def set_progress(filename: str, step_index: int, total_steps: int, message: str) -> None:
    """Store the current processing progress for a given output file."""
    _progress_map[filename] = {
        'step_index': step_index,
        'total_steps': total_steps,
        'message': message,
        'percent': round((step_index / max(total_steps, 1)) * 100),
    }


def _get_progress_key(filename: str) -> str:
    """Derive a progress lookup key from the original or output filename."""
    key = filename.replace('.pptx.report.json', '').replace('.pptx', '')
    return key


@presentation_rewriter_bp.route('/progress/<filename>', methods=['GET'])
def get_progress(filename: str):
    """Poll endpoint for real-time processing progress."""
    key = _get_progress_key(filename)
    data = _progress_map.get(key)
    if data is None:
        # Check if the output file exists — if it does, progress is done
        try:
            get_download_path(filename)
            return jsonify({
                'success': True,
                'step_index': 100,
                'total_steps': 100,
                'percent': 100,
                'message': 'Complete',
                'done': True,
            }), 200
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'message': 'No progress information available for this file.',
            }), 404
    done = data['percent'] >= 100
    return jsonify({
        'success': True,
        'step_index': data['step_index'],
        'total_steps': data['total_steps'],
        'percent': data['percent'],
        'message': data['message'],
        'done': done,
    }), 200


# ─── Slide-by-Slide Report ──────────────────────────────────────────────────

@presentation_rewriter_bp.route('/report/<filename>', methods=['GET'])
def get_slide_report(filename: str):
    """Return the per-slide comparison report for a completed rewrite."""
    try:
        get_download_path(filename)  # verify file exists
    except FileNotFoundError:
        return _error('Presentation file not found. Please rewrite first.', 404)

    download_folder = ensure_download_folder()
    report = load_report_for_pptx(filename, download_folder)
    if not report:
        return _error('Slide-by-slide report is not available for this file.', 404)
    return jsonify({'success': True, 'report': report}), 200


# ─── PDF Report Download ────────────────────────────────────────────────────

@presentation_rewriter_bp.route('/report/<filename>/pdf', methods=['GET'])
def download_report_pdf(filename: str):
    """Generate and return a PDF of the detailed analysis report.

    The PDF includes: overall scores, slide-wise before/after comparison,
    grammar, spelling, readability, tone, and 7 Cs analysis.
    Uses the server-side report.json to render a text-based report.
    """
    try:
        get_download_path(filename)  # verify the PPTX exists
    except FileNotFoundError:
        return _error('Presentation file not found. Please rewrite first.', 404)

    download_folder = ensure_download_folder()
    report = load_report_for_pptx(filename, download_folder)
    if not report:
        return _error('Report data not available for PDF generation.', 404)

    try:
        pdf_bytes = _generate_report_pdf(report, filename)
        from io import BytesIO
        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=filename.replace('.pptx', '_report.pdf'),
            mimetype='application/pdf',
            max_age=0,
        )
    except Exception:
        logger.exception('[routes/rewriter] PDF report generation failed.')
        return _error('PDF report generation failed.', 500)


def _generate_report_pdf(report: dict, pptx_filename: str) -> bytes:
    """Build a text-structured PDF report using reportlab or a pure-FPDF fallback.

    Uses reportlab if available, otherwise falls back to a simple FPDF approach.
    """
    try:
        return _reportlab_pdf(report, pptx_filename)
    except ImportError:
        return _simple_pdf(report, pptx_filename)
    except Exception:
        return _simple_pdf(report, pptx_filename)


def _reportlab_pdf(report: dict, pptx_filename: str) -> bytes:
    """Generate PDF using reportlab (rich formatting)."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, ListFlowable, ListItem,
    )
    from reportlab.lib import colors

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Presentation Rewrite Report", styles['Title']))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"File: {pptx_filename}", styles['Normal']))
    story.append(Spacer(1, 4 * mm))

    # Quality scores
    qs = report.get('quality_scores', {})
    if qs:
        story.append(Paragraph(f"<b>Overall Score:</b> {qs.get('overall_score', 'N/A')}/100 — Grade {qs.get('grade', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("<b>Category Scores</b>", styles['Heading2']))
        cat_data = [['Category', 'Score']]
        for k, v in qs.get('category_scores', {}).items():
            cat_data.append([k, str(v)])
        t = Table(cat_data, colWidths=[120 * mm, 40 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # Per-slide comparison
    slides = report.get('slides', [])
    story.append(Paragraph(f"<b>Slide-by-Slide Comparison ({len(slides)} slides)</b>", styles['Heading2']))
    story.append(Spacer(1, 3 * mm))

    for slide in slides:
        sn = slide.get('slide_number', '?')
        title = slide.get('title', f'Slide {sn}')
        story.append(Paragraph(f"<b>Slide {sn}: {title}</b>", styles['Heading3']))
        story.append(Spacer(1, 2 * mm))

        for tb in slide.get('textboxes', []):
            orig_text = '\n'.join(tb.get('original_paragraphs', []))
            impr_text = '\n'.join(tb.get('improved_paragraphs', []))
            if orig_text == impr_text:
                continue
            story.append(Paragraph(f"<i>Textbox (shape {tb.get('shape_index', '?')}):</i>", styles['Normal']))
            story.append(Paragraph(f"<font color='#dc2626'>Original:</font> {orig_text[:300]}", styles['Normal']))
            story.append(Paragraph(f"<font color='#16a34a'>Improved:</font> {impr_text[:300]}", styles['Normal']))
            story.append(Spacer(1, 2 * mm))

        for table in slide.get('tables', []):
            story.append(Paragraph(f"<i>Table (shape {table.get('shape_index', '?')}):</i>", styles['Normal']))
            for cell in table.get('cells', []):
                orig = '\n'.join(cell.get('original_paragraphs', []))
                impr = '\n'.join(cell.get('improved_paragraphs', []))
                if orig != impr:
                    story.append(Paragraph(f"  Cell ({cell.get('row_index')},{cell.get('column_index')}): {orig[:100]} → {impr[:100]}", styles['Normal']))
            story.append(Spacer(1, 2 * mm))

        story.append(Spacer(1, 4 * mm))

    # 7 Cs
    if qs.get('seven_cs_scores'):
        story.append(Paragraph("<b>7 Cs of Communication</b>", styles['Heading2']))
        cs_data = [['Criterion', 'Score', 'Evaluation']]
        for k, v in qs.get('seven_cs_scores', {}).items():
            ev = qs.get('seven_cs_evaluation', {}).get(k, '')
            cs_data.append([k, str(v), ev[:100]])
        ct = Table(cs_data, colWidths=[40 * mm, 20 * mm, 110 * mm])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(ct)

    # Strengths & Recommendations
    if qs.get('strengths'):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>Strengths</b>", styles['Heading2']))
        for s in qs['strengths']:
            story.append(Paragraph(f"• {s}", styles['Normal']))
    if qs.get('recommendations'):
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("<b>Recommendations</b>", styles['Heading2']))
        for r in qs['recommendations']:
            story.append(Paragraph(f"• {r}", styles['Normal']))

    doc.build(story)
    return buf.getvalue()


def _simple_pdf(report: dict, pptx_filename: str) -> bytes:
    """Generate a plain-text PDF without reportlab."""
    try:
        from fpdf import FPDF
    except ImportError:
        # Ultra-minimal fallback: PDF manually constructed
        return _minimal_pdf(report, pptx_filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', size=10)

    # Title
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Presentation Rewrite Report', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=9)
    pdf.cell(0, 6, f'File: {pptx_filename}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)

    # Quality Score
    qs = report.get('quality_scores', {})
    if qs:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, f"Overall Score: {qs.get('overall_score', 'N/A')}/100 — Grade {qs.get('grade', 'N/A')}", new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 7, 'Category Scores:', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', size=9)
        for k, v in qs.get('category_scores', {}).items():
            pdf.cell(0, 5, f'  {k}: {v}/100', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(3)

        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 7, '7 Cs Scores:', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', size=9)
        for k, v in qs.get('seven_cs_scores', {}).items():
            pdf.cell(0, 5, f'  {k}: {v}/100', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(3)

    # Slide comparison
    slides = report.get('slides', [])
    if not pdf.page and slides:
        pdf.add_page()
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, f'Slide-by-Slide Comparison ({len(slides)} slides)', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    for slide in slides:
        sn = slide.get('slide_number', '?')
        title = slide.get('title', f'Slide {sn}')
        if pdf.y > 250:
            pdf.add_page()
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 7, f'Slide {sn}: {title}', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', size=8)

        for tb in slide.get('textboxes', []):
            orig = '\n'.join(tb.get('original_paragraphs', []))[:200]
            impr = '\n'.join(tb.get('improved_paragraphs', []))[:200]
            if orig != impr:
                pdf.multi_cell(0, 4, f'  [Textbox] Original: {orig}')
                pdf.multi_cell(0, 4, f'  [Textbox] Improved: {impr}')
                pdf.ln(1)

        for table in slide.get('tables', []):
            for cell in table.get('cells', []):
                orig = '\n'.join(cell.get('original_paragraphs', []))[:100]
                impr = '\n'.join(cell.get('improved_paragraphs', []))[:100]
                if orig != impr:
                    pdf.multi_cell(0, 4, f'  [Cell ({cell.get("row_index")},{cell.get("column_index")})] {orig} -> {impr}')
            pdf.ln(1)

        pdf.ln(2)

    # Strengths & Recommendations
    if qs.get('strengths') or qs.get('recommendations'):
        if pdf.y > 240:
            pdf.add_page()
        if qs.get('strengths'):
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 7, 'Strengths:', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', size=9)
            for s in qs['strengths']:
                pdf.multi_cell(0, 5, f'  - {s}')
            pdf.ln(2)
        if qs.get('recommendations'):
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 7, 'Recommendations:', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', size=9)
            for r in qs['recommendations']:
                pdf.multi_cell(0, 5, f'  - {r}')

    return bytes(pdf.output())


def _minimal_pdf(report: dict, pptx_filename: str) -> bytes:
    """Last-resort plain text wrapped in PDF boilerplate."""
    lines = [
        'Presentation Rewrite Report',
        f'File: {pptx_filename}',
        '',
    ]
    qs = report.get('quality_scores', {})
    if qs:
        lines.append(f"Overall Score: {qs.get('overall_score', 'N/A')}/100 — Grade {qs.get('grade', 'N/A')}")
        lines.append('')
        lines.append('Category Scores:')
        for k, v in qs.get('category_scores', {}).items():
            lines.append(f'  {k}: {v}/100')
        lines.append('')
        lines.append('7 Cs Scores:')
        for k, v in qs.get('seven_cs_scores', {}).items():
            lines.append(f'  {k}: {v}/100')
        lines.append('')

    slides = report.get('slides', [])
    lines.append(f'Slide-by-Slide Comparison ({len(slides)} slides)')
    lines.append('')
    for slide in slides:
        sn = slide.get('slide_number', '?')
        title = slide.get('title', f'Slide {sn}')
        lines.append(f'Slide {sn}: {title}')
        for tb in slide.get('textboxes', []):
            orig = '\n'.join(tb.get('original_paragraphs', []))[:200]
            impr = '\n'.join(tb.get('improved_paragraphs', []))[:200]
            if orig != impr:
                lines.append(f'  Original: {orig}')
                lines.append(f'  Improved: {impr}')
        for table in slide.get('tables', []):
            for cell in table.get('cells', []):
                orig = '\n'.join(cell.get('original_paragraphs', []))[:100]
                impr = '\n'.join(cell.get('improved_paragraphs', []))[:100]
                if orig != impr:
                    lines.append(f'  Cell ({cell.get("row_index")},{cell.get("column_index")}): {orig} -> {impr}')
        lines.append('')

    if qs.get('strengths'):
        lines.append('Strengths:')
        for s in qs['strengths']:
            lines.append(f'  - {s}')
        lines.append('')
    if qs.get('recommendations'):
        lines.append('Recommendations:')
        for r in qs['recommendations']:
            lines.append(f'  - {r}')
        lines.append('')

    text = '\n'.join(lines)
    # Basic PDF envelope
    pdf = (
        b'%PDF-1.4\n'
        b'1 0 obj\n'
        b'<< /Type /Catalog /Pages 2 0 R >>\n'
        b'endobj\n'
        b'2 0 obj\n'
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n'
        b'endobj\n'
        b'3 0 obj\n'
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n'
        b'   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n'
        b'endobj\n'
        b'4 0 obj\n'
        b'<< /Length ' + str(len(text) + 50).encode() + b' >>\n'
        b'stream\n'
        b'BT\n'
        b'/F1 10 Tf\n'
        b'50 750 Td\n'
    )
    for line in text.split('\n'):
        safe = line.replace('(', '\\(').replace(')', '\\)').replace('\\', '\\\\')
        pdf += f'({safe}) Tj\n0 -13 Td\n'.encode()
    pdf += (
        b'ET\n'
        b'endstream\n'
        b'endobj\n'
        b'5 0 obj\n'
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\n'
        b'endobj\n'
        b'xref\n'
        b'0 6\n'
        b'0000000000 65535 f \n'
        b'0000000009 00000 n \n'
        b'0000000058 00000 n \n'
        b'0000000115 00000 n \n'
        b'0000000266 00000 n \n'
        b'0000000369 00000 n \n'
        b'trailer\n'
        b'<< /Size 6 /Root 1 0 R >>\n'
        b'startxref\n'
        b'452\n'
        b'%%EOF\n'
    )
    return pdf
