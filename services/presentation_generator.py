"""
AI Presentation Generator Service
Generates structured, professional presentation outlines using Gemini AI and programmatically
constructs high-quality, visually appealing PowerPoint (.pptx) decks with modern layouts,
multi-column card grids, split executive frames, and styled typography (comparable to Gamma/Pitch).
"""

import os
import json
import logging
import uuid
import re
from typing import Dict, Any, List
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

logger = logging.getLogger(__name__)

# Output folder for generated presentations
GENERATED_FOLDER = os.path.join(os.getcwd(), 'instance', 'generated_presentations')
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# Preset Color Themes with modern contrast palettes
THEMES = {
    'modern_dark': {
        'bg_color': RGBColor(15, 23, 42),          # Slate 900
        'card_color': RGBColor(30, 41, 59),        # Slate 800
        'card_border': RGBColor(51, 65, 85),       # Slate 700
        'title_color': RGBColor(56, 189, 248),      # Sky 400
        'text_color': RGBColor(248, 250, 252),      # Slate 50
        'subtext_color': RGBColor(148, 163, 184),   # Slate 400
        'accent_color': RGBColor(129, 140, 248),    # Indigo 400
        'highlight_bg': RGBColor(30, 58, 138),     # Blue 900
        'badge_bg': RGBColor(14, 116, 144),        # Cyan 700
    },
    'corporate_clean': {
        'bg_color': RGBColor(248, 250, 252),      # Slate 50
        'card_color': RGBColor(255, 255, 255),      # Pure White
        'card_border': RGBColor(203, 213, 225),     # Slate 300
        'title_color': RGBColor(2, 132, 199),       # Sky 600
        'text_color': RGBColor(30, 41, 59),         # Slate 800
        'subtext_color': RGBColor(71, 85, 105),     # Slate 600
        'accent_color': RGBColor(13, 148, 136),     # Teal 600
        'highlight_bg': RGBColor(224, 242, 254),    # Sky 100
        'badge_bg': RGBColor(15, 118, 110),        # Teal 700
    },
    'creative_neon': {
        'bg_color': RGBColor(24, 24, 27),         # Zinc 900
        'card_color': RGBColor(39, 39, 42),        # Zinc 800
        'card_border': RGBColor(63, 63, 70),       # Zinc 700
        'title_color': RGBColor(244, 63, 94),       # Rose 500
        'text_color': RGBColor(250, 250, 250),     # Zinc 50
        'subtext_color': RGBColor(161, 161, 170),   # Zinc 400
        'accent_color': RGBColor(245, 158, 11),    # Amber 500
        'highlight_bg': RGBColor(136, 19, 55),     # Rose 900
        'badge_bg': RGBColor(190, 18, 60),        # Rose 700
    },
    'academic_elegant': {
        'bg_color': RGBColor(15, 23, 42),         # Dark Navy
        'card_color': RGBColor(30, 41, 59),       # Card Navy
        'card_border': RGBColor(71, 85, 105),      # Slate Border
        'title_color': RGBColor(245, 158, 11),      # Gold Amber
        'text_color': RGBColor(226, 232, 240),     # Light Grey Text
        'subtext_color': RGBColor(148, 163, 184),
        'accent_color': RGBColor(16, 185, 129),    # Emerald 500
        'highlight_bg': RGBColor(120, 53, 15),     # Amber 900
        'badge_bg': RGBColor(180, 83, 9),         # Amber 700
    }
}


