import os
import pickle
import random
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
try:
    from feature_extractors import extract_features, get_feature_names
except ImportError:
    from .feature_extractors import extract_features, get_feature_names

DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
DATASET_PATH = os.path.join(DATASETS_DIR, 'asap_aes.csv')
# FIX: synthetic fallback now writes to its OWN filename, never to asap_aes.csv,
# so a fake dataset can never masquerade as (or silently overwrite the slot of)
# the real downloaded dataset.
SYNTHETIC_DATASET_PATH = os.path.join(DATASETS_DIR, 'synthetic_essays_DO_NOT_USE_FOR_FINAL.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'trained_weights.pkl')

REQUIRED_TRAITS = ["organization", "conventions", "word_choice", "sentence_fluency", "voice", "content"]


def generate_synthetic_dataset():
    """
    Generates a synthetic dataset ONLY for pipeline smoke-testing (verifying the
    code runs end-to-end). This is NOT real human-labeled data and must never be
    used for the actual submitted/trained model — labels here are computed from
    hand-crafted formulas on the same features, which is functionally equivalent
    to hardcoded/fixed weights, not genuine trained scoring.
    """
    print("=" * 70)
    print("[WARNING] Generating SYNTHETIC dataset for smoke-testing only.")
    print("          This is NOT real human-labeled data.")
    print("          Do NOT use trained_weights.pkl from this run as your final model.")
    print("=" * 70)
    os.makedirs(DATASETS_DIR, exist_ok=True)

    templates = [
        "In this presentation, I am going to explain the design. Firstly, the architecture is modular. Secondly, the database runs on MongoDB. However, we found that scaling is hard. In conclusion, we succeeded.",
        "Um, like, basically, you know, we built this app and it's actually really cool. We did some things, kind of, and so it works. The end.",
        "We are absolutely delighted to welcome you to our corporate proposal. It is absolutely essential to join together to achieve our future plans. We appreciate your consideration.",
        "This project has several errors. The database fail. The API is wrong. Punctuation , is bad . Spelling errrors are present. Duplicate duplicate words here.",
        "Our scalable technical architecture leverages distributed microservices. To implement this, we vectorized all text features using an offline TF-IDF matrix. The results demonstrate high performance.",
        "To achieve clarity, we must keep sentences brief. Long sentences clutter the message. Focus on direct verbs. Avoid passive phrasing.",
        "We thank you, our esteemed panel, for your consideration. We want to align this lecture with your expectations.",
        "The architecture is very disorganized. No agenda is present. Slides are cluttered. There is no call to action at the end.",
    ]

    data = []
    for i in range(300):
        template = random.choice(templates)
        words = template.split()
        if len(words) > 10:
            if random.random() < 0.2:
                words = words + ["um", "basically", "actually", "like"]
            if random.random() < 0.15:
                words = [w for w in words if random.random() > 0.1]
        text = " ".join(words)

        feats = extract_features(text)

        org = 80.0
        if feats["transition_density"] == 0:
            org -= 25
        if feats["word_count"] < 30:
            org -= 20
        org = max(10, min(100, org + random.randint(-5, 5)))

        conv = max(10, min(100, 100 - (feats["error_density"] * 300) + random.randint(-5, 5)))

        word_choice = max(10, min(100, 50 + (feats["noun_chunks_ratio"] * 100) - (feats["filler_density"] * 100) + random.randint(-5, 5)))

        fluency = 80.0
        if feats["avg_sentence_len"] > 20:
            fluency -= 20
        if feats["passive_ratio"] > 0.3:
            fluency -= 15
        if feats["filler_density"] > 0.05:
            fluency -= 15
        fluency = max(10, min(100, fluency + random.randint(-5, 5)))

        voice = max(10, min(100, 50 + (feats["audience_pronoun_ratio"] * 300) + (feats["sentiment_score"] * 30) + random.randint(-5, 5)))

        content = max(10, min(100, (org + conv + word_choice + fluency + voice) / 5.0 + random.randint(-4, 4)))

        data.append({
            "essay": text, "organization": org, "conventions": conv,
            "word_choice": word_choice, "sentence_fluency": fluency,
            "voice": voice, "content": content
        })

    df = pd.DataFrame(data)
    df.to_csv(SYNTHETIC_DATASET_PATH, index=False)
    print(f"[INFO] Synthetic smoke-test dataset saved to {SYNTHETIC_DATASET_PATH}")
    return SYNTHETIC_DATASET_PATH


def _map_real_labels(df):
    """
    FIX: this replaces the old np.random.uniform() fallback, which trained the
    model on pure random noise whenever exact column names like "organization"
    weren't found in the raw ASAP-AES CSV (which they almost never are — the
    real file uses names like domain1_score / rater1_traitN). Training on
    random noise is why the model likely converged to predicting a near-constant
    value regardless of input text.

    Strategy (in priority order, all using REAL human-assigned scores, never
    random values):
      1. If the CSV already has our exact trait column names, use them as-is.
      2. If it has rater1_trait1..rater1_trait6 (the real ASAP multi-trait
         columns for essay sets 7/8), map them in order to our 6 traits.
      3. If neither exists, fall back to domain1_score (a genuine human-rater
         holistic score present across the whole ASAP-AES dataset), scaled to
         0-100, and use that SAME real score as a proxy for all 6 traits.
         This is coarser than per-trait scores but is still real human
         judgment data, not fabricated noise.
      4. If NONE of the above exist, raise an error instead of silently
         inventing labels — a loud failure is safer than a fake model.
    """
    print(f"[INFO] Columns found in dataset: {list(df.columns)}")

    # Priority 1: exact trait columns already present
    if all(t in df.columns for t in REQUIRED_TRAITS):
        print("[INFO] Using exact trait columns found directly in the dataset. (REAL per-trait data)")
        return df

    # Priority 2: real ASAP multi-trait rater columns (essay sets 7 & 8)
    trait_cols = [f"rater1_trait{i}" for i in range(1, 7)]
    if all(c in df.columns for c in trait_cols):
        print("[INFO] Mapping rater1_trait1..6 columns to our 6 traits. (REAL per-trait rater data)")
        print("[ACTION REQUIRED] Verify this order matches your CSV's actual trait definitions "
              "(check the ASAP-AES essay set 7/8 rubric documentation) before treating this as final.")
        for target, source in zip(REQUIRED_TRAITS, trait_cols):
            df[target] = df[source]
        return df

    # Priority 3: holistic domain1_score as a real (if coarse) proxy
    if "domain1_score" in df.columns:
        print("[WARNING] Per-trait columns not found. Falling back to domain1_score "
              "(a real human-rater holistic score) as a proxy for ALL 6 traits.")
        print("          This is coarser than per-trait scoring but is still genuine "
              "human-judged data — not random/fabricated.")
        mn, mx = df["domain1_score"].min(), df["domain1_score"].max()
        scaled = ((df["domain1_score"] - mn) / (mx - mn) * 90 + 10) if mx > mn else pd.Series(70.0, index=df.index)
        for target in REQUIRED_TRAITS:
            df[target] = scaled
        return df

    # Priority 4: nothing usable found — fail loudly, do NOT fabricate labels
    raise ValueError(
        "Could not find usable label columns in the dataset (checked exact trait names, "
        "rater1_trait1..6, and domain1_score). Refusing to train on fabricated/random labels. "
        f"Available columns were: {list(df.columns)}. "
        "Please inspect the CSV and confirm which column holds the human-assigned score."
    )


def train_model(use_synthetic_if_missing=True):
    if not os.path.exists(DATASET_PATH):
        print(f"[WARN] Real dataset '{DATASET_PATH}' not found.")
        if not use_synthetic_if_missing:
            raise FileNotFoundError(
                f"'{DATASET_PATH}' not found and synthetic fallback disabled. "
                "Download ASAP-AES and place it at this exact path."
            )
        dataset_path = generate_synthetic_dataset()
        is_real_data = False
    else:
        dataset_path = DATASET_PATH
        is_real_data = True
        print(f"[INFO] Found real dataset at {os.path.abspath(dataset_path)}")

    print(f"[INFO] Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    print(f"[INFO] Loaded {len(df)} rows.")

    # Normalize the text column name
    if "essay" not in df.columns:
        if "essay_text" in df.columns:
            df.rename(columns={"essay_text": "essay"}, inplace=True)
        else:
            found = False
            for col in df.columns:
                if df[col].dtype == object and df[col].str.len().mean() > 50:
                    df.rename(columns={col: "essay"}, inplace=True)
                    found = True
                    break
            if not found:
                raise ValueError(f"Could not identify an essay text column. Columns: {list(df.columns)}")

    # FIX: real label mapping instead of random-noise fallback
    if is_real_data:
        df = _map_real_labels(df)
    else:
        missing = [t for t in REQUIRED_TRAITS if t not in df.columns]
        if missing:
            raise ValueError(f"Synthetic dataset is missing expected columns: {missing}")

    print(f"[INFO] Extracting features for {len(df)} documents. This may take a moment...")
    X_list = []
    feature_names = get_feature_names()
    for text in df["essay"]:
        feats = extract_features(str(text))
        X_list.append([feats[name] for name in feature_names])
    X = np.array(X_list)

    # Sanity check: warn if features have near-zero variance (would explain
    # constant/near-constant scores regardless of the label-fixing above)
    feature_std = X.std(axis=0)
    low_variance = [feature_names[i] for i, s in enumerate(feature_std) if s < 1e-6]
    if low_variance:
        print(f"[WARNING] These features show ~zero variance across the dataset: {low_variance}. "
              "They will contribute nothing to differentiating scores between texts.")

    models = {}
    print("[INFO] Training Random Forest Regressors (80/20 train/test split per trait)...")
    for trait in REQUIRED_TRAITS:
        y = df[trait].values
        label_std = np.std(y)
        if label_std < 1e-6:
            print(f"[WARNING] Trait '{trait}' has ~zero variance in labels (std={label_std:.4f}). "
                  "The model cannot learn meaningful differences for this trait.")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        score = r2_score(y_test, preds)
        pred_std = np.std(preds)
        print(f"   '{trait}': R² = {score:.3f} | prediction std = {pred_std:.2f} "
              f"{'⚠ LOW — predictions barely vary, investigate' if pred_std < 1.0 else ''}")

        # Refit on full data for the final saved model
        model.fit(X, y)
        models[trait] = model

    checkpoint = {
        "models": models,
        "feature_names": feature_names,
        "trained_on_real_data": is_real_data,
    }

    print(f"[INFO] Saving trained models to {MODEL_PATH}...")
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(checkpoint, f)

    if not is_real_data:
        print("=" * 70)
        print("[REMINDER] This model was trained on SYNTHETIC smoke-test data.")
        print("           Re-run after placing the real asap_aes.csv for your final model.")
        print("=" * 70)
    print("[SUCCESS] Offline NLP models successfully trained and serialized!")


if __name__ == '__main__':
    train_model()