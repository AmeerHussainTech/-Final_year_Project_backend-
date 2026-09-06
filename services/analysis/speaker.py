"""
Speaker Readiness Analyzer

Analyzes presentation from a speaker's perspective:
- Speaking duration estimation
- Reading difficulty assessment (Flesch Reading Ease)
- Audience engagement prediction
- Confidence prediction
- Q&A preparedness scoring
- Speaker readiness score generation
"""

import logging
import math
import re
from typing import Optional

from services.config import (
    SPEAKING_WORDS_PER_MINUTE,
    SLOW_SPEAKING_WPM,
    FAST_SPEAKING_WPM,
    FLESCH_SCORES,
)

logger = logging.getLogger(__name__)


class SpeakerAnalyzer:
    """Analyzes speaker readiness from presentation content."""

    # Filler words that reduce engagement
    FILLER_PHRASES = [
        'basically', 'actually', 'literally', 'honestly', 'simply',
        'in order to', 'as you can see', 'it is important to note',
        'i think', 'maybe', 'sort of', 'kind of', 'you know',
        'as previously mentioned', 'as discussed earlier',
        'in this slide', 'in this presentation',
    ]

    QA_TRIGGER_WORDS = [
        'question', 'faq', 'qa', 'q&a', 'discussion', 'contact',
        'further information', 'learn more', 'resources',
        'thank you', 'questions', 'feedback',
    ]

    def analyze(self, slides: list[dict]) -> dict:
        """Analyze speaker readiness for the presentation.

        Args:
            slides: List of slide dicts.

        Returns:
            Dict with speaker readiness scores.
        """
        if not slides:
            return self._default()

        # Extract all text
        all_text_parts = []
        for slide in slides:
            for tb in slide.get('textboxes', []):
                for para in tb.get('paragraphs', []):
                    text = para.get('text', '') if isinstance(para, dict) else str(para)
                    if text.strip():
                        all_text_parts.append(text)

        full_text = ' '.join(all_text_parts)
        word_count = len(full_text.split())

        # ── Speaking Duration ──────────────────────────────────────────
        normal_duration_min = word_count / SPEAKING_WORDS_PER_MINUTE
        slow_duration_min = word_count / SLOW_SPEAKING_WPM
        fast_duration_min = word_count / FAST_SPEAKING_WPM

        # Add transition time between slides (~10 seconds per slide)
        transition_seconds = len(slides) * 10
        total_duration_normal_sec = int(normal_duration_min * 60 + transition_seconds)
        total_duration_slow_sec = int(slow_duration_min * 60 + transition_seconds)

        # ── Reading Difficulty ─────────────────────────────────────────
        flesch_score = self._compute_flesch_score(full_text)
        difficulty_level = self._get_difficulty_level(flesch_score)

        # ── Audience Engagement ────────────────────────────────────────
        engagement_score = self._compute_engagement_score(full_text, slides)

        # ── Confidence Prediction ──────────────────────────────────────
        filler_density = self._compute_filler_density(full_text)
        confidence_score = max(0, min(100, 100 - (filler_density * 100)))

        # ── Q&A Preparedness ───────────────────────────────────────────
        has_qa_slide = self._detect_qa_slide(slides)
        qa_preparedness = 80 if has_qa_slide else 40

        # ── Overall Speaker Readiness ──────────────────────────────────
        speaker_readiness = round(
            (engagement_score + confidence_score + qa_preparedness + self._reading_to_readiness(flesch_score)) / 4
        )

        # Recommendations
        recommendations = []
        if flesch_score < 50:
            recommendations.append("Simplify text for better audience comprehension — aim for shorter sentences.")
        if filler_density > 0.05:
            recommendations.append(f"Reduce filler phrases like '{', '.join(self.FILLER_PHRASES[:3])}'.")
        if not has_qa_slide:
            recommendations.append("Add a Q&A section to prepare for audience questions.")
        if confidence_score < 60:
            recommendations.append("Practice more to build confidence — text contains uncertain language.")
        if total_duration_normal_sec > 3600:
            recommendations.append(f"Consider shortening the presentation ({total_duration_normal_sec // 60} min estimated).")

        return {
            'speaker_readiness_score': speaker_readiness,
            'total_words': word_count,
            'flesch_reading_ease': round(flesch_score, 1),
            'difficulty_level': difficulty_level,
            'filler_phrase_count': int(filler_density * len(full_text.split())),
            'filler_density': round(filler_density, 4),
            'engagement_score': engagement_score,
            'confidence_score': confidence_score,
            'qa_preparedness': qa_preparedness,
            'has_qa_slide': has_qa_slide,
            'speaking_duration_normal': self._format_duration(total_duration_normal_sec),
            'speaking_duration_slow': self._format_duration(total_duration_slow_sec),
            'speaking_duration_normal_seconds': total_duration_normal_sec,
            'speaking_duration_slow_seconds': total_duration_slow_sec,
            'recommendations': recommendations,
        }

    def _compute_flesch_score(self, text: str) -> float:
        """Compute Flesch Reading Ease score."""
        if not text.strip():
            return 100.0

        words = text.split()
        word_count = len(words)
        if word_count < 3:
            return 90.0

        # Count syllables (simplified)
        syllable_count = 0
        for word in words[:200]:  # Sample first 200 words
            syllable_count += self._count_syllables(word)

        # Count sentences
        sentence_count = max(1, text.count('.') + text.count('!') + text.count('?'))

        avg_words_per_sentence = word_count / sentence_count
        avg_syllables_per_word = syllable_count / min(word_count, 200)

        score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
        return max(0, min(100, score))

    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        word = word.lower().strip('.,!?;:')
        if not word:
            return 0

        vowels = 'aeiouy'
        count = 0
        prev_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel

        # Ensure at least 1 syllable per word
        return max(1, count)

    def _get_difficulty_level(self, flesch_score: float) -> str:
        """Map Flesch score to difficulty level."""
        for level, (low, high) in FLESCH_SCORES.items():
            if low <= flesch_score <= high:
                return level.replace('_', ' ').title()
        return 'Standard'

    def _compute_engagement_score(self, text: str, slides: list[dict]) -> int:
        """Predict audience engagement based on content features."""
        score = 70  # Baseline

        # Variable sentence length = better engagement
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths:
                avg_len = sum(lengths) / len(lengths)
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                # Moderate variance indicates varied pacing
                if 10 < variance ** 0.5 < 25:
                    score += 10
                elif variance ** 0.5 > 30:
                    score -= 10

        # Questions engage audience
        question_count = text.count('?')
        if question_count >= 3:
            score += 10

        # Very long presentations lose engagement
        if len(slides) > 30:
            score -= 10
        elif len(slides) <= 10:
            score += 5

        return max(0, min(100, score))

    def _compute_filler_density(self, text: str) -> float:
        """Compute density of filler phrases in text."""
        if not text.strip():
            return 0.0

        lower_text = text.lower()
        filler_count = 0
        words = lower_text.split()
        total_words = len(words)

        for phrase in self.FILLER_PHRASES:
            filler_count += lower_text.count(phrase)

        return filler_count / max(total_words, 1)

    def _detect_qa_slide(self, slides: list[dict]) -> bool:
        """Detect if there's a Q&A or discussion slide."""
        for slide in slides:
            title = (slide.get('title', '') or '').lower()
            text = ' '.join(
                str(p.get('text', '') if isinstance(p, dict) else str(p))
                for tb in slide.get('textboxes', [])
                for p in tb.get('paragraphs', [])
            ).lower()

            combined = title + ' ' + text
            for trigger in self.QA_TRIGGER_WORDS:
                if trigger in combined:
                    return True
        return False

    def _reading_to_readiness(self, flesch_score: float) -> int:
        """Convert reading ease to a readiness contribution."""
        return min(100, max(0, int(flesch_score)))

    def _format_duration(self, seconds: int) -> str:
        """Format seconds to human-readable duration."""
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        if minutes < 60:
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m" if mins else f"{hours}h"

    def _default(self) -> dict:
        return {
            'speaker_readiness_score': 70,
            'total_words': 0,
            'flesch_reading_ease': 75.0,
            'difficulty_level': 'Fairly Easy',
            'filler_phrase_count': 0,
            'filler_density': 0.0,
            'engagement_score': 70,
            'confidence_score': 70,
            'qa_preparedness': 50,
            'has_qa_slide': False,
            'speaking_duration_normal': '0m',
            'speaking_duration_slow': '0m',
            'speaking_duration_normal_seconds': 0,
            'speaking_duration_slow_seconds': 0,
            'recommendations': [],
        }

