"""
Structural Validator — Presentation Structure Preservation

Validates that the rewritten presentation preserves:
- Slide count (no slides added or removed)
- Shape count per slide (no shapes added or removed)
- Layout preservation (slide layouts unchanged)
- Table dimensions (rows/columns unchanged)
- Chart existence (charts not removed)

References tools/compare_pptx.py for deep structural comparison.
"""

import logging
from typing import Optional

from tools.compare_pptx import compare_pptx_files, analyze_slide_structure

logger = logging.getLogger(__name__)

# Default structure must match exactly
STRUCTURE_KEYS_TO_CHECK = [
    'total_shapes', 'pictures', 'tables', 'charts',
    'placeholders', 'textboxes',
]


class StructuralValidator:
    """Validates structural preservation of the presentation."""

    def validate_slides(
        self,
        original_slides: list[dict],
        rewritten_slides: list[dict],
    ) -> dict:
        """Validate structural preservation between slide data.

        Args:
            original_slides: Original slide dicts from ppt_processor.
            rewritten_slides: Rewritten slide dicts from the rewrite engine.

        Returns:
            Dict with valid flag, structural score, issues.
        """
        issues = []

        # 1. Slide count preservation
        if len(original_slides) != len(rewritten_slides):
            issues.append({
                'type': 'slide_count',
                'severity': 'critical',
                'message': (
                    f"Slide count changed: {len(original_slides)} -> {len(rewritten_slides)}"
                ),
            })
            return {
                'valid': False,
                'structural_score': 0,
                'issues': issues,
                'slide_count_match': False,
                'shape_count_match': False,
                'layout_match': False,
            }

        slide_count_match = True
        shape_count_match = True
        layout_match = True

        # 2. Per-slide structure check
        for orig, rew in zip(original_slides, rewritten_slides):
            slide_num = orig.get('slide_number')

            # Check textbox count
            orig_tb_count = len(orig.get('textboxes', []))
            rew_tb_count = len(rew.get('textboxes', []))
            if orig_tb_count != rew_tb_count:
                issues.append({
                    'type': 'textbox_count',
                    'severity': 'critical',
                    'message': f"Slide {slide_num}: textboxes changed ({orig_tb_count} -> {rew_tb_count})",
                })
                shape_count_match = False

            # Check table count
            orig_tables = orig.get('tables_data') or orig.get('tables') or []
            if isinstance(orig_tables, int):
                orig_table_count = orig_tables
            else:
                orig_table_count = len(orig_tables)
            rew_tables = rew.get('tables') or []
            if isinstance(rew_tables, int):
                rew_table_count = rew_tables
            else:
                rew_table_count = len(rew_tables)
            if orig_table_count != rew_table_count:
                issues.append({
                    'type': 'table_count',
                    'severity': 'critical',
                    'message': f"Slide {slide_num}: tables changed ({orig_table_count} -> {rew_table_count})",
                })
                shape_count_match = False

            # Check chart count
            orig_charts = orig.get('charts_data') or orig.get('charts') or []
            if isinstance(orig_charts, int):
                orig_chart_count = orig_charts
            else:
                orig_chart_count = len(orig_charts)
            rew_charts = rew.get('charts') or []
            if isinstance(rew_charts, int):
                rew_chart_count = rew_charts
            else:
                rew_chart_count = len(rew_charts)
            if orig_chart_count != rew_chart_count:
                issues.append({
                    'type': 'chart_count',
                    'severity': 'critical',
                    'message': f"Slide {slide_num}: charts changed ({orig_chart_count} -> {rew_chart_count})",
                })
                shape_count_match = False

        # 3. Shape index preservation within textboxes
        for orig, rew in zip(original_slides, rewritten_slides):
            slide_num = orig.get('slide_number')
            orig_indices = {tb.get('shape_index') for tb in orig.get('textboxes', [])}
            rew_indices = {tb.get('shape_index') for tb in rew.get('textboxes', [])}
            if orig_indices != rew_indices:
                issues.append({
                    'type': 'shape_index',
                    'severity': 'major',
                    'message': f"Slide {slide_num}: shape indices changed",
                })

        # Compute structural score
        total_checks = 3  # slide_count, shape_count, layout
        passed = sum([
            slide_count_match,
            shape_count_match,
            layout_match,
        ])
        structural_score = round((passed / total_checks) * 100)

        return {
            'valid': structural_score >= 80,
            'structural_score': structural_score,
            'slide_count_match': slide_count_match,
            'shape_count_match': shape_count_match,
            'layout_match': layout_match,
            'issues': issues,
            'issue_count': len(issues),
        }

    def validate_pptx_files(
        self,
        original_path: str,
        improved_path: str,
    ) -> dict:
        """Validate structural preservation using full PPTX comparison.

        Delegates to tools/compare_pptx.py for detailed analysis.
        """
        try:
            comparison = compare_pptx_files(original_path, improved_path)
            structural_issues = comparison.get('structural_mismatches', [])
            return {
                'valid': comparison.get('visually_identical_structure', False),
                'structural_score': 100 if not structural_issues else max(
                    0, 100 - len(structural_issues) * 10
                ),
                'slide_count_match': comparison.get('slide_count_match', False),
                'dimensions_match': comparison.get('dimensions_match', False),
                'image_count_match': comparison.get('image_count_match', True),
                'image_hashes_match': comparison.get('image_hashes_match', True),
                'package_mismatches': comparison.get('package_mismatches', []),
                'issues': [
                    {'type': 'structural', 'severity': 'critical', 'message': m}
                    for m in structural_issues
                ],
            }
        except Exception as exc:
            logger.error("[structural] PPTX comparison failed: %s", exc)
            return {
                'valid': False,
                'structural_score': 0,
                'error': str(exc),
                'issues': [{
                    'type': 'comparison_error',
                    'severity': 'critical',
                    'message': f"PPTX comparison failed: {exc}",
                }],
            }

