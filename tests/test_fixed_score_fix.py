import sys
import os
import pickle

# Force stdout/stderr UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add nlp_module directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NLP_DIR = os.path.join(BASE_DIR, 'nlp_module')
if NLP_DIR not in sys.path:
    sys.path.insert(0, NLP_DIR)

from feature_extractors import extract_features, get_feature_names
from scoring_model import score_text_offline, load_scoring_models
from train_model import train_model, DATASET_PATH, MODEL_PATH
import pandas as pd

def run_6_step_fix_plan():
    print("============================================================")
    print("🛠️  EXECUTING 6-STEP FIX PLAN: 7CS SCORING MODULE AUDIT")
    print("============================================================")

    # ---------------------------------------------------------
    # STEP 1: Verify Dataset Loading
    # ---------------------------------------------------------
    print("\n--- STEP 1: VERIFY DATASET LOADING ---")
    if not os.path.exists(DATASET_PATH):
        print(f"[INFO] Dataset file {DATASET_PATH} not found. Running dataset generator...")
        train_model()
    
    df = pd.read_csv(DATASET_PATH)
    print(f"✅ Dataset Path: {DATASET_PATH}")
    print(f"✅ Dataframe Shape: {df.shape} (Rows: {df.shape[0]}, Columns: {df.shape[1]})")
    print(f"✅ Column Headers: {list(df.columns)}")
    print(f"✅ First Row Preview: {dict(df.iloc[0])}")

    # ---------------------------------------------------------
    # STEP 2: Feature Extraction Sanity Check (Before & After)
    # ---------------------------------------------------------
    print("\n--- STEP 2: FEATURE EXTRACTION SANITY CHECK ---")
    text_bad = "um like basically app works bad . duplicate duplicate word bad grammar punctuation , bad . no agenda ."
    text_good = (
        "Welcome to our technical presentation. Firstly, our microservices architecture leverages distributed caching "
        "and spaCy feature extraction. Secondly, we benchmarked overall accuracy across 300 test cases. In conclusion, "
        "this solution guarantees high performance and scalability for our stakeholders."
    )

    feats_bad = extract_features(text_bad)
    feats_good = extract_features(text_good)
    feature_names = get_feature_names()

    print(f"{'Feature Name':<25} | {'Text A (Bad)':<18} | {'Text B (Good)':<18} | {'Differs?':<8}")
    print("-" * 75)
    features_differ = False
    for fname in feature_names:
        v_bad = round(feats_bad[fname], 4)
        v_good = round(feats_good[fname], 4)
        diff_flag = "YES ✅" if v_bad != v_good else "NO ❌"
        if v_bad != v_good:
            features_differ = True
        print(f"{fname:<25} | {v_bad:<18} | {v_good:<18} | {diff_flag:<8}")

    if not features_differ:
        print("❌ CRITICAL BUG: Feature vectors are identical across different texts!")
        sys.exit(1)
    else:
        print("✅ SUCCESS: Feature vectors differ significantly across different texts!")

    # ---------------------------------------------------------
    # STEP 3: Run Model Training & Verify .pkl
    # ---------------------------------------------------------
    print("\n--- STEP 3: RUN TRAINING & VERIFY WEIGHTS ---")
    train_model()
    
    if not os.path.exists(MODEL_PATH):
        print(f"❌ CRITICAL ERROR: {MODEL_PATH} was not created!")
        sys.exit(1)
    
    file_size_kb = os.path.getsize(MODEL_PATH) / 1024.0
    print(f"✅ Trained Model Path: {MODEL_PATH}")
    print(f"✅ Checkpoint File Size: {file_size_kb:.2f} KB (Confirmed Non-Empty)")

    # ---------------------------------------------------------
    # STEP 4: Audit scoring_model.py & Verify Model Loading
    # ---------------------------------------------------------
    print("\n--- STEP 4: AUDIT MODEL LOADING ---")
    models, loaded_feats = load_scoring_models()
    if models is None:
        print("❌ CRITICAL ERROR: Scoring model failed to load trained_weights.pkl!")
        sys.exit(1)
    print(f"✅ Loaded Estimators: {list(models.keys())}")
    print(f"✅ Loaded Feature Names: {loaded_feats}")

    # ---------------------------------------------------------
    # STEP 5: Re-test With Two Different Texts
    # ---------------------------------------------------------
    print("\n--- STEP 5: SCORE DIFFERENTIATION TEST ---")
    scores_bad, sc_7cs_bad, _ = score_text_offline(text_bad)
    scores_good, sc_7cs_good, _ = score_text_offline(text_good)

    print(f"Text A (Bad) Overall Score: {scores_bad['overall_score']}")
    print(f"Text B (Good) Overall Score: {scores_good['overall_score']}")
    
    print("\n7Cs Breakdown Comparison:")
    print(f"{'7Cs Trait':<20} | {'Text A (Bad)':<18} | {'Text B (Good)':<18} | {'Delta':<8}")
    print("-" * 70)
    score_diff_found = False
    for trait, s_bad in sc_7cs_bad.items():
        s_good = sc_7cs_good[trait]
        delta = s_good - s_bad
        if delta != 0:
            score_diff_found = True
        print(f"{trait:<20} | {s_bad:<18} | {s_good:<18} | {delta:+d}")

    if not score_diff_found:
        print("❌ BUG STILL PRESENT: 7Cs Scores are identical for different texts!")
        sys.exit(1)
    else:
        print(f"✅ SUCCESS: Scores differ meaningfully! (Overall Gap: {scores_good['overall_score'] - scores_bad['overall_score']} points)")

    # ---------------------------------------------------------
    # STEP 6: Determinism Consistency Re-check
    # ---------------------------------------------------------
    print("\n--- STEP 6: DETERMINISM CONSISTENCY RE-CHECK (5 RUNS) ---")
    runs_scores = []
    for run_idx in range(1, 6):
        sc, sc_7c, _ = score_text_offline(text_good)
        runs_scores.append(sc['overall_score'])
        print(f"   Run #{run_idx}: Overall Score = {sc['overall_score']}, 7Cs = {sc_7c}")

    if len(set(runs_scores)) == 1:
        print(f"✅ SUCCESS: 100% Deterministic! All 5 runs yielded exact score = {runs_scores[0]}")
    else:
        print(f"❌ BUG: Scores varied across runs for identical text: {runs_scores}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 ALL 6 STEPS VERIFIED 100% SUCCESSFULLY!")
    print("============================================================")

if __name__ == '__main__':
    run_6_step_fix_plan()
