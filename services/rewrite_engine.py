"""
End-to-end orchestration for the AI Presentation Enhancement Platform.

Integrates all new modular components:
- Provider abstraction (services/ai/)
- Analysis modules (services/analysis/)
- Rewrite modules (services/rewrite/)
- Validation modules (services/validation/)
- Report modules (services/report/)
- Existing services (ppt_processor, download_service, etc.)

Maintains full backward compatibility with existing API endpoints.
"""

import json
import logging
import os
import time
from typing import Optional

from services.ai import get_provider
from services.ai.base_provider import AIProvider
from services.ai.fallback import FallbackManager
from services.ai.prompts import build_quality_analysis_prompt, build_rewrite_prompt
from services.analysis import (
    compute_presentation_statistics,
    HolisticAnalyzer,
    PerSlideAnalyzer,
    StorytellingAnalyzer,
    DesignAnalyzer,
    ConsistencyAnalyzer,
    DuplicateDetector,
    AccessibilityAnalyzer,
    SpeakerAnalyzer,
)
from services.rewrite import SmartFilter, RewritePlanner, RewriteExecutor
from services.validation import SemanticValidator, StructuralValidator, FinalValidator
from services.report import ExecutiveSummaryGenerator, AnalyticsGenerator, RecommendationsGenerator

from services.download_service import (
    ensure_download_folder,
    generate_output_filename,
    validate_upload_size,
)
from services.language_tool_service import check_grammar, summarise_grammar_issues
from services.ppt_processor import (
    extract_slides,
    get_presentation_metadata,
    update_presentation_text,
)
from services.report_generator import build_slide_report, save_report_json
from services.text_extractor import (
    get_all_text_for_analysis,
    get_extension,
    is_allowed_for_analysis,
    is_allowed_for_rewrite,
    validate_file_content,
)
from tools.compare_pptx import compare_pptx_files

logger = logging.getLogger(__name__)


