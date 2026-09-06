import os
import pickle
import numpy as np
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
try:
    from feature_extractors import extract_features
except ImportError:
    from .feature_extractors import extract_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'trained_weights.pkl')

_models_cache = None
_feature_names_cache = None

def load_scoring_models():
    """
    Loads the trained RandomForest regressors and feature mapping list.
    """
    global _models_cache, _feature_names_cache
    if _models_cache is not None:
        return _models_cache, _feature_names_cache
        
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                checkpoint = pickle.load(f)
            _models_cache = checkpoint["models"]
            _feature_names_cache = checkpoint["feature_names"]
            print("[NLP INFO] Successfully loaded offline RandomForest scoring models.")
            return _models_cache, _feature_names_cache
        except Exception as e:
            print(f"[NLP WARN] Error loading model weights: {str(e)}")
            
    return None, None

def score_text_offline(text):
    """
    Predicts scores (0-100) for all 7Cs and performance dimensions using the trained offline model.
    Falls back to robust mathematical heuristics if models are not loaded.
    """
    feats = extract_features(text)
    models, feature_names = load_scoring_models()
    
    scores = {}
    
    if models is not None and feature_names is not None:
        try:
            # Format feature vector
            x = np.array([[feats[name] for name in feature_names]])
            
            # Predict traits
            traits = {}
            for name, regressor in models.items():
                pred = regressor.predict(x)[0]
                traits[name] = float(np.clip(pred, 10.0, 100.0))
                
            # Map traits directly to dimensions and 7Cs
            # 1. Performance Dimensions (0-100 scale)
            scores["Structure"] = int(traits["organization"])
            scores["Clarity"] = int(traits["sentence_fluency"])
            scores["Persuasion"] = int((traits["voice"] * 0.4) + (traits["content"] * 0.6))
            scores["Content_Quality"] = int(traits["content"])
            scores["Call_to_Action"] = int((traits["organization"] * 0.7) + (traits["content"] * 0.3))
            
            # Additional metrics for document analyzer
            scores["Grammar_and_Syntax"] = int(traits["conventions"])
            scores["Accuracy"] = int((traits["content"] * 0.8) + (traits["conventions"] * 0.2))
            scores["Tone_Appropriateness"] = int(traits["voice"])
            scores["Audience_Alignment"] = int((traits["voice"] * 0.5) + (traits["content"] * 0.5))
            scores["Purpose_Fulfillment"] = int(traits["content"])
            
            # Overall score
            scores["overall_score"] = int(traits["content"])
            
            # 2. 7Cs Scores (0-100 scale)
            seven_cs_scores = {
                "Clear": int(traits["sentence_fluency"]),
                "Concise": int((traits["sentence_fluency"] * 0.6) + (traits["word_choice"] * 0.4)),
                "Correct": int(traits["conventions"]),
                "Complete": int(traits["organization"]),
                "Courteous": int(traits["voice"]),
                "Concrete": int(traits["word_choice"]),
                "Consistent": int((traits["conventions"] * 0.5) + (traits["organization"] * 0.5))
            }
            
            return scores, seven_cs_scores, feats
        except Exception as e:
            print(f"[NLP WARN] Regression prediction failed: {str(e)}. Using fallback heuristics.")
            
    # Heuristics Fallback (if weights are not trained/loaded yet)
    scores["Structure"] = int(max(20, 75 - (feats["avg_sentence_len"] > 25) * 15 + (feats["transition_density"] > 0.02) * 15))
    scores["Clarity"] = int(max(20, 85 - (feats["avg_sentence_len"] > 22) * 20 - (feats["filler_density"] > 0.04) * 20))
    scores["Persuasion"] = int(max(20, 70 + int(feats["sentiment_score"] * 15) - (feats["filler_density"] > 0.05) * 10))
    scores["Content_Quality"] = int(max(20, 60 + min(30, int(feats["word_count"] / 10)) + int(feats["noun_chunks_ratio"] * 30)))
    scores["Call_to_Action"] = int(max(20, scores["Structure"] - 5))
    
    scores["Grammar_and_Syntax"] = int(max(20, 100 - (feats["error_density"] * 300)))
    scores["Accuracy"] = int(max(20, scores["Content_Quality"] - 2))
    scores["Tone_Appropriateness"] = int(max(20, 60 + int(feats["sentiment_score"] * 40)))
    scores["Audience_Alignment"] = int(max(20, 60 + int(feats["audience_pronoun_ratio"] * 400)))
    scores["Purpose_Fulfillment"] = int(scores["Content_Quality"])
    
    scores["overall_score"] = int((scores["Structure"] + scores["Clarity"] + scores["Content_Quality"]) / 3.0)
    
    seven_cs_scores = {
        "Clear": scores["Clarity"],
        "Concise": int(max(20, 90 - (feats["filler_density"] * 250) - (feats["redundancy_density"] * 300))),
        "Correct": scores["Grammar_and_Syntax"],
        "Complete": scores["Structure"],
        "Courteous": scores["Tone_Appropriateness"],
        "Concrete": int(max(20, 50 + int(feats["noun_chunks_ratio"] * 100))),
        "Consistent": int((scores["Grammar_and_Syntax"] + scores["Structure"]) / 2)
    }
    
    return scores, seven_cs_scores, feats
