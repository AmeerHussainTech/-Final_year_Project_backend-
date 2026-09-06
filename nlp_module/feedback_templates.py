import re

def generate_offline_feedback(features, scores, seven_cs_scores, text):
    """
    Generates detailed, deterministic feedback paragraphs, strengths, recommendations,
    7Cs justifications, and polished rewrites without any LLM requests.
    """
    strengths = []
    recommendations = []
    
    # 1. Evaluate Strengths (Pick top 3 strongest dimensions)
    sorted_dims = sorted(
        [(k, v) for k, v in scores.items() if k not in ["overall_score"]],
        key=lambda x: x[1],
        reverse=True
    )
    
    strengths_map = {
        "Structure": "Demonstrates excellent organization with logical transitions and a clear progression of thoughts.",
        "Clarity": "Your writing uses straightforward language and simple sentences, making ideas easy to follow.",
        "Persuasion": "Crafts compelling reasoning with strong rhetorical elements that naturally engage the audience.",
        "Content_Quality": "Provides substantial details and depth, showing excellent subject-matter expertise.",
        "Call_to_Action": "Includes a highly clear call-to-action that guides the audience on key next steps.",
        "Grammar_and_Syntax": "Exhibits outstanding grammatical structure and polished spelling with no errors.",
        "Accuracy": "Contains highly precise information, sound definitions, and factually correct statements.",
        "Tone_Appropriateness": "Maintains a highly professional, respectful, and scholarly tone ideal for evaluations.",
        "Audience_Alignment": "Tailors details to address the explicit concerns and expectations of key stakeholders.",
        "Purpose_Fulfillment": "Successfully answers the core prompt and achieves the presentation's primary goals."
    }
    
    for dim, score in sorted_dims[:3]:
        msg = strengths_map.get(dim, f"Shows good competency in {dim}.")
        strengths.append(msg)
        
    # 2. Evaluate Recommendations (Pick top 3 weakest dimensions)
    recs_map = {
        "Structure": "Structure your presentation with clear outline markers (e.g. 'Slide 1: Title') and ensure a distinct Agenda is present.",
        "Clarity": "Simplify complex sentences to under 15 words and eliminate filler words like 'um' or 'basically'.",
        "Persuasion": "Reinforce key points with stronger visual examples or rhetorical emphasis to build trust.",
        "Content_Quality": "Elaborate further on your methodology and key metrics to give the slides more depth.",
        "Call_to_Action": "Add a dedicated concluding slide with a clear, direct call-to-action or summary of next steps.",
        "Grammar_and_Syntax": "Run a thorough spelling check to correct minor grammatical errors and punctuation issues.",
        "Accuracy": "Review technical terms to ensure statements are completely precise and logically connected.",
        "Tone_Appropriateness": "Refrain from conversational phrasing; keep the slides formal and professional.",
        "Audience_Alignment": "Align the technical depth of the presentation directly with the expectations of the panel.",
        "Purpose_Fulfillment": "Clarify the target outcome of the presentation early on to establish context."
    }
    
    for dim, score in reversed(sorted_dims):
        if len(recommendations) < 3:
            msg = recs_map.get(dim, f"Focus on improving {dim} to polish your delivery.")
            recommendations.append(msg)
            
    # 3. Create 7Cs justifications
    seven_cs_evaluation = {}
    
    if seven_cs_scores["Clear"] >= 75:
        seven_cs_evaluation["Clear"] = "The core message is highly clear, featuring short, readable sentences."
    else:
        seven_cs_evaluation["Clear"] = f"Sentence length averages {features['avg_sentence_len']:.1f} words, creating clarity barriers."
        
    if seven_cs_scores["Concise"] >= 75:
        seven_cs_evaluation["Concise"] = "The draft is highly concise with minimal filler words and redundant phrases."
    else:
        seven_cs_evaluation["Concise"] = f"Conciseness is affected by a filler word density of {features['filler_density']*100:.1f}%."
        
    if seven_cs_scores["Correct"] >= 75:
        seven_cs_evaluation["Correct"] = "The text displays strong grammatical structure and proper spelling."
    else:
        seven_cs_evaluation["Correct"] = "Proofreading is required to correct punctuation spacing or syntactic errors."
        
    if seven_cs_scores["Complete"] >= 75:
        seven_cs_evaluation["Complete"] = "Contains transition words that signpost a complete beginning, middle, and end."
    else:
        seven_cs_evaluation["Complete"] = "Structure feels fragmented; add transition phrases (e.g. 'therefore', 'in conclusion')."
        
    if seven_cs_scores["Courteous"] >= 75:
        seven_cs_evaluation["Courteous"] = "Tone is highly polite, formal, and suitable for professional presenting."
    else:
        seven_cs_evaluation["Courteous"] = "The tone is overly informal. Adjust phrasing to be more respectful and academic."
        
    if seven_cs_scores["Concrete"] >= 75:
        seven_cs_evaluation["Concrete"] = "The language uses concrete nouns and chunks, showing good subject matter focus."
    else:
        seven_cs_evaluation["Concrete"] = "The wording is abstract. Add details, facts, or statistics to ground your points."
        
    if seven_cs_scores["Consistent"] >= 75:
        seven_cs_evaluation["Consistent"] = "Formatting and style markers are highly consistent across the draft."
    else:
        seven_cs_evaluation["Consistent"] = "Style shifts or formatting errors compromise the consistency of the delivery."

    # 4. Generate detailed paragraph summary
    top_strength_cat = sorted_dims[0][0]
    weakest_cat = sorted_dims[-1][0]
    detailed_feedback = (
        f"This offline ML evaluation reports an overall score of {scores['overall_score']}/100. "
        f"Analysis indicates your primary strength is in {top_strength_cat.replace('_', ' ')}, "
        f"which shows polished execution. However, your performance in {weakest_cat.replace('_', ' ')} "
        f"leaves room for improvement. We recommend revising your script following the concrete suggestions "
        f"detailed below to achieve a more cohesive and professional presentation."
    )
    
    # 5. Local Speech Polisher (Polished Rewrite)
    polished_text = text
    fillers = ['um', 'uh', 'like', 'you know', 'basically', 'actually', 'so', 'kind of', 'sort of', 'literally']
    for f in fillers:
        polished_text = re.sub(rf'\b{f}\b', '', polished_text, flags=re.IGNORECASE)
    
    # Clean multiple spaces
    polished_text = re.sub(r'\s+', ' ', polished_text).strip()
    
    # Capitalize sentences correctly
    sentences = re.split(r'([.!?]\s*)', polished_text)
    if len(sentences) > 1:
        capitalized = []
        for s in sentences:
            if s and not s.isspace():
                if capitalized and capitalized[-1].endswith((' ', '.', '!', '?')):
                    capitalized.append(s[0].upper() + s[1:])
                elif not capitalized:
                    capitalized.append(s[0].upper() + s[1:])
                else:
                    capitalized.append(s)
            else:
                capitalized.append(s)
        polished_text = "".join(capitalized)

    # Format into slide headers if no formatting exists
    if "slide" not in polished_text.lower() and "#" not in polished_text:
        sents = [s.strip() for s in re.split(r'[.!?]+', polished_text) if s.strip()]
        slide_blocks = []
        for i in range(0, len(sents), 4):
            sub_block = ". ".join(sents[i:i+4]).strip()
            if sub_block:
                if not sub_block.endswith('.'):
                    sub_block += '.'
                slide_blocks.append(f"# SLIDE {len(slide_blocks)+1}\n{sub_block}")
        polished_text = "\n\n".join(slide_blocks)
        
    return {
        "strengths": strengths,
        "recommendations": recommendations,
        "seven_cs_evaluation": seven_cs_evaluation,
        "detailed_feedback": detailed_feedback,
        "improved_text": polished_text
    }
