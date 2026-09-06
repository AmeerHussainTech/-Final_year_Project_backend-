"""
Analysis Package — Presentation Analysis Modules

Provides comprehensive analysis of presentations:
- statistics: Presentation statistics (word counts, reading time, etc.)
- holistic: Overall presentation understanding (topic, audience, etc.)
- per_slide: Per-slide quality scoring (grammar, tone, 7Cs, etc.)
- storytelling: Narrative structure and flow analysis
- design: Visual design assessment (balance, whitespace, etc.)
- consistency: Terminology and formatting consistency
- duplicate_detector: Repeated content detection
- accessibility: Accessibility analysis (contrast, text size, etc.)
- speaker: Speaker readiness assessment
"""

from services.analysis.statistics import compute_presentation_statistics, PresentationStatistics
from services.analysis.holistic import HolisticAnalyzer
from services.analysis.per_slide import PerSlideAnalyzer
from services.analysis.storytelling import StorytellingAnalyzer
from services.analysis.design import DesignAnalyzer
from services.analysis.consistency import ConsistencyAnalyzer
from services.analysis.duplicate_detector import DuplicateDetector
from services.analysis.accessibility import AccessibilityAnalyzer
from services.analysis.speaker import SpeakerAnalyzer
from services.analysis.context_verifier import verify_internal_context_consistency

__all__ = [
    "compute_presentation_statistics",
    "PresentationStatistics",
    "HolisticAnalyzer",
    "PerSlideAnalyzer",
    "StorytellingAnalyzer",
    "DesignAnalyzer",
    "ConsistencyAnalyzer",
    "DuplicateDetector",
    "AccessibilityAnalyzer",
    "SpeakerAnalyzer",
    "verify_internal_context_consistency",
]

