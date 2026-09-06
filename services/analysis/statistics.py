"""
Presentation Statistics Module

Computes quantitative statistics about a presentation:
- Slide count, word count, character count
- Textboxes, tables, charts, images per slide
- Reading time, speaking duration
- Text density, average bullets/slide
- Longest and shortest slides
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from services.config import (
    READING_WORDS_PER_MINUTE,
    SPEAKING_WORDS_PER_MINUTE,
    SECONDS_PER_SLIDE,
)

logger = logging.getLogger(__name__)


@dataclass
class SlideStatistics:
    """Per-slide statistics."""
    slide_number: int
    title: str
    word_count: int
    character_count: int
    textbox_count: int
    paragraph_count: int
    table_count: int
    chart_count: int
    image_count: int
    bullet_count: int
    longest_bullet_words: int
    average_bullet_words: float
    heading_length: int
    text_density: float  # characters per shape


@dataclass
class PresentationStatistics:
    """Complete presentation statistics."""
    slide_count: int
    total_words: int
    total_characters: int
    total_textboxes: int
    total_paragraphs: int
    total_tables: int
    total_charts: int
    total_images: int
    total_bullets: int
    average_words_per_slide: float
    longest_slide: int  # slide number
    longest_slide_words: int
    shortest_slide: int  # slide number
    shortest_slide_words: int
    reading_time_seconds: int
    reading_time_formatted: str
    speaking_time_seconds: int
    speaking_time_formatted: str
    estimated_presentation_duration_seconds: int
    estimated_presentation_duration_formatted: str
    text_density: float  # average characters per slide
    average_bullets_per_slide: float
    average_heading_length: float
    per_slide: list[SlideStatistics] = field(default_factory=list)


def _count_bullets(textboxes: list[dict]) -> int:
    """Count total bullet points (paragraphs) across all textboxes."""
    return sum(
        len(tb.get('paragraphs', []))
        for tb in textboxes
    )


def _get_longest_bullet_words(textbox: dict) -> int:
    """Find the longest paragraph in a textbox by word count."""
    max_words = 0
    for para in textbox.get('paragraphs', []):
        text = para.get('text', '') if isinstance(para, dict) else str(para)
        words = len(text.split())
        max_words = max(max_words, words)
    return max_words


def _get_average_bullet_words(textbox: dict) -> float:
    """Get average words per paragraph in a textbox."""
    paras = textbox.get('paragraphs', [])
    if not paras:
        return 0.0
    total = 0
    for para in paras:
        text = para.get('text', '') if isinstance(para, dict) else str(para)
        total += len(text.split())
    return total / len(paras)


def _format_duration(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m" if mins else f"{hours}h"


def _extract_text_from_slide(slide: dict) -> str:
    """Get all text content from a slide as a single string."""
    parts = []
    for tb in slide.get('textboxes', []):
        for para in tb.get('paragraphs', []):
            text = para.get('text', '') if isinstance(para, dict) else str(para)
            parts.append(text)
    for table in slide.get('tables_data', []):
        for cell in table.get('cells', []):
            for para in cell.get('paragraphs', []):
                text = para.get('text', '') if isinstance(para, dict) else str(para)
                parts.append(text)
    for chart in slide.get('charts_data', []):
        for para in chart.get('title_paragraphs', []):
            text = para.get('text', '') if isinstance(para, dict) else str(para)
            parts.append(text)
    return ' '.join(parts)


def compute_presentation_statistics(slides: list[dict]) -> PresentationStatistics:
    """Compute comprehensive statistics for a presentation.

    Args:
        slides: List of slide dicts from ppt_processor.extract_slides().

    Returns:
        PresentationStatistics dataclass with all computed stats.
    """
    total_words = 0
    total_chars = 0
    total_textboxes = 0
    total_paragraphs = 0
    total_tables = 0
    total_charts = 0
    total_images = 0
    total_bullets = 0

    per_slide_stats: list[SlideStatistics] = []
    longest_slide_num = 1
    longest_slide_words = 0
    shortest_slide_num = 1
    shortest_slide_words = float('inf')

    for slide in slides:
        slide_text = _extract_text_from_slide(slide)
        word_count = len(slide_text.split()) if slide_text else 0
        char_count = len(slide_text)
        tb_count = len(slide.get('textboxes', []))
        para_count = sum(
            len(tb.get('paragraphs', [])) for tb in slide.get('textboxes', [])
        )
        table_count = slide.get('tables', 0) or len(slide.get('tables_data', []))
        chart_count = slide.get('charts', 0) or len(slide.get('charts_data', []))
        image_count = slide.get('images', 0) or len(slide.get('images_data', []))
        bullet_count = _count_bullets(slide.get('textboxes', []))

        # Bullet measurements from first textbox with content
        longest_bullet = 0
        avg_bullet = 0.0
        for tb in slide.get('textboxes', []):
            lb = _get_longest_bullet_words(tb)
            longest_bullet = max(longest_bullet, lb)
            avg_bullet = _get_average_bullet_words(tb)
            if avg_bullet:
                break

        slide_stats = SlideStatistics(
            slide_number=slide.get('slide_number', 0),
            title=slide.get('title', ''),
            word_count=word_count,
            character_count=char_count,
            textbox_count=tb_count,
            paragraph_count=para_count,
            table_count=table_count,
            chart_count=chart_count,
            image_count=image_count,
            bullet_count=bullet_count,
            longest_bullet_words=longest_bullet,
            average_bullet_words=round(avg_bullet, 1),
            heading_length=len(slide.get('title', '')),
            text_density=round(char_count / max(tb_count, 1), 1),
        )
        per_slide_stats.append(slide_stats)

        # Accumulate totals
        total_words += word_count
        total_chars += char_count
        total_textboxes += tb_count
        total_paragraphs += para_count
        total_tables += table_count
        total_charts += chart_count
        total_images += image_count
        total_bullets += bullet_count

        # Track longest/shortest
        if word_count > longest_slide_words:
            longest_slide_words = word_count
            longest_slide_num = slide.get('slide_number', 1)
        if word_count < shortest_slide_words:
            shortest_slide_words = word_count
            shortest_slide_num = slide.get('slide_number', 1)

    slide_count = len(slides)
    avg_words = round(total_words / max(slide_count, 1), 1)
    reading_time_sec = max(1, math.ceil((total_words / READING_WORDS_PER_MINUTE) * 60))
    speaking_time_sec = max(1, math.ceil((total_words / SPEAKING_WORDS_PER_MINUTE) * 60))
    est_duration_sec = max(
        speaking_time_sec,
        slide_count * SECONDS_PER_SLIDE,
    )

    return PresentationStatistics(
        slide_count=slide_count,
        total_words=total_words,
        total_characters=total_chars,
        total_textboxes=total_textboxes,
        total_paragraphs=total_paragraphs,
        total_tables=total_tables,
        total_charts=total_charts,
        total_images=total_images,
        total_bullets=total_bullets,
        average_words_per_slide=avg_words,
        longest_slide=longest_slide_num,
        longest_slide_words=longest_slide_words,
        shortest_slide=shortest_slide_num,
        shortest_slide_words=shortest_slide_words if shortest_slide_words != float('inf') else 0,
        reading_time_seconds=reading_time_sec,
        reading_time_formatted=_format_duration(reading_time_sec),
        speaking_time_seconds=speaking_time_sec,
        speaking_time_formatted=_format_duration(speaking_time_sec),
        estimated_presentation_duration_seconds=est_duration_sec,
        estimated_presentation_duration_formatted=_format_duration(est_duration_sec),
        text_density=round(total_chars / max(slide_count, 1), 1),
        average_bullets_per_slide=round(total_bullets / max(slide_count, 1), 1),
        average_heading_length=round(
            sum(len(s.get('title', '')) for s in slides) / max(slide_count, 1), 1
        ),
        per_slide=per_slide_stats,
    )

