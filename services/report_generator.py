"""Report generation for per-slide comparison data and PDF export."""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _ensure_list(value, default=None):
    """Ensure a value is a list; convert None/int to empty list."""
    if isinstance(value, list):
        return value
    return default or []


def build_slide_report(original_slides: list[dict], rewritten_slides: list[dict]) -> list[dict]:
    """Pair original and rewritten slides into a per-slide comparison report.

    Each entry maps shape/slide structure from the Gemini-validated rewrite
    output back to the original extracted text so consumers can render a
    before/after diff.
    """
    report_slides = []
    for orig, rew in zip(original_slides, rewritten_slides):
        slide_report = {
            'slide_number': orig.get('slide_number'),
            'title': orig.get('title', ''),
            'textboxes': [],
            'tables': [],
            'charts': [],
        }

        # ── Textboxes ────────────────────────────────────────────────────
        orig_textboxes = {}
        for tb in _ensure_list(orig.get('textboxes')):
            if isinstance(tb, dict) and 'shape_index' in tb:
                orig_textboxes[tb['shape_index']] = tb
        for tb in _ensure_list(rew.get('textboxes')):
            if not isinstance(tb, dict):
                continue
            orig_tb = orig_textboxes.get(tb.get('shape_index'), {})
            slide_report['textboxes'].append({
                'shape_index': tb.get('shape_index'),
                'shape_name': orig_tb.get('shape_name', ''),
                'original_paragraphs': [
                    _para_text(p) for p in _ensure_list(orig_tb.get('paragraphs'))
                ],
                'improved_paragraphs': [str(p) for p in _ensure_list(tb.get('paragraphs'))],
            })

        # ── Tables (support both 'tables_data' and 'tables' keys) ────────
        orig_table_list = _ensure_list(orig.get('tables_data')) or _ensure_list(orig.get('tables'))
        orig_tables = {}
        for t in orig_table_list:
            if isinstance(t, dict) and 'shape_index' in t:
                orig_tables[t['shape_index']] = t
        for t in _ensure_list(rew.get('tables')):
            if not isinstance(t, dict):
                continue
            orig_t = orig_tables.get(t.get('shape_index'), {})
            orig_cells_map = {}
            for c in _ensure_list(orig_t.get('cells')):
                if isinstance(c, dict):
                    orig_cells_map[(c.get('row_index'), c.get('column_index'))] = c
            cells = []
            for c in _ensure_list(t.get('cells')):
                if not isinstance(c, dict):
                    continue
                orig_c = orig_cells_map.get((c.get('row_index'), c.get('column_index')), {})
                cells.append({
                    'row_index': c.get('row_index'),
                    'column_index': c.get('column_index'),
                    'original_paragraphs': [
                        _para_text(p) for p in _ensure_list(orig_c.get('paragraphs'))
                    ],
                    'improved_paragraphs': [str(p) for p in _ensure_list(c.get('paragraphs'))],
                })
            slide_report['tables'].append({
                'shape_index': t.get('shape_index'),
                'cells': cells,
            })

        # ── Charts (support both 'charts_data' and 'charts' keys) ────────
        orig_chart_list = _ensure_list(orig.get('charts_data')) or _ensure_list(orig.get('charts'))
        orig_charts = {}
        for c in orig_chart_list:
            if isinstance(c, dict) and 'shape_index' in c:
                orig_charts[c['shape_index']] = c
        for c in _ensure_list(rew.get('charts')):
            if not isinstance(c, dict):
                continue
            orig_c = orig_charts.get(c.get('shape_index'), {})
            slide_report['charts'].append({
                'shape_index': c.get('shape_index'),
                'original_title_paragraphs': [
                    _para_text(p) for p in _ensure_list(orig_c.get('title_paragraphs'))
                ],
                'improved_title_paragraphs': [str(p) for p in _ensure_list(c.get('title_paragraphs'))],
            })

        report_slides.append(slide_report)
    return report_slides


def _para_text(p) -> str:
    """Extract text from a paragraph dict or return the value as string."""
    if isinstance(p, dict):
        return str(p.get('text', ''))
    return str(p)


def save_report_json(
    report_data: dict,
    output_pptx_path: str,
) -> str:
    """Write a .report.json file alongside the PPTX output.

    Returns the path of the saved report file.
    """
    report_path = output_pptx_path + '.report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    logger.info("[report_generator] Saved report to '%s'.", report_path)
    return report_path


def load_report_json(filename: str, download_folder: str) -> dict | None:
    """Load a saved .report.json file by PPTX output filename."""
    base, _ = os.path.splitext(filename)
    report_path = os.path.join(download_folder, base + '.pptx.report.json')
    if not os.path.isfile(report_path):
        # Try alternate naming
        report_path = os.path.join(download_folder, filename + '.report.json')
    if not os.path.isfile(report_path):
        logger.warning("[report_generator] Report file not found for '%s'.", filename)
        return None
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("[report_generator] Failed to load report: %s", exc)
        return None


def load_report_for_pptx(output_filename: str, download_folder: str) -> dict | None:
    """Load report JSON using the output PPTX filename (no extra extension)."""
    return load_report_json(output_filename, download_folder)
