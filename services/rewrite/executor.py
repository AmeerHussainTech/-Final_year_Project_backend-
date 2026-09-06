"""
Rewrite Executor — Batched Rewrite Execution

Executes rewrite operations with:
- Three-level batching (analysis, rewrite, validation)
- Rolling summaries between batches
- Per-slide error recovery
- Change severity classification
- Performance metrics collection
"""

import json
import logging
import time
from typing import Callable, Optional

from services.ai import get_provider
from services.ai.base_provider import AIProvider
from services.ai.fallback import FallbackManager
from services.ai.prompts import build_rewrite_prompt
from services.rewrite.planner import RewritePlanner
from services.rewrite.smart_filter import SmartFilter

logger = logging.getLogger(__name__)

# Severity thresholds
SEVERITY_HIGH_CHANGE_RATIO = 0.5  # >50% text changed = major rewrite
SEVERITY_MODERATE_CHANGE_RATIO = 0.2  # >20% = moderate


class RewriteExecutor:
    """Executes slide rewriting with batching, fallback, and metrics."""

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        planner: Optional[RewritePlanner] = None,
        smart_filter: Optional[SmartFilter] = None,
    ):
        self.provider = provider or get_provider()
        self.planner = planner or RewritePlanner()
        self.smart_filter = smart_filter or SmartFilter()
        self.metrics: dict = {
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'model_calls': 0,
            'retry_count': 0,
            'fallback_count': 0,
            'slides_rewritten': 0,
            'slides_skipped': 0,
            'batches_processed': 0,
            'total_batches': 0,
        }

    def execute_rewrite(
        self,
        slides: list[dict],
        grammar_issues_summary: str = "",
        presentation_context: Optional[dict] = None,
        focus_items: Optional[list[str]] = None,
    ) -> tuple[list[dict], dict]:
        """Execute the full rewrite pipeline.

        Args:
            slides: List of slide dicts to rewrite.
            grammar_issues_summary: Pre-computed grammar issues.
            presentation_context: Optional holistic context.
            focus_items: Pre-analysis recommendations (e.g.
                quality_scores['recommendations']) the rewrite must address.

        Returns:
            Tuple of (rewritten_slides, execution_metrics).
        """
        self.metrics['start_time'] = time.time()

        # Step 1: Smart filter to identify what needs rewriting
        to_rewrite, to_skip = self.smart_filter.filter_slides(slides)
        self.metrics['slides_rewritten'] = len(to_rewrite)
        self.metrics['slides_skipped'] = len(to_skip)

        if not to_rewrite:
            logger.info("[executor] No slides need rewriting; returning originals.")
            self._finalize_metrics()
            return slides, self.metrics

        # Step 2: Plan batches
        batches = self.planner.plan_batches(to_rewrite)
        self.metrics['total_batches'] = len(batches)

        # Step 3: Execute batches
        all_rewritten = []
        for batch in batches:
            rewritten = self._execute_batch(
                batch['slides'],
                grammar_issues_summary,
                presentation_context,
                batch['batch_index'],
                batch['context_summary'],
                focus_items,
            )
            all_rewritten.extend(rewritten)
            self.metrics['batches_processed'] += 1

        self._finalize_metrics()
        logger.info(
            "[executor] Rewrote %d slides in %d batches (%.1fs)",
            len(to_rewrite), len(batches), self.metrics['total_duration'],
        )

        return all_rewritten, self.metrics

    def _execute_batch(
        self,
        batch_slides: list[dict],
        grammar_issues_summary: str,
        presentation_context: Optional[dict],
        batch_index: int,
        context_summary: Optional[str] = None,
        focus_items: Optional[list[str]] = None,
    ) -> list[dict]:
        """Execute rewrite for a single batch of slides.

        Uses fallback manager for per-slide error recovery.
        """
        rewritten = []

        for idx, slide in enumerate(batch_slides):
            slide_num = slide.get('slide_number')
            try:
                result = self._rewrite_single_slide(
                    slide, grammar_issues_summary, presentation_context, focus_items
                )
                if result:
                    result['_change_severity'] = self._classify_severity(slide, result)
                    rewritten.append(result)
                else:
                    # Fallback: return original
                    rewritten.append({
                        'slide_number': slide_num,
                        'textboxes': [
                            {
                                'shape_index': tb.get('shape_index'),
                                'paragraphs': [
                                    p.get('text', '') if isinstance(p, dict) else str(p)
                                    for p in tb.get('paragraphs', [])
                                ],
                            }
                            for tb in slide.get('textboxes', [])
                        ],
                        'tables': [],
                        'charts': [],
                        '_fallback': True,
                        '_change_severity': 'none',
                    })
                    self.metrics['fallback_count'] += 1

            except Exception as exc:
                logger.error(
                    "[executor] Slide %d rewrite failed: %s", slide_num, exc
                )
                rewritten.append({
                    'slide_number': slide_num,
                    'textboxes': [
                        {
                            'shape_index': tb.get('shape_index'),
                            'paragraphs': [
                                p.get('text', '') if isinstance(p, dict) else str(p)
                                for p in tb.get('paragraphs', [])
                            ],
                        }
                        for tb in slide.get('textboxes', [])
                    ],
                    'tables': [],
                    'charts': [],
                    '_fallback': True,
                    '_error': str(exc),
                    '_change_severity': 'none',
                })
                self.metrics['fallback_count'] += 1

        return rewritten

    def _rewrite_single_slide(
        self,
        slide: dict,
        grammar_issues_summary: str,
        presentation_context: Optional[dict],
        focus_items: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Rewrite a single slide using the AI provider.

        Returns the rewritten slide dict, or None for fallback.
        """
        # Build prompt for this slide
        prompt = build_rewrite_prompt(
            [slide],
            grammar_issues_summary,
            presentation_context,
            mode=self.planner.mode,
            tone=self.planner.tone,
            focus_items=focus_items,
        )

        # Call provider
        try:
            result = self.provider.generate_structured(
                prompt=prompt,
                temperature=0.3,
                max_output_tokens=4096,
            )
            self.metrics['model_calls'] += 1

            if isinstance(result, dict) and 'slides' in result:
                slides_result = result.get('slides', [])
                if slides_result:
                    return slides_result[0]
        except Exception as exc:
            logger.warning(
                "[executor] Single slide rewrite failed: %s", exc
            )
            self.metrics['retry_count'] += 1

        return None

    def _classify_severity(
        self,
        original_slide: dict,
        rewritten_slide: dict,
    ) -> str:
        """Classify the severity of changes made to a slide.

        Returns 'minor', 'moderate', or 'major'.
        """
        changes = 0
        total = 0

        for orig_tb in original_slide.get('textboxes', []):
            orig_texts = [
                p.get('text', '') if isinstance(p, dict) else str(p)
                for p in orig_tb.get('paragraphs', [])
            ]
            for rew_tb in rewritten_slide.get('textboxes', []):
                if rew_tb.get('shape_index') == orig_tb.get('shape_index'):
                    rew_texts = [str(p) for p in rew_tb.get('paragraphs', [])]
                    for o, r in zip(orig_texts, rew_texts):
                        total += 1
                        if o.strip() != r.strip():
                            changes += 1
                    break

        if total == 0:
            return 'none'

        change_ratio = changes / total
        if change_ratio >= SEVERITY_HIGH_CHANGE_RATIO:
            return 'major'
        elif change_ratio >= SEVERITY_MODERATE_CHANGE_RATIO:
            return 'moderate'
        return 'minor'

    def _finalize_metrics(self) -> None:
        """Finalize execution metrics."""
        self.metrics['end_time'] = time.time()
        self.metrics['total_duration'] = round(
            self.metrics['end_time'] - self.metrics['start_time'], 2
        )
        # Remove internal timestamps for cleaner output
        clean = {k: v for k, v in self.metrics.items()
                 if k not in ('start_time', 'end_time')}
        self.metrics = clean

