"""
Phase Five: AI Coach / Practice Mode Blueprint
Role: Provide real-time local AI coaching for presentation practice and feedback.

Key Features:
- Multi-turn conversational intent classification using TF-IDF + Logistic Regression
- Dr. Alexander Vance finite-state machine persona
- Context-aware coaching based on document analysis reports
- Grammar analysis via LanguageTool
"""

import os
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
from services.language_tool_service import (
    check_grammar,
    summarise_grammar_issues,
    grammar_score as lt_grammar_score,
)
from services.coach_intent_engine import process_coach_chat, predict_intent
from services.coach_state_machine import transition_state
from services.coach_templates import COACH_RESPONSES

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()



# Create a blueprint for AI coach / practice mode
phase_five_bp = Blueprint('phase_five', __name__, url_prefix='/api')


def format_chat_history(frontend_history: list) -> list:
    """
    Convert frontend chat history format to Gemini-compatible format.
    
    Frontend format: { "role": "user"|"ai", "content": "..." }
    Gemini format: { "role": "user"|"model", "parts": [{ "text": "..." }] }
    
    Args:
        frontend_history: List of chat messages from frontend
        
    Returns:
        List of chat messages in Gemini format
    """
    gemini_history = []

    for msg in frontend_history:
        # Map frontend role names to Gemini role names
        # "ai" role becomes "model" in Gemini API
        role = "model" if msg.get("role") == "ai" else msg.get("role", "user")

        gemini_message = {
            "role": role,
            "parts": [
                {
                    "text": msg.get("content", "")
                }
            ]
        }

        gemini_history.append(gemini_message)

    return gemini_history


