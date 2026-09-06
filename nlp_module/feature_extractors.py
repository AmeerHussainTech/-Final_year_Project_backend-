import re
import sys

# Dynamic imports with graceful fallbacks if packages are not installed or fail
try:
    import textstat
except ImportError:
    textstat = None

try:
    import spacy
    # Load model dynamically inside functions to handle missing model errors gracefully
except ImportError:
    spacy = None

try:
    # pyrefly: ignore [missing-import]
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    # Try downloading the vader lexicon quietly
    try:
        nltk.download('vader_lexicon', quiet=True)
    except Exception:
        pass
except ImportError:
    nltk = None
    SentimentIntensityAnalyzer = None

try:
    import language_tool_python
except ImportError:
    language_tool_python = None


# ---------------------------------------------------------------------------
# Cached tool instances (avoid re-loading heavy models/processes on every call)
# ---------------------------------------------------------------------------

_nlp_cache = None

def get_spacy_nlp():
    global _nlp_cache
    if _nlp_cache is not None:
        return _nlp_cache
    if spacy is not None:
        try:
            _nlp_cache = spacy.load("en_core_web_sm")
            return _nlp_cache
        except Exception as e:
            print(f"[NLP WARN] SpaCy model 'en_core_web_sm' could not be loaded: {str(e)}")
    return None


_lt_cache = None
_lt_failed = False

def get_language_tool():
    global _lt_cache, _lt_failed
    if _lt_failed:
        return None
    if _lt_cache is not None:
        return _lt_cache
    if language_tool_python is not None:
        try:
            _lt_cache = language_tool_python.LanguageTool('en-US')
            return _lt_cache
        except Exception as e:
            print(f"[NLP WARN] LanguageTool initialization failed: {str(e)}")
            _lt_failed = True
    return None


_sia_cache = None
_sia_failed = False

def get_sentiment_analyzer():
    """FIX: SentimentIntensityAnalyzer was previously re-created on every single
    call to extract_features(), unlike every other tool in this file which is
    cached. This wastes time and is inconsistent with the rest of the module."""
    global _sia_cache, _sia_failed
    if _sia_failed:
        return None
    if _sia_cache is not None:
        return _sia_cache
    if nltk is not None and SentimentIntensityAnalyzer is not None:
        try:
            _sia_cache = SentimentIntensityAnalyzer()
            return _sia_cache
        except Exception as e:
            print(f"[NLP WARN] SentimentIntensityAnalyzer initialization failed: {str(e)}")
            _sia_failed = True
    return None


# ---------------------------------------------------------------------------
# Heuristic fallback implementations
# FIX: these are now standalone functions so they can be called BOTH when a
# library is missing AND when a library is installed but fails/throws at
# runtime. Previously the heuristic branch only ran on ImportError, so a
# runtime exception (e.g. LanguageTool's Java process not available, a
# corrupted spaCy model, textstat raising internally) silently fell back to a
# hardcoded static value (flesch_score = 65.0, error_count = 0, passive_ratio
# = 0.0) instead of the heuristic — producing the SAME score for every input
# text. That was the most likely cause of the "fixed score" bug.
# ---------------------------------------------------------------------------

def _heuristic_flesch(clean_text, words, avg_sentence_len, word_count):
    vowels_pattern = re.compile(r'[aeiouy]+')
    syllables = sum(len(vowels_pattern.findall(word)) for word in words)
    syl_per_word = (syllables / word_count) if word_count > 0 else 1.5
    score = 206.835 - (1.015 * avg_sentence_len) - (84.6 * syl_per_word)
    return max(0.0, min(100.0, score))


def _heuristic_passive_ratio(clean_text, sentence_count):
    be_verbs = r'\b(is|am|are|was|were|be|been|being)\b'
    passive_matches = len(re.findall(f"{be_verbs}\\s+\\w+ed\\b", clean_text, re.IGNORECASE))
    return (passive_matches / sentence_count) if sentence_count > 0 else 0.0


