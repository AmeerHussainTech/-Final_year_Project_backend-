"""
Per-Slide Quality Analyzer

Analyzes each slide individually for:
- Grammar and spelling quality (via LanguageTool Cloud API)
- Readability and tone
- Clarity and conciseness
- 7 Cs of Communication scores
- Strengths and issues per slide
"""

import json
import logging
from typing import Optional

from services.ai import get_provider
from services.ai.base_provider import AIProvider
from services.ai.prompts import build_quality_analysis_prompt
from services.language_tool_service import (
    check_grammar,
    grammar_score as lt_grammar_score,
)

logger = logging.getLogger(__name__)


class PerSlideAnalyzer:
    """Analyzes quality of individual slides and the overall presentation."""

    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or get_provider()

    def analyze_presentation(
        self,
        text: str,
        filename: str = "",
        mode: str = "professional",
    ) -> dict:
        """Analyze the full presentation text for quality.

        Runs a LanguageTool Cloud grammar pre-pass first so that Grammar,
        Spelling, and the 'Correct' 7Cs dimension are scored with real data.

        Args:
            text: Full presentation text.
            filename: Original filename for context.
            mode: Processing mode (quick, professional, academic).

        Returns:
            Dict with quality scores, 7Cs, strengths, issues, recommendations.
        """
        if not text or len(text.strip()) < 10:
            return self._default_scores()

        # ── Grammar pre-pass (LanguageTool Cloud) ─────────────────────────
        grammar_issues: list[dict] = []
        computed_grammar_score: int = 100
        try:
            grammar_issues = check_grammar(text)
            computed_grammar_score = lt_grammar_score(grammar_issues, len(text.split()))
            logger.info(
                "[per_slide] LanguageTool: %d issues, grammar score=%d",
                len(grammar_issues), computed_grammar_score,
            )
        except Exception as exc:
            logger.warning("[per_slide] Grammar pre-pass failed: %s", exc)

        if self.provider and self.provider.is_available():
            try:
                prompt = build_quality_analysis_prompt(
                    text, filename, mode,
                    grammar_issues=grammar_issues,
                    grammar_score=computed_grammar_score,
                )
                result = self.provider.generate_structured(
                    prompt=prompt,
                    temperature=0.2,
                    max_output_tokens=4096,
                )
                if isinstance(result, dict) and 'overall_score' in result:
                    normalized = self._normalize(result)
                    # Override grammar-related scores with LanguageTool's
                    # authoritative values so they cannot be hallucinated.
                    normalized.setdefault('category_scores', {})['Grammar'] = computed_grammar_score
                    normalized['category_scores']['Spelling'] = computed_grammar_score
                    normalized.setdefault('seven_cs_scores', {})['Correct'] = computed_grammar_score
                    normalized['grammar_issues'] = grammar_issues
                    normalized['grammar_issues_count'] = len(grammar_issues)
                    normalized['grammar_score'] = computed_grammar_score
                    return normalized
            except Exception as exc:
                logger.warning("[per_slide] AI analysis failed: %s", exc)

        # Fallback with grammar data injected
        fallback = self._default_scores()
        fallback['category_scores']['Grammar'] = computed_grammar_score
        fallback['category_scores']['Spelling'] = computed_grammar_score
        fallback['seven_cs_scores']['Correct'] = computed_grammar_score
        fallback['grammar_issues'] = grammar_issues
        fallback['grammar_issues_count'] = len(grammar_issues)
        fallback['grammar_score'] = computed_grammar_score
        return fallback

    def analyze_slide(self, slide: dict) -> dict:
        """Analyze a single slide's text content.

        Args:
            slide: Single slide dict.

        Returns:
            Dict with per-slide quality metrics.
        """
        text = self._get_slide_text(slide)
        word_count = len(text.split())
        char_count = len(text)
        tb_count = len(slide.get('textboxes', []))

        return {
            'slide_number': slide.get('slide_number'),
            'title': slide.get('title', ''),
            'word_count': word_count,
            'character_count': char_count,
            'textbox_count': tb_count,
            'has_content': word_count > 0,
            'readability_score': self._estimate_readability(text),
            'has_grammar_issues': self._has_grammar_issues(text),
            'text_density': round(char_count / max(tb_count, 1), 1),
        }

    def _get_slide_text(self, slide: dict) -> str:
        """Extract all text from a slide."""
        parts = []
        for tb in slide.get('textboxes', []):
            for para in tb.get('paragraphs', []):
                text = para.get('text', '') if isinstance(para, dict) else str(para)
                parts.append(text)
        return ' '.join(parts)

    def _estimate_readability(self, text: str) -> float:
        """Estimate readability score (0-100) using Flesch-like heuristics.

        Higher scores mean easier to read.
        """
        if not text.strip():
            return 100.0

        words = text.split()
        word_count = len(words)
        if word_count < 3:
            return 90.0

        # Count syllables (heuristic)
        syllable_count = sum(
            sum(1 for c in word.lower() if c in 'aeiou')
            for word in words[:100]
        )

        # Count sentences
        sentence_count = max(1, text.count('.') + text.count('!') + text.count('?'))

        # Flesch Reading Ease: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        avg_words_per_sentence = word_count / sentence_count
        avg_syllables_per_word = syllable_count / max(word_count, 1)

        score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
        return max(0, min(100, round(score, 1)))

    def _has_grammar_issues(self, text: str) -> bool:
        """Check for grammar issues using LanguageTool Cloud API.

        Falls back to simple heuristics if the API is unavailable.
        """
        try:
            issues = check_grammar(text)
            return len(issues) > 0
        except Exception:
            pass

        # Heuristic fallback
        issues = 0
        if '  ' in text:
            issues += 1
        for sentence in text.split('.'):
            s = sentence.strip()
            if s and s[0].islower():
                issues += 1
        for sentence in text.split('.'):
            if len(sentence.split()) > 40:
                issues += 1
        return issues > 0

    def _normalize(self, result: dict) -> dict:
        """Ensure all expected keys are present in the result."""
        defaults = self._default_scores()
        defaults.update(result)
        return defaults

    def _default_scores(self) -> dict:
        """Return default/neutral scores when analysis is unavailable."""
        return {
            'overall_score': 75,
            'grade': 'B',
            'summary': 'Quality analysis could not be completed by AI. Default scores shown.',
            'category_scores': {
                'Grammar': 75,
                'Spelling': 80,
                'Readability': 75,
                'Tone': 75,
                'Clarity': 70,
                'Conciseness': 70,
                'Structure': 72,
            },
            'seven_cs_scores': {
                'Clear': 75, 'Concise': 70, 'Correct': 75,
                'Complete': 70, 'Concrete': 65, 'Coherent': 72, 'Courteous': 78,
            },
            'seven_cs_evaluation': {
                'Clear': 'Analysis unavailable.',
                'Concise': 'Analysis unavailable.',
                'Correct': 'Analysis unavailable.',
                'Complete': 'Analysis unavailable.',
                'Concrete': 'Analysis unavailable.',
                'Coherent': 'Analysis unavailable.',
                'Courteous': 'Analysis unavailable.',
            },
            'strengths': ['Presentation has been processed'],
            'issues_found': ['Detailed AI analysis was not available'],
            'recommendations': ['Upload with a configured AI provider for detailed recommendations'],
        }