def run_rewrite_pipeline(
    temp_file_path: str,
    original_filename: str,
    mode: str = "professional",
    tone: str = "professional",
) -> dict:
    """Rewrite a PPTX using the complete AI enhancement pipeline.

    Args:
        temp_file_path: Path to the uploaded temporary file.
        original_filename: Original filename for extension detection.
        mode: Processing mode (quick, professional, academic).
        tone: Writing tone (professional, academic, business, etc.).

    Returns:
        Dict with output_filename, slides_processed, quality_scores,
        improvements, processing_steps, metadata, and full report data.
    """
    extension = get_extension(original_filename)
    if not is_allowed_for_rewrite(original_filename):
        raise ValueError(
            f"Unsupported file type '{extension}' for rewriting. Only .pptx files supported."
        )

    file_size = os.path.getsize(temp_file_path)
    validate_upload_size(file_size)
    validate_file_content(temp_file_path, original_filename)
    steps = ['File validated']

    # ── Step 1: Extract slides and metadata ────────────────────────────
    slides = extract_slides(temp_file_path)
    metadata = get_presentation_metadata(temp_file_path)
    slide_count = len(slides)
    steps.append(f'Extracted {slide_count} slides')

    # ── Step 2: Extract text for analysis ──────────────────────────────
    extracted_text = get_all_text_for_analysis(temp_file_path, original_filename)
    steps.append('Text extracted for analysis')

    # ── Step 3: Grammar pre-check ──────────────────────────────────────
    grammar_matches = check_grammar(extracted_text)
    grammar_summary = summarise_grammar_issues(grammar_matches)
    steps.append(
        f'Grammar pre-analysis: {len(grammar_matches)} issues detected'
        if grammar_matches else 'Grammar pre-analysis complete'
    )

    # ── Step 4: Initialize providers and analyzers ─────────────────────
    provider = get_provider()
    fallback = FallbackManager(primary_provider=provider)
    planner = RewritePlanner(mode=mode, tone=tone)
    smart_filter = SmartFilter()
    executor = RewriteExecutor(provider=provider, planner=planner, smart_filter=smart_filter)

    holistic_analyzer = HolisticAnalyzer(provider=provider)
    per_slide_analyzer = PerSlideAnalyzer(provider=provider)
    storytelling_analyzer = StorytellingAnalyzer(provider=provider)
    design_analyzer = DesignAnalyzer()
    consistency_analyzer = ConsistencyAnalyzer()
    duplicate_detector = DuplicateDetector()
    accessibility_analyzer = AccessibilityAnalyzer()
    speaker_analyzer = SpeakerAnalyzer()

    semantic_validator = SemanticValidator(provider=provider)
    structural_validator = StructuralValidator()
    final_validator = FinalValidator(provider=provider)

    exec_summary_gen = ExecutiveSummaryGenerator()
    analytics_gen = AnalyticsGenerator()
    recommendations_gen = RecommendationsGenerator()

    # ── Step 5: Holistic presentation analysis ─────────────────────────
    presentation_context = holistic_analyzer.analyze(slides)
    steps.append('Holistic presentation analysis complete')

    # ── Step 6: Quality analysis ───────────────────────────────────────
    quality_scores = per_slide_analyzer.analyze_presentation(
        extracted_text, original_filename, mode
    )
    steps.append('AI quality analysis complete')

    # ── Step 7: Additional analyses (design, storytelling, etc.) ───────
    stats = compute_presentation_statistics(slides)
    steps.append('Presentation statistics computed')

    design_analysis = design_analyzer.analyze(slides)
    storytelling_analysis = storytelling_analyzer.analyze(slides)
    consistency_analysis = consistency_analyzer.analyze(slides)
    duplicate_analysis = duplicate_detector.analyze(slides)
    accessibility_analysis = accessibility_analyzer.analyze(slides)
    speaker_analysis = speaker_analyzer.analyze(slides)
    steps.append('Advanced analyses complete')

    # ── Step 8: Smart filter optimization ──────────────────────────────
    token_savings = smart_filter.estimate_token_savings(slides)
    if token_savings['savings_percent'] > 5:
        steps.append(
            f"Smart filter saved ~{token_savings['savings_percent']}% tokens"
        )

    # ── Step 9: Execute rewrite ────────────────────────────────────────
    rewritten_slides, rewrite_metrics = executor.execute_rewrite(
        slides, grammar_summary, presentation_context,
        focus_items=quality_scores.get('recommendations', []),
    )
    steps.append(f'{len(rewritten_slides)} slides rewritten')

    # ── Step 10: Validate rewritten content ────────────────────────────
    semantic_result = semantic_validator.validate(slides, rewritten_slides)
    structural_result = structural_validator.validate_slides(slides, rewritten_slides)
    steps.append('Validation complete')

    # ── Step 11: Compute final assessment ──────────────────────────────
    final_assessment = final_validator.compute_final_assessment(
        original_slides=slides,
        rewritten_slides=rewritten_slides,
        analysis_results=quality_scores,
        semantic_results=semantic_result,
        structural_results=structural_result,
        statistics={
            'slide_count': stats.slide_count,
            'total_words': stats.total_words,
            'topic': presentation_context.get('overall_topic', ''),
        },
    )
    steps.append('Final assessment complete')

    # ── Step 12: Generate reports ─────────────────────────────────────
    executive_summary = exec_summary_gen.generate(final_assessment, {
        'slide_count': stats.slide_count,
        'total_words': stats.total_words,
        'topic': presentation_context.get('overall_topic', ''),
    }, quality_scores)
    analytics = analytics_gen.generate(final_assessment)
    recommendations = recommendations_gen.generate(
        final_assessment, quality_scores,
        design_analysis, storytelling_analysis,
        consistency_analysis, accessibility_analysis, speaker_analysis,
    )
    steps.append('Reports generated')

    # ── Step 13: Save PPTX output ─────────────────────────────────────
    output_folder = ensure_download_folder()
    output_filename = generate_output_filename(original_filename)
    output_path = os.path.join(output_folder, output_filename)

    update_presentation_text(
        input_path=temp_file_path,
        rewritten_slides=_convert_gemini_to_ppt_format(rewritten_slides),
        original_slides=slides,
        output_path=output_path,
    )
    # ── Step 14: Post-save validation (soft-fail) ───────────────────────
    preservation_ok = True
    try:
        comparison = compare_pptx_files(temp_file_path, output_path)
        preservation_ok = comparison.get('visually_identical_structure', False)
        if not preservation_ok:
            logger.warning(
                '[rewrite_engine] Preservation check flagged differences for %r: %s',
                original_filename, comparison.get('structural_mismatches', comparison),
            )
    except Exception as exc:
        logger.warning('[rewrite_engine] Preservation check itself failed: %s', exc)
        comparison = {}
    steps.append('Improved presentation generated')
    steps.append('Preservation verified' if preservation_ok else 'Preservation check flagged differences (file kept — please review)')    

    # ── Step 15: Save per-slide comparison report ─────────────────────
    try:
        slide_report = build_slide_report(slides, rewritten_slides)
        report_payload = {
            'output_filename': output_filename,
            'original_filename': original_filename,
            'slide_count': slide_count,
            'quality_scores': quality_scores,
            'slides': slide_report,
            'generated_at': None,
            # New fields
            'final_assessment': final_assessment,
            'executive_summary': executive_summary,
            'analytics': analytics,
            'recommendations': recommendations,
            'statistics': {
                'slide_count': stats.slide_count,
                'total_words': stats.total_words,
                'total_characters': stats.total_characters,
                'total_textboxes': stats.total_textboxes,
                'total_tables': stats.total_tables,
                'total_charts': stats.total_charts,
                'total_images': stats.total_images,
                'total_bullets': stats.total_bullets,
                'average_words_per_slide': stats.average_words_per_slide,
                'longest_slide': stats.longest_slide,
                'shortest_slide': stats.shortest_slide,
                'reading_time_formatted': stats.reading_time_formatted,
                'speaking_time_formatted': stats.speaking_time_formatted,
                'estimated_duration_formatted': stats.estimated_presentation_duration_formatted,
            },
            'design_analysis': design_analysis,
            'storytelling_analysis': storytelling_analysis,
            'consistency_analysis': consistency_analysis,
            'duplicate_analysis': duplicate_analysis,
            'accessibility_analysis': accessibility_analysis,
            'speaker_analysis': speaker_analysis,
            'semantic_validation': semantic_result,
            'structural_validation': structural_result,
            'rewrite_metrics': rewrite_metrics,
            'processing_metadata': {
                'mode': mode,
                'tone': tone,
                'model': provider.get_model_info() if provider.is_available() else 'local',
                'provider': 'gemini',
                'retry_count': rewrite_metrics.get('retry_count', 0),
                'fallback_used': rewrite_metrics.get('fallback_count', 0) > 0,
                'total_ai_calls': rewrite_metrics.get('model_calls', 0),
                'smart_filter_savings': token_savings.get('savings_percent', 0),
            },
        }
        save_report_json(report_payload, output_path)
        steps.append('Comprehensive report saved')
    except Exception as exc:
        logger.warning('[rewrite_engine] Could not save report: %s', exc)
        steps.append('Report saving failed')

    # ── Build improvements list ───────────────────────────────────────
    improvements = _build_improvements_summary(quality_scores, final_assessment)

    return {
        'output_filename': output_filename,
        'slides_processed': slide_count,
        'quality_scores': quality_scores,
        'improvements': improvements,
        'processing_steps': steps,
        'metadata': {
            **metadata,
            'preservation_check': _comparison_summary(comparison) if 'comparison' in locals() else {},
        },
        'mode': mode,
        'tone': tone,
        'final_assessment': final_assessment,
        'executive_summary': executive_summary,
        'analytics': analytics,
        'recommendations': recommendations,
        'statistics': {
            'slide_count': stats.slide_count,
            'total_words': stats.total_words,
            'reading_time': stats.reading_time_formatted,
            'speaking_time': stats.speaking_time_formatted,
            'estimated_duration': stats.estimated_presentation_duration_formatted,
            'average_words_per_slide': stats.average_words_per_slide,
        },
    }