def build_prompt_for_presentation(topic: str, slide_count: int, tone: str, audience: str) -> str:
    """Build prompt asking Gemini for JSON presentation outline adhering to 7 Cs and modern visual card design."""
    return f"""You are a world-class executive presentation strategist and visual presentation designer (like Gamma, Pitch, and Beautiful.ai).
Generate a complete, highly structured presentation outline on the topic: "{topic}".

STRICT EVALUATION & COMMUNICATION CRITERIA (7 Cs OF COMMUNICATION):
1. CLARITY: Crystal clear slide headers, direct titles, and unambiguous takeaways.
2. CONCISENESS: Punchy, impact-driven bullet points (under 15 words per item). No wordy paragraphs on slides!
3. COMPLETENESS: Logical story curve: Executive Title -> Strategic Overview -> Core Pillars & Architecture -> Execution Metrics -> Summary & Next Steps.
4. CONCRETENESS: Use concrete numbers, real-world metrics, or tangible step names rather than generic fluff.
5. CONSIDERATION: Tailor tone and examples specifically for the target audience: "{audience}".
6. CORRECTNESS: Flawless professional grammar and domain terminology.
7. COURTESY: Maintain an engaging, respectful {tone} tone.

REQUIRED SLIDE LAYOUT TYPES ({slide_count} SLIDES TOTAL):
- Slide 1: Type 'title' -> Hero Title, Compelling Subtitle, Target Audience Tag, Presenter Intro.
- Slide 2: Type 'split' -> Executive Summary & Objectives (Left: Key Takeaway Box, Right: 3 Strategic Objectives).
- Slide 3: Type 'cards' -> 3 Core Pillars / Architecture Cards (Grid layout with Card 01, Card 02, Card 03).
- Slide 4: Type 'metrics' -> Operational Deep Dive (Left: Core Focus, Right: 2 High-Impact Metric Cards).
- Slide 5 to {slide_count}: Type 'timeline' or 'cards' -> Implementation Roadmap, Action Milestones, or Key Recommendations.

CRITICAL FORMAT REQUIREMENT:
Return ONLY a raw valid JSON object with NO markdown code blocks, NO ```json wrapping, and NO commentary.

Required JSON Structure:
{{
  "presentation_title": "Main Presentation Title",
  "subtitle": "Compelling Subtitle or Executive Tagline",
  "topic": "{topic}",
  "target_audience": "{audience}",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Main Presentation Title",
      "subtitle": "Subtitle or Presenter Introduction",
      "type": "title",
      "bullets": [],
      "speaker_notes": "Welcome the audience, establish rapport, and state the primary objectives."
    }},
    {{
      "slide_number": 2,
      "title": "Executive Summary & Objectives",
      "key_takeaway": "Main 1-line strategic takeaway for this section",
      "type": "split",
      "bullets": [
        "Primary driver: Establish core market baseline and objectives",
        "Strategic focus: Align operational priorities and team workflows",
        "Expected output: Deliver scalable results within target timeline"
      ],
      "speaker_notes": "Walk through the executive summary and highlight key objectives."
    }},
    {{
      "slide_number": 3,
      "title": "Core Architectural Pillars",
      "key_takeaway": "Three foundational pillars driving system performance",
      "type": "cards",
      "cards": [
        {{ "title": "01. Foundation Layer", "description": "Core data ingestion, security protocols, and architecture." }},
        {{ "title": "02. Analysis Engine", "description": "AI processing pipeline, feature extraction, and real-time rules." }},
        {{ "title": "03. Delivery & Scale", "description": "Automated reporting, dashboard visualizer, and user analytics." }}
      ],
      "bullets": [],
      "speaker_notes": "Explain each of the three core pillars and their role."
    }}
  ]
}}

Generate exactly {slide_count} slides. Ensure content is crisp, professional, and visually structured!"""