@phase_five_bp.route('/practice-chat', methods=['POST'])
def practice_chat():
    """
    AI coach chat endpoint for multi-turn practice mode conversations.
    
    Expected JSON input:
    {
        "message": "User's current message",
        "history": [
            { "role": "user", "content": "..." },
            { "role": "ai", "content": "..." }
        ],
        "contextReport": {
            "phase": "practice",
            "analysis": { ... document/speech analysis data ... }
        }
    }
    
    Returns:
    {
        "status": "success",
        "ai_response": "AI coach's response text",
        "message_id": "unique_message_id",
        "timestamp": "ISO 8601 timestamp"
    }
    
    Error responses (400/500):
    - Missing or invalid message
    - JSON parsing errors
    - Gemini API failures
    - Network timeouts
    """

    temp_chat_session = None

    try:
        # ===== STEP 1: VALIDATE REQUEST DATA =====
        data = request.get_json()

        if data is None:
            return jsonify({
                "error": "Invalid JSON",
                "message": "Request body must be valid JSON"
            }), 400

        # Extract and validate message field
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                "error": "Missing message field",
                "message": "Please provide a 'message' field with your input"
            }), 400

        # Extract history and context report (optional but recommended)
        history = data.get('history', [])
        context_report = data.get('contextReport', {})

        # ===== STEP 1b: GRAMMAR CHECK ON USER MESSAGE =====
        # Run LanguageTool on the user's spoken/typed message so the AI coach
        # can point out specific grammar mistakes in the user's own words.
        grammar_issues = []
        grammar_score_val = 100
        grammar_context = ""
        try:
            if len(message) > 10:
                grammar_issues = check_grammar(message)
                grammar_score_val = lt_grammar_score(grammar_issues, len(message.split()))
                grammar_summary = summarise_grammar_issues(grammar_issues, max_issues=10)
                if grammar_issues:
                    grammar_context = f"""

--- GRAMMAR ANALYSIS OF USER'S MESSAGE (LanguageTool) ---
Grammar Score: {grammar_score_val}/100  |  Issues Found: {len(grammar_issues)}
{grammar_summary}
IMPORTANT: Gently point out these grammar issues in your coaching response.
Be specific — quote the erroneous phrase and suggest the correction.
--- END GRAMMAR ANALYSIS ---"""
                    print(f"[AI COACH] LanguageTool: {len(grammar_issues)} grammar issues in user message.")
        except Exception as _ge:
            print(f"[AI COACH WARN] Grammar pre-pass failed: {_ge}")

        # ===== STEP 2: BUILD SYSTEM PROMPT WITH CONTEXT INJECTION =====
        # CRITICAL: The system prompt establishes the AI's role and constraints
        # Context injection allows the AI to reference the user's detailed V1 vs V2 analysis
        
        context_text = "No analysis report provided."
        
        if context_report:
            phase = context_report.get('phase', 'Unknown')
            v1_analysis = context_report.get('v1Analysis') or context_report.get('v1Report')
            v2_analysis = context_report.get('v2Analysis') or context_report.get('v2Report')
            v1_text = context_report.get('v1Text') or context_report.get('v1Transcript')
            v2_text = context_report.get('v2Text') or context_report.get('v2Transcript')
            comparison_data = context_report.get('comparison') or context_report.get('comparisonReport')
            
            context_text = f"""
Previous Analysis Session Context:
- Phase / Mode: {phase}
- Version 1 (Baseline) Content/Text: {v1_text}
- Version 1 (Baseline) Score & Evaluation: {v1_analysis}
- Version 2 (Revised) Content/Text: {v2_text}
- Version 2 (Revised) Score & Evaluation: {v2_analysis}
- Progress Comparison Report: {comparison_data}
"""

        system_prompt = f"""You are Dr. Alexander Vance, a World-Class Executive Presentation Coach and Viva Defense Specialist.

CRITICAL MANDATE - CONCISE & QUESTION-APPROPRIATE RESPONSES:
- **Maximum Length**: Keep your response short, punchy, and digestible (2 to 3 brief bullet points or paragraphs, UNDER 150 words total).
- **Direct & Actionable**: Answer the user's specific question immediately. Do not write long preambles, multi-page outlines, or unrequested general lectures.
- **Practice-Friendly**: Format feedback so a student can read and apply it in 5–10 seconds while practicing.
- **Scripting**: If giving script rewrites, provide only 1 to 2 crisp, high-impact sentences.
- **Grammar**: If grammar issues are flagged below, briefly point out the fix in 1 sentence.

=== USER PRESENTATION CONTEXT ===
{context_text}{grammar_context}

=== STYLE ===
- Professional, encouraging, clear, and focused.
- End with 1 short, targeted follow-up question or quick tip."""

        # ===== STEP 3: LOCAL INTENT ENGINE & STATE MACHINE =====
        from services.coach_intent_engine import process_coach_chat
        
        coach_result = process_coach_chat(
            user_message=message,
            current_state="PRACTICE",
            session_context=context_report
        )
        
        ai_response_text = coach_result.get("response", "Keep practicing with clear WPM pacing and structured slides.")

        if not ai_response_text:
            print("❌ Empty response from Gemini API")
            return jsonify({
                "error": "Empty response from AI model",
                "message": "The AI model returned an empty response. Please try again."
            }), 500

        # ===== STEP 7: COMPILE AND RETURN RESPONSE =====
        chat_response = {
            "status": "success",
            "ai_response": ai_response_text,
            "message_id": f"msg_{int(datetime.now().timestamp() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            # Grammar data for the user's own message
            "grammar_score": grammar_score_val,
            "grammar_issues": grammar_issues,
            "grammar_issues_count": len(grammar_issues),
        }

        print(f"✅ AI Coach response generated successfully")

        return jsonify(chat_response), 200

    except Exception as e:
        # ===== ERROR HANDLING =====
        # Catch all exceptions from Gemini API calls, network errors, etc.
        
        print(f"❌ Error during AI coach chat: {str(e)}")

        # Provide user-friendly error messages based on exception type
        error_message = str(e)
        
        if "api_key" in error_message.lower() or "authentication" in error_message.lower():
            error_message = "Authentication failed. Please check your API key configuration."
        elif "quota" in error_message.lower() or "rate" in error_message.lower():
            error_message = "API quota exceeded. Please try again later."
        elif "timeout" in error_message.lower() or "connection" in error_message.lower():
            error_message = "Network timeout. Please check your connection and try again."

        return jsonify({
            "error": "AI coach service unavailable",
            "message": error_message,
            "details": str(e)
        }), 500
