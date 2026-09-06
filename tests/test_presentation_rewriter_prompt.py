import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.gemini_service import build_rewrite_prompt as build_gemini_prompt


def test_build_gemini_prompt_handles_json_example_without_format_errors():
    slides = [
        {
            "slide_number": 1,
            "title": "Intro",
            "title_shape_index": 0,
            "textboxes": [
                {"shape_index": 3, "text": "Hello world"}
            ],
            "shape_count": 4,
        }
    ]

    prompt = build_gemini_prompt(slides)

    assert "Expected JSON format:" in prompt
    assert '"shape_index": 3' in prompt
    assert '"text": "Improved text"' in prompt