def generate_presentation_outline(topic: str, slide_count: int = 5, tone: str = "Professional", audience: str = "General Audience") -> Dict[str, Any]:
    """Call AI provider or fallback generator to return structured presentation JSON."""
    offline = os.getenv('FORCE_OFFLINE_MODE', '0').strip().lower() in {'1', 'true', 'yes', 'on'} or \
              os.getenv('PRESENTATION_REWRITER_OFFLINE', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    
    logger.info("[presentation_generator] Operating in local deterministic template generator mode.")
    return _build_fallback_outline(topic, slide_count, tone, audience)


def _build_fallback_outline(topic: str, slide_count: int, tone: str, audience: str) -> Dict[str, Any]:
    """Generate high-quality structured outline for fallback mode."""
    topic_clean = topic.strip().title()
    slides = [
        {
            "slide_number": 1,
            "title": f"Mastering {topic_clean}",
            "subtitle": f"A Strategic {tone} Guide for {audience}",
            "type": "title",
            "bullets": [],
            "speaker_notes": f"Welcome everyone. Today we will explore key strategies and practical insights regarding {topic_clean}."
        },
        {
            "slide_number": 2,
            "title": "Executive Summary & Objectives",
            "key_takeaway": "Core goals and strategic significance",
            "type": "split",
            "bullets": [
                f"Understanding primary growth drivers and principles of {topic_clean}.",
                "Identifying operational challenges and high-value opportunities.",
                "Establishing measurable milestones for execution success."
            ],
            "speaker_notes": "Highlight the overarching goals and explain why this topic is essential right now."
        },
        {
            "slide_number": 3,
            "title": "Core Architectural Pillars",
            "key_takeaway": "Three foundational pillars driving performance",
            "type": "cards",
            "cards": [
                { "title": "01. Foundation & Quality", "description": f"Establishing core standards, baseline metrics, and governance for {topic_clean}." },
                { "title": "02. Execution Pipeline", "description": "Integrating workflows, operational automation, and continuous feedback." },
                { "title": "03. Scaling & Analytics", "description": "Tracking key performance indicators, longitudinal metrics, and growth." }
            ],
            "bullets": [],
            "speaker_notes": "Walk through each of the three core architectural pillars step-by-step."
        },
        {
            "slide_number": 4,
            "title": "Strategic Implementation Roadmap",
            "key_takeaway": "Actionable milestones and execution phases",
            "type": "timeline",
            "cards": [
                { "title": "Phase 1: Assessment", "description": "Initial assessment, resource allocation, and team alignment." },
                { "title": "Phase 2: Execution", "description": "Core rollout, continuous monitoring, and optimization." },
                { "title": "Phase 3: Scaling", "description": "Expanding scope, institutionalizing best practices, and measuring impact." }
            ],
            "bullets": [
                "Phase 1: Initial assessment and resource allocation.",
                "Phase 2: Execution and continuous optimization.",
                "Phase 3: Scaling and institutionalizing success."
            ],
            "speaker_notes": "Emphasize practical execution steps and realistic timelines."
        },
        {
            "slide_number": 5,
            "title": "Summary & Key Next Steps",
            "key_takeaway": "Final recommendations and collaborative Q&A",
            "type": "split",
            "bullets": [
                f"Consolidate top learnings for {topic_clean}.",
                "Initiate immediate next steps and assign team ownership.",
                "Open the floor for questions, feedback, and discussion."
            ],
            "speaker_notes": "Summarize top takeaways and invite audience questions."
        }
    ]

    while len(slides) < slide_count:
        idx = len(slides) + 1
        slides.insert(len(slides) - 1, {
            "slide_number": idx,
            "title": f"Deep Dive: Key Area #{idx - 2}",
            "key_takeaway": "In-depth operational breakdown",
            "type": "cards",
            "cards": [
                { "title": "Focus A: Quality Control", "description": "Enforcing continuous monitoring and rigorous benchmarking." },
                { "title": "Focus B: Efficiency", "description": "Streamlining processes to reduce latency and maximize throughput." },
                { "title": "Focus C: User Impact", "description": "Ensuring measurable end-user value and satisfaction." }
            ],
            "bullets": [],
            "speaker_notes": f"Discuss deep dive details for area #{idx - 2}."
        })

    for i, s in enumerate(slides):
        s["slide_number"] = i + 1

    return {
        "presentation_title": f"Mastering {topic_clean}",
        "subtitle": f"A Strategic {tone} Guide for {audience}",
        "topic": topic,
        "target_audience": audience,
        "seven_cs_applied": ["Clarity", "Conciseness", "Completeness", "Concreteness", "Consideration", "Correctness", "Courtesy"],
        "slides": slides[:slide_count]
    }


def build_pptx_from_outline(outline_data: Dict[str, Any], theme_name: str = 'modern_dark') -> str:
    """
    Programmatically construct a highly styled, professional PowerPoint (.pptx) deck.
    Supports multi-column card grids, split executive cards, timelines, and custom visual badges.
    """
    theme = THEMES.get(theme_name, THEMES['modern_dark'])
    
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 Widescreen ratio
    prs.slide_height = Inches(7.5)
    
    blank_layout = prs.slide_layouts[6]
    
    slides = outline_data.get('slides', [])
    for slide_info in slides:
        slide = prs.slides.add_slide(blank_layout)
        
        # 1. Slide Background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = theme['bg_color']
        bg.line.fill.background()
        
        slide_type = slide_info.get('type', 'content')
        is_title_slide = (slide_type == 'title' or slide_info.get('slide_number') == 1)
        
        if is_title_slide:
            # ── TITLE SLIDE LAYOUT (Hero Card Structure) ─────────────────────
            # Background Hero Card Container
            hero_card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.0), Inches(11.333), Inches(5.5)
            )
            hero_card.fill.solid()
            hero_card.fill.fore_color.rgb = theme['card_color']
            hero_card.line.color.rgb = theme['card_border']
            
            # Accent Stripe Bar
            stripe = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(1.8), Inches(2.2), Inches(0.08)
            )
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = theme['title_color']
            stripe.line.fill.background()
            
            # Title & Subtitle Box
            txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2.1), Inches(10.33), Inches(3.8))
            tf = txBox.text_frame
            tf.word_wrap = True
            
            p = tf.paragraphs[0]
            p.text = slide_info.get('title', outline_data.get('presentation_title', 'Presentation'))
            p.font.size = Pt(42)
            p.font.bold = True
            p.font.color.rgb = theme['title_color']
            
            if slide_info.get('subtitle') or outline_data.get('subtitle'):
                p2 = tf.add_paragraph()
                p2.text = slide_info.get('subtitle', outline_data.get('subtitle', ''))
                p2.font.size = Pt(20)
                p2.font.color.rgb = theme['subtext_color']
                p2.space_before = Pt(12)
                
            p3 = tf.add_paragraph()
            p3.text = f"🎯 Target Audience: {outline_data.get('target_audience', 'General')}"
            p3.font.size = Pt(14)
            p3.font.bold = True
            p3.font.color.rgb = theme['accent_color']
            p3.space_before = Pt(22)
            
        else:
            # ── HEADER (All Content Slides) ──────────────────────────────────
            header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.1))
            tf_head = header_box.text_frame
            tf_head.word_wrap = True
            
            p_title = tf_head.paragraphs[0]
            p_title.text = slide_info.get('title', f"Slide {slide_info.get('slide_number')}")
            p_title.font.size = Pt(28)
            p_title.font.bold = True
            p_title.font.color.rgb = theme['title_color']
            
            if slide_info.get('key_takeaway'):
                p_sub = tf_head.add_paragraph()
                p_sub.text = f"💡 {slide_info.get('key_takeaway')}"
                p_sub.font.size = Pt(13)
                p_sub.font.color.rgb = theme['accent_color']
                p_sub.space_before = Pt(3)

            cards = slide_info.get('cards', [])
            bullets = slide_info.get('bullets', [])
            
            if (slide_type == 'cards' or slide_type == 'timeline') and cards:
                # ── LAYOUT A: 3-COLUMN CARD GRID (Gamma / Pitch Style) ────────
                num_cards = min(3, len(cards))
                card_width = Inches(3.6)
                card_gap = Inches(0.4)
                left_margin = Inches(0.8)
                top_pos = Inches(1.7)
                card_height = Inches(4.8)
                
                for ci in range(num_cards):
                    c_data = cards[ci]
                    c_left = left_margin + ci * (card_width + card_gap)
                    
                    # Individual Grid Card
                    grid_card = slide.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE, c_left, top_pos, card_width, card_height
                    )
                    grid_card.fill.solid()
                    grid_card.fill.fore_color.rgb = theme['card_color']
                    grid_card.line.color.rgb = theme['card_border']
                    
                    # Header accent band on card
                    band = slide.shapes.add_shape(
                        MSO_SHAPE.RECTANGLE, c_left, top_pos, card_width, Inches(0.12)
                    )
                    band.fill.solid()
                    band.fill.fore_color.rgb = theme['title_color'] if ci == 0 else theme['accent_color']
                    band.line.fill.background()
                    
                    # Card Content
                    c_box = slide.shapes.add_textbox(c_left + Inches(0.2), top_pos + Inches(0.3), card_width - Inches(0.4), card_height - Inches(0.5))
                    c_tf = c_box.text_frame
                    c_tf.word_wrap = True
                    
                    # Card Header
                    p_ctitle = c_tf.paragraphs[0]
                    p_ctitle.text = c_data.get('title', f'Feature {ci+1}')
                    p_ctitle.font.size = Pt(17)
                    p_ctitle.font.bold = True
                    p_ctitle.font.color.rgb = theme['title_color']
                    
                    # Card Description
                    p_cdesc = c_tf.add_paragraph()
                    p_cdesc.text = c_data.get('description', '')
                    p_cdesc.font.size = Pt(13)
                    p_cdesc.font.color.rgb = theme['text_color']
                    p_cdesc.space_before = Pt(10)

            elif slide_type == 'split' or len(bullets) > 0:
                # ── LAYOUT B: SPLIT 2-COLUMN FOCUS LAYOUT ────────────────────
                # Left Highlight Card
                left_card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.7), Inches(3.6), Inches(4.8)
                )
                left_card.fill.solid()
                left_card.fill.fore_color.rgb = theme['highlight_bg']
                left_card.line.color.rgb = theme['title_color']
                
                lc_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(3.2), Inches(4.4))
                lc_tf = lc_box.text_frame
                lc_tf.word_wrap = True
                
                lc_p1 = lc_tf.paragraphs[0]
                lc_p1.text = "🎯 STRATEGIC FOCUS"
                lc_p1.font.size = Pt(13)
                lc_p1.font.bold = True
                lc_p1.font.color.rgb = theme['title_color']
                
                lc_p2 = lc_tf.add_paragraph()
                lc_p2.text = slide_info.get('key_takeaway', outline_data.get('presentation_title', 'Core Objective'))
                lc_p2.font.size = Pt(16)
                lc_p2.font.bold = True
                lc_p2.font.color.rgb = theme['text_color']
                lc_p2.space_before = Pt(12)

                # Right Column Stacked Bullet Cards
                rc_card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.7), Inches(1.7), Inches(7.8), Inches(4.8)
                )
                rc_card.fill.solid()
                rc_card.fill.fore_color.rgb = theme['card_color']
                rc_card.line.color.rgb = theme['card_border']
                
                rc_box = slide.shapes.add_textbox(Inches(5.0), Inches(1.9), Inches(7.2), Inches(4.4))
                rc_tf = rc_box.text_frame
                rc_tf.word_wrap = True
                
                for i, b_text in enumerate(bullets):
                    p_b = rc_tf.paragraphs[0] if i == 0 else rc_tf.add_paragraph()
                    p_b.text = f"•  {b_text}"
                    p_b.font.size = Pt(16)
                    p_b.font.color.rgb = theme['text_color']
                    p_b.space_before = Pt(14)
            else:
                # ── LAYOUT C: STANDARD WIDE CARD ──────────────────────────────
                wide_card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.7), Inches(11.733), Inches(4.8)
                )
                wide_card.fill.solid()
                wide_card.fill.fore_color.rgb = theme['card_color']
                wide_card.line.color.rgb = theme['card_border']
                
                w_box = slide.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(11.1), Inches(4.4))
                w_tf = w_box.text_frame
                w_tf.word_wrap = True
                
                for i, b_text in enumerate(bullets):
                    p_b = w_tf.paragraphs[0] if i == 0 else w_tf.add_paragraph()
                    p_b.text = f"•  {b_text}"
                    p_b.font.size = Pt(16)
                    p_b.font.color.rgb = theme['text_color']
                    p_b.space_before = Pt(12)

            # Footer / Slide Number
            footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.4))
            tf_foot = footer_box.text_frame
            p_foot = tf_foot.paragraphs[0]
            p_foot.text = f"{outline_data.get('presentation_title', 'AI Presentation')}  |  Slide {slide_info.get('slide_number')}"
            p_foot.font.size = Pt(10)
            p_foot.font.color.rgb = theme['subtext_color']

        # Add Speaker Notes
        if slide_info.get('speaker_notes'):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_info.get('speaker_notes')

    # Save output file
    filename = f"generated_{uuid.uuid4().hex[:10]}.pptx"
    filepath = os.path.join(GENERATED_FOLDER, filename)
    prs.save(filepath)
    logger.info(f"[presentation_generator] Presentation saved to {filepath}")
    return filepath
