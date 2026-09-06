try:
    from scoring_model import score_text_offline
    from feedback_templates import generate_offline_feedback
except ImportError:
    from .scoring_model import score_text_offline
    from .feedback_templates import generate_offline_feedback

def evaluate_text_offline(text, module_type='document'):
    """
    Unified entry point for offline deterministic 7Cs evaluation.
    Replaces all Gemini calls for text evaluation in Phase 2, Phase 4, and Phase Live.
    
    Args:
        text (str): The script, slides, or transcript text.
        module_type (str): 'document', 'speech', or 'live'.
        
    Returns:
        dict: Standardized scorecard JSON structure.
    """
    # Safeguard text input
    if not text or not str(text).strip():
        text = "No content provided."

    # 1. Compute scores and extract features
    scores, seven_cs_scores, feats = score_text_offline(text)
    
    # 2. Generate detailed feedback
    feedback = generate_offline_feedback(feats, scores, seven_cs_scores, text)
    
    # Filter category scores based on module type to keep outputs neat
    if module_type == 'document':
        category_scores = {
            "Structure": scores.get("Structure", 70),
            "Clarity": scores.get("Clarity", 70),
            "Persuasion": scores.get("Persuasion", 70),
            "Content_Quality": scores.get("Content_Quality", 70),
            "Call_to_Action": scores.get("Call_to_Action", 70),
            "Grammar_and_Syntax": scores.get("Grammar_and_Syntax", 70),
            "Accuracy": scores.get("Accuracy", 70),
            "Tone_Appropriateness": scores.get("Tone_Appropriateness", 70),
            "Audience_Alignment": scores.get("Audience_Alignment", 70),
            "Purpose_Fulfillment": scores.get("Purpose_Fulfillment", 70)
        }
    else: # speech or live
        category_scores = {
            "Structure": scores.get("Structure", 70),
            "Clarity": scores.get("Clarity", 70),
            "Persuasion": scores.get("Persuasion", 70),
            "Content_Quality": scores.get("Content_Quality", 70),
            "Call_to_Action": scores.get("Call_to_Action", 70)
        }
        
    # Build complete response payload in original expected JSON format
    result = {
        "overall_score": scores["overall_score"],
        "category_scores": category_scores,
        "seven_cs_evaluation": feedback["seven_cs_evaluation"],
        "seven_cs_scores": seven_cs_scores,
        "strengths": feedback["strengths"],
        "recommendations": feedback["recommendations"],
        "detailed_feedback": feedback["detailed_feedback"],
        "improved_text": feedback["improved_text"]
    }
    
    return result
