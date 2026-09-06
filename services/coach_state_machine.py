"""
Dr. Alexander Vance AI Coach State Machine
"""

import logging
from typing import Dict, Any, Tuple
from services.coach_templates import COACH_RESPONSES

logger = logging.getLogger(__name__)


def transition_state(current_state: str, intent: str) -> Tuple[str, str]:
    """
    Transition conversation state based on detected user intent.

    States: INIT -> OVERVIEW -> VIVA_PRACTICE | METRICS_REVIEW | GENERAL_COACHING
    """
    next_state = current_state

    if intent == "greeting":
        next_state = "OVERVIEW"
    elif intent == "viva_prep":
        next_state = "VIVA_PRACTICE"
    elif intent in ["slide_feedback", "pacing_question", "disfluency_query"]:
        next_state = "METRICS_REVIEW"
    else:
        next_state = "GENERAL_COACHING"

    response_text = COACH_RESPONSES.get(intent, COACH_RESPONSES["general_help"])
    return response_text, next_state
