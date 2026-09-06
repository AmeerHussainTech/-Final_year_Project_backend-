"""
Language Tool Service (Cloud API Edition)
Role: Grammar checking via LanguageTool's free public REST API.
No Java installation required — uses HTTP requests to api.languagetool.org.

The detected grammar issues are used to ENRICH the Gemini prompt so Gemini
knows exactly which mistakes to correct, producing higher-quality analysis
and rewrites.

Environment Variables:
  LANGUAGETOOL_API_URL  - Base URL (default: https://api.languagetool.org/v2)
  LANGUAGETOOL_API_KEY  - Optional premium API key (leave blank for free tier)
  LANGUAGETOOL_USERNAME - Optional premium username (leave blank for free tier)
  ENABLE_GRAMMAR_CHECK  - Set to '1' to enable (default: '1', always on with cloud API)
"""

import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
LANGUAGETOOL_API_URL = os.getenv(
    'LANGUAGETOOL_API_URL',
    'https://api.languagetool.org/v2'
).rstrip('/')

LANGUAGETOOL_API_KEY  = os.getenv('LANGUAGETOOL_API_KEY', '').strip()
LANGUAGETOOL_USERNAME = os.getenv('LANGUAGETOOL_USERNAME', '').strip()

# Cloud API is always available — no Java needed
_CLOUD_ENABLED = os.getenv('ENABLE_GRAMMAR_CHECK', '1').strip().lower() not in {'0', 'false', 'no', 'off'}

# Request timeout (seconds)
_TIMEOUT = 15


# ── Public API ────────────────────────────────────────────────────────────────

def check_grammar(text: str, language: str = 'en-US') -> list[dict]:
    """
    Send text to LanguageTool Cloud REST API and return a list of grammar issues:
      {
        "rule_id":      str,   # e.g. "COMMA_COMPOUND_SENTENCE"
        "category":     str,   # e.g. "PUNCTUATION"
        "message":      str,   # human-readable explanation
        "context":      str,   # the problematic snippet
        "offset":       int,   # character offset in original text
        "length":       int,   # length of the erroneous span
        "replacements": list[str]  # top-3 suggested fixes
      }

    Returns an empty list if the API is disabled, text is too short,
    or the request fails (graceful degradation).
    """
    if not _CLOUD_ENABLED:
        return []

    if not text or len(text.strip()) < 10:
        return []

    # ── Build request payload ─────────────────────────────────────────────────
    payload: dict = {
        'text':     text,
        'language': language,
    }

    # Attach premium credentials if provided
    if LANGUAGETOOL_API_KEY and LANGUAGETOOL_USERNAME:
        payload['apiKey']   = LANGUAGETOOL_API_KEY
        payload['username'] = LANGUAGETOOL_USERNAME

    # ── Call LanguageTool Cloud API ───────────────────────────────────────────
    try:
        response = requests.post(
            f'{LANGUAGETOOL_API_URL}/check',
            data=payload,
            timeout=_TIMEOUT,
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.warning('[language_tool_service] LanguageTool API timed out. Skipping grammar pre-pass.')
        return []
    except requests.exceptions.ConnectionError:
        logger.warning('[language_tool_service] LanguageTool API unreachable. Skipping grammar pre-pass.')
        return []
    except Exception as exc:
        logger.warning(f'[language_tool_service] Grammar check failed: {exc}')
        return []

    # ── Parse response ────────────────────────────────────────────────────────
    matches = data.get('matches', [])
    results = []
    for m in matches:
        rule       = m.get('rule', {})
        context    = m.get('context', {})
        replacements_raw = m.get('replacements', [])

        # Extract top-3 replacement suggestions
        suggestions = [r.get('value', '') for r in replacements_raw[:3] if r.get('value')]

        results.append({
            'rule_id':      rule.get('id', 'unknown'),
            'category':     rule.get('category', {}).get('name', ''),
            'message':      m.get('message', ''),
            'context':      context.get('text', ''),
            'offset':       m.get('offset', 0),
            'length':       m.get('length', 0),
            'replacements': suggestions,
        })

    logger.info(f'[language_tool_service] Found {len(results)} grammar issues via Cloud API.')
    return results


def summarise_grammar_issues(matches: list[dict], max_issues: int = 20) -> str:
    """
    Convert raw LanguageTool matches into a compact human-readable summary
    that can be appended to the Gemini prompt for enriched correction.

    Example output:
      The following specific grammar/spelling issues were detected:
        1. [COMMA_COMPOUND_SENTENCE] Use a comma before 'and' ... (context: "...") → suggest: ', and'
        2. [MORFOLOGIK_RULE_EN_US] Possible spelling mistake (context: "...") → suggest: 'their'
    """
    if not matches:
        return ''

    lines = ['The following specific grammar/spelling issues were detected:']
    for i, m in enumerate(matches[:max_issues], 1):
        rule_id  = m.get('rule_id') or 'unknown'
        category = m.get('category', '')
        message  = str(m.get('message', ''))
        context  = str(m.get('context', ''))
        fix = f" → suggest: '{m['replacements'][0]}'" if m.get('replacements') else ''

        # Truncate long context snippets
        if len(context) > 70:
            context = context[:70] + '…'

        cat_tag = f' [{category}]' if category else ''
        lines.append(f'  {i}. [{rule_id}]{cat_tag} {message} (context: "{context}"){fix}')

    if len(matches) > max_issues:
        lines.append(f'  … and {len(matches) - max_issues} more issues.')

    return '\n'.join(lines)


def grammar_score(matches: list[dict], word_count: int) -> int:
    """
    Convert raw grammar match count into a 0-100 grammar quality score.
    Penalises proportionally — more errors per word = lower score.

    Used to contribute to the 'Correct' dimension in the 7Cs scorecard.
    """
    if word_count <= 0:
        return 100
    if not matches:
        return 100

    # Error density: errors per 100 words
    error_density = (len(matches) / word_count) * 100

    # Score formula: starts at 100, loses 4 points per error per 100 words
    score = max(0, min(100, round(100 - (error_density * 4))))
    return score


def is_available() -> bool:
    """Return True if the grammar check cloud API is enabled."""
    return _CLOUD_ENABLED