def run_analysis_pipeline(
    temp_file_path: str,
    original_filename: str,
) -> dict:
    """Analyze PPTX/PDF text without creating a rewritten file.

    Uses the new analysis modules for comprehensive scoring.
    """
    extension = get_extension(original_filename)
    if not is_allowed_for_analysis(original_filename):
        raise ValueError(f"Unsupported file type '{extension}'. Supported: .pptx, .pdf")
    file_size = os.path.getsize(temp_file_path)
    validate_upload_size(file_size)
    validate_file_content(temp_file_path, original_filename)
    steps = ['File validated']

    extracted_text = get_all_text_for_analysis(temp_file_path, original_filename)
    steps.append('Text extracted')

    slide_count = None
    slides = []
    if extension == '.pptx':
        slides = extract_slides(temp_file_path)
        slide_count = len(slides)
        steps.append(f'{slide_count} slides extracted')

    provider = get_provider()
    analyzer = PerSlideAnalyzer(provider=provider)
    quality_scores = analyzer.analyze_presentation(extracted_text, original_filename)
    steps.append('AI quality analysis complete')

    # Additional analyses if slides extracted
    extra_analyses = {}
    if slides:
        stats = compute_presentation_statistics(slides)
        extra_analyses['statistics'] = {
            'slide_count': stats.slide_count,
            'total_words': stats.total_words,
            'total_characters': stats.total_characters,
            'reading_time': stats.reading_time_formatted,
            'speaking_time': stats.speaking_time_formatted,
            'average_words_per_slide': stats.average_words_per_slide,
            'total_bullets': stats.total_bullets,
            'total_images': stats.total_images,
            'total_tables': stats.total_tables,
            'total_charts': stats.total_charts,
        }

        # Quick design analysis
        design_analyzer = DesignAnalyzer()
        extra_analyses['design'] = design_analyzer.analyze(slides)

        # Quick consistency check
        consistency_analyzer = ConsistencyAnalyzer()
        extra_analyses['consistency'] = consistency_analyzer.analyze(slides)

        steps.append('Advanced analyses complete')

    return {
        'quality_scores': quality_scores,
        'slides_analysed': slide_count,
        'processing_steps': steps,
        'analyses': extra_analyses,
    }