def _heuristic_noun_chunks(word_count):
    # Average noun chunk distribution is ~30% of words
    return int(word_count * 0.3)


def _heuristic_error_count(clean_text, text_lower):
    error_count = 0
    error_count += len(re.findall(r'\b(\w+)\s+\1\b', text_lower))  # Duplicate words
    error_count += len(re.findall(r'\s+[,.!?]', clean_text))       # Bad punctuation spacing
    return error_count


def extract_features(text):
    """
    Extracts high-dimensional NLP features from text for 7Cs grading.
    Guaranteed to run offline and fallback to heuristics if packages fail
    or misbehave at runtime (not just when they're missing entirely).
    """
    if not text or not text.strip():
        # FIX: warn loudly instead of silently substituting placeholder text,
        # so an upstream bug that always sends empty text is visible in logs.
        print("[NLP WARN] extract_features() received empty/whitespace-only text.")
        text = "No content provided."

    # Pre-clean text
    clean_text = re.sub(r'\s+', ' ', text).strip()
    words = [w.lower() for w in re.findall(r'\b\w+\b', clean_text)]
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean_text) if s.strip()]
    sentence_count = len(sentences)

    # 1. Averaged Sentence Length
    avg_sentence_len = (word_count / sentence_count) if sentence_count > 0 else 0

    # 2. Readability (Flesch Reading Ease)
    flesch_score = None
    if textstat is not None:
        try:
            flesch_score = textstat.flesch_reading_ease(clean_text)
        except Exception as e:
            print(f"[NLP WARN] textstat failed at runtime, using heuristic fallback: {str(e)}")
    if flesch_score is None:
        flesch_score = _heuristic_flesch(clean_text, words, avg_sentence_len, word_count)
    flesch_score = max(0.0, min(100.0, flesch_score))

    # 3. Passive Voice & Complexity (SpaCy)
    passive_ratio = None
    noun_chunks_count = None
    nlp = get_spacy_nlp()
    if nlp is not None:
        try:
            doc = nlp(clean_text)
            passive_count = sum(1 for token in doc if token.dep_ == 'auxpass')
            sents_list = list(doc.sents)
            passive_ratio = (passive_count / len(sents_list)) if len(sents_list) > 0 else 0.0
            noun_chunks_count = len(list(doc.noun_chunks))
        except Exception as e:
            print(f"[NLP WARN] spaCy parsing failed at runtime, using heuristic fallback: {str(e)}")
    if passive_ratio is None:
        passive_ratio = _heuristic_passive_ratio(clean_text, sentence_count)
    if noun_chunks_count is None:
        noun_chunks_count = _heuristic_noun_chunks(word_count)

    # 4. Filler Word Density
    # NOTE (known limitation): "so", "like", "actually" etc. are common words
    # with legitimate non-filler uses ("I LIKE pizza", "SO be it"). A precise
    # fix requires POS-tag-based disambiguation; left as a documented
    # limitation given project time constraints rather than fixed here.
    fillers = ['um', 'uh', 'like', 'you know', 'basically', 'actually', 'so', 'kind of', 'sort of', 'literally']
    filler_count = 0
    text_lower = clean_text.lower()
    for f in fillers:
        pattern = r'\b' + re.escape(f) + r'\b'
        filler_count += len(re.findall(pattern, text_lower))
    filler_density = (filler_count / word_count) if word_count > 0 else 0

    # 5. Redundant Phrases (Conciseness)
    redundant_phrases = [
        r'\babsolutely\s+essential\b', r'\bclose\s+proximity\b', r'\badded\s+bonus\b',
        r'\bjoin\s+together\b', r'\bperiod\s+of\s+time\b', r'\bfuture\s+plans\b',
        r'\bend\s+result\b', r'\balternative\s+choices\b', r'\brepeat\s+again\b'
    ]
    redundancy_count = 0
    for pattern in redundant_phrases:
        redundancy_count += len(re.findall(pattern, text_lower))

    # 6. Grammar & Spelling Errors (LanguageTool)
    error_count = None
    lt = get_language_tool()
    if lt is not None:
        try:
            matches = lt.check(clean_text)
            error_count = len(matches)
        except Exception as e:
            print(f"[NLP WARN] LanguageTool check failed at runtime, using heuristic fallback: {str(e)}")
    if error_count is None:
        error_count = _heuristic_error_count(clean_text, text_lower)
    error_density = (error_count / word_count) if word_count > 0 else 0

    # 7. Audience Consideration & Tone (Pronouns)
    audience_pronouns = ['you', 'your', 'yours', 'we', 'our', 'us', 'ours']
    personal_pronouns = ['i', 'me', 'my', 'mine', 'myself']

    audience_count = sum(len(re.findall(r'\b' + p + r'\b', text_lower)) for p in audience_pronouns)
    personal_count = sum(len(re.findall(r'\b' + p + r'\b', text_lower)) for p in personal_pronouns)

    audience_pronoun_ratio = (audience_count / word_count) if word_count > 0 else 0
    personal_pronoun_ratio = (personal_count / word_count) if word_count > 0 else 0

    # 8. Structure / Transition Words (Completeness)
    transition_words = [
        'firstly', 'secondly', 'thirdly', 'furthermore', 'moreover', 'in addition',
        'however', 'nevertheless', 'consequently', 'therefore', 'in conclusion', 'finally',
        'subsequently', 'meanwhile', 'specifically', 'to summarize'
    ]
    transition_count = sum(len(re.findall(r'\b' + t + r'\b', text_lower)) for t in transition_words)
    transition_density = (transition_count / word_count) if word_count > 0 else 0

    # 9. Politeness / Sentiment (Courtesy)
    sentiment_score = None
    sia = get_sentiment_analyzer()
    if sia is not None:
        try:
            pol = sia.polarity_scores(clean_text)
            # Map compound score (-1 to +1) to 0 to 1 scale
            sentiment_score = (pol['compound'] + 1.0) / 2.0
        except Exception as e:
            print(f"[NLP WARN] VADER sentiment failed at runtime, using heuristic fallback: {str(e)}")
    if sentiment_score is None:
        # Very simple lexicon fallback
        positive_words = {'good', 'great', 'awesome', 'excellent', 'perfect', 'helpful', 'nice', 'please', 'thank', 'thanks', 'appreciate'}
        negative_words = {'bad', 'terrible', 'poor', 'wrong', 'fail', 'error', 'rude', 'hate', 'stupid', 'useless'}
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        total_lex = pos_count + neg_count
        sentiment_score = (pos_count / total_lex) if total_lex > 0 else 0.5

    # Return key-value dict of numerical features (12 features)
    return {
        "word_count": float(word_count),
        "avg_sentence_len": float(avg_sentence_len),
        "flesch_score": float(flesch_score),
        "passive_ratio": float(passive_ratio),
        "noun_chunks_ratio": float(noun_chunks_count / word_count) if word_count > 0 else 0.0,
        "filler_density": float(filler_density),
        "redundancy_density": float(redundancy_count / word_count) if word_count > 0 else 0.0,
        "error_density": float(error_density),
        "audience_pronoun_ratio": float(audience_pronoun_ratio),
        "personal_pronoun_ratio": float(personal_pronoun_ratio),
        "transition_density": float(transition_density),
        "sentiment_score": float(sentiment_score)
    }


def get_feature_names():
    return [
        "word_count", "avg_sentence_len", "flesch_score", "passive_ratio",
        "noun_chunks_ratio", "filler_density", "redundancy_density", "error_density",
        "audience_pronoun_ratio", "personal_pronoun_ratio", "transition_density", "sentiment_score"
    ]