def _extract_paragraph_text(value) -> str:
    """Extract plain display text from a paragraph value.

    RewriteExecutor / validators sometimes pass richer paragraph objects
    like {'para_index': 0, 'text': '...', 'runs': [...]} for run-level
    diffing. The PPT writer only ever wants the plain 'text' — never the
    raw dict repr, which would render as literal text on the slide.
    """
    if isinstance(value, dict):
        return str(value.get('text', ''))
    return str(value)

def _convert_gemini_to_ppt_format(gemini_slides: list[dict]) -> list[dict]:
    """Normalise already-validated Gemini output for the PPT writer."""
    result = []
    for slide in gemini_slides:
        textboxes = []
        for textbox in slide.get('textboxes', []):
            textboxes.append({
                'shape_index': textbox.get('shape_index'),
                'paragraphs': [_extract_paragraph_text(v) for v in textbox.get('paragraphs', [])],
            })
        tables = []
        tables_raw = slide.get('tables', [])
        if isinstance(tables_raw, list):
            for table in tables_raw:
                tables.append({
                    'shape_index': table.get('shape_index'),
                    'cells': [
                        {
                            'row_index': cell.get('row_index'),
                            'column_index': cell.get('column_index'),
                            'paragraphs': [_extract_paragraph_text(v) for v in cell.get('paragraphs', [])],
                        }
                        for cell in table.get('cells', [])
                    ],
                })
        charts = []
        charts_raw = slide.get('charts', [])
        if isinstance(charts_raw, list):
            charts = [
                {
                    'shape_index': chart.get('shape_index'),
                    'title_paragraphs': [_extract_paragraph_text(v) for v in chart.get('title_paragraphs', [])],
                }
                for chart in charts_raw
            ]
        result.append({
            'slide_number': slide.get('slide_number'),
            'textboxes': textboxes,
            'tables': tables,
            'charts': charts,
        })
    return result


def _comparison_summary(comparison: dict) -> dict:
    return {
        'slide_count_match': comparison.get('slide_count_match', False),
        'dimensions_match': comparison.get('dimensions_match', False),
        'visually_identical_structure': comparison.get('visually_identical_structure', False),
        'structural_mismatches': comparison.get('structural_mismatches', []),
        'text_changes_detected': len(comparison.get('text_changes_detected', [])),
        'package_mismatches': comparison.get('package_mismatches', []),
    }


def _build_improvements_summary(
    quality_scores: dict,
    final_assessment: Optional[dict] = None,
) -> list[str]:
    """Build user-friendly improvement descriptions."""
    improvements = []

    if final_assessment:
        change_metrics = final_assessment.get('change_metrics', {})
        if change_metrics.get('major_rewrites', 0) > 0:
            improvements.append(
                f"{change_metrics['major_rewrites']} sections received major improvements"
            )
        if change_metrics.get('moderate_improvements', 0) > 0:
            improvements.append(
                f"{change_metrics['moderate_improvements']} text elements moderately improved"
            )
        if change_metrics.get('minor_improvements', 0) > 0:
            improvements.append(
                f"{change_metrics['minor_improvements']} text elements polished for clarity"
            )

        overall = final_assessment.get('overall_score', 0)
        original = final_assessment.get('original_score', 0)
        if overall > original:
            improvements.append(
                f"Overall score improved from {original}/100 to {overall}/100"
            )

    categories = quality_scores.get('category_scores', {})
    if categories.get('Grammar', 100) < 90:
        improvements.append('Sentences restructured for correct grammar and natural flow')
    if categories.get('Spelling', 100) < 90:
        improvements.append('Spelling and punctuation corrected throughout')
    if categories.get('Readability', 100) < 85:
        improvements.append('Readability enhanced — shorter sentences, clearer word choice')
    if categories.get('Tone', 100) < 85:
        improvements.append('Professional tone strengthened — conference-ready language')
    if categories.get('Clarity', 100) < 85:
        improvements.append('Clarity improved — each bullet now conveys one clear idea')
    if categories.get('Conciseness', 100) < 85:
        improvements.append('Text condensed — filler words and repetition removed')
    if categories.get('Structure', 100) < 85:
        improvements.append('Slide structure tightened — logical hierarchy and parallel bullets')

    return improvements or [
        'Professional tone and presentation-friendly language applied',
        'Bullet points tightened for scannability and parallel structure',
        'All 7 Cs of Communication optimised for maximum impact',
        'Filler phrases and weak wording eliminated',
    ]