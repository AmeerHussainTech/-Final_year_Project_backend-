import os
import json
import math
import numpy as np

class CustomTfidfVectorizer:
    """
    Custom Unigram & Bigram TF-IDF Vectorizer with feature fusion.
    Extracts vocabulary phrases and merges them with structural metadata.
    """
    def __init__(self, max_features=1000):
        self.max_features = max_features
        self.vocabulary_ = {}
        self.idf_ = []
        self.stop_words = set([
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'to', 'of', 'in', 'for', 
            'with', 'by', 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 
            'we', 'our', 'us', 'you', 'your', 'he', 'she', 'him', 'her', 'i', 'my', 'me'
        ])

    def _tokenize(self, text):
        words = text.lower().replace('\n', ' ').replace('\r', ' ')
        for char in '.,!?;:"()[]{}@#$/\\-+=_*&^%':
            words = words.replace(char, ' ')
        unigrams = [w.strip() for w in words.split() if w.strip()]
        
        # Build clean unigrams excluding stop words
        clean_unigrams = [w for w in unigrams if w not in self.stop_words]
        
        # Build bigrams excluding stop word pairs (if both words are stop words)
        bigrams = []
        for i in range(len(unigrams) - 1):
            w1 = unigrams[i]
            w2 = unigrams[i+1]
            if w1 not in self.stop_words or w2 not in self.stop_words:
                bigrams.append(f"{w1} {w2}")
                
        return clean_unigrams + bigrams

    def _extract_metadata(self, text):
        # 1. Word count
        words = text.lower().split()
        word_count = len(words)
        
        # 2. Slide dividers
        slide_markers = ['slide', 'page', 'agenda', 'conclusion', 'introduction', 'summary']
        slide_count = sum(text.lower().count(m) for m in slide_markers)
        slide_count += text.count('#')
        
        # 3. Filler word density
        fillers = ['um', 'uh', 'like', 'you know', 'basically', 'actually', 'so']
        filler_count = sum(text.lower().count(f) for f in fillers)
        filler_density = (filler_count / word_count) if word_count > 0 else 0
        
        # 4. Bullet points & list markers
        bullet_count = text.count('*') + text.count('-') + text.count('1.') + text.count('2.')
        
        # 5. Vocabulary richness
        unique_words = len(set(words))
        vocab_richness = (unique_words / word_count) if word_count > 0 else 0
        
        # Scale inputs roughly between 0.0 and 1.0
        return np.array([
            min(1.0, word_count / 400.0),
            min(1.0, slide_count / 10.0),
            min(1.0, filler_density * 10.0),
            min(1.0, bullet_count / 20.0),
            vocab_richness
        ])

    def fit(self, raw_documents):
        tokenized_docs = [self._tokenize(doc) for doc in raw_documents]
        
        # Count document frequency (DF) for each word
        word_df = {}
        for doc in tokenized_docs:
            seen = set(doc)
            for word in seen:
                word_df[word] = word_df.get(word, 0) + 1
                
        # Sort words by DF to pick top features
        sorted_words = sorted(word_df.items(), key=lambda x: x[1], reverse=True)
        top_words = [w[0] for w in sorted_words[:self.max_features]]
        
        self.vocabulary_ = {word: i for i, word in enumerate(top_words)}
        
        # Calculate IDF values
        num_docs = len(raw_documents)
        self.idf_ = []
        for word in top_words:
            df = word_df[word]
            # Standard IDF formula with smoothing: log((1 + num_docs) / (1 + df)) + 1
            idf_val = math.log((1 + num_docs) / (1 + df)) + 1
            self.idf_.append(idf_val)
            
        self.idf_ = np.array(self.idf_)
        return self

    def transform(self, raw_documents):
        num_docs = len(raw_documents)
        num_features = len(self.vocabulary_)
        X_tfidf = np.zeros((num_docs, num_features))
        X_meta = np.zeros((num_docs, 5))
        
        for idx, doc in enumerate(raw_documents):
            # Extract TF-IDF
            tokens = self._tokenize(doc)
            if tokens:
                term_count = {}
                for token in tokens:
                    if token in self.vocabulary_:
                        term_count[token] = term_count.get(token, 0) + 1
                for token, count in term_count.items():
                    feat_idx = self.vocabulary_[token]
                    X_tfidf[idx, feat_idx] = (count / len(tokens)) * self.idf_[feat_idx]
            
            # Extract metadata
            X_meta[idx] = self._extract_metadata(doc)
            
        # L2 normalization of TF-IDF vectors
        norms = np.linalg.norm(X_tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        X_tfidf = X_tfidf / norms
        
        # Concatenate TF-IDF and structural metadata vectors
        return np.hstack([X_tfidf, X_meta])

    def fit_transform(self, raw_documents):
        return self.fit(raw_documents).transform(raw_documents)


class CustomRidgeRegressor:
    """
    Custom Ridge Regression implemented using the analytic normal equations in NumPy:
    beta = (X^T X + alpha * I)^-1 X^T Y
    """
    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.weights_ = None
        self.intercept_ = None

    def fit(self, X, Y):
        num_samples = X.shape[0]
        # Append bias term (column of 1s) to feature matrix X
        X_bias = np.hstack([np.ones((num_samples, 1)), X])
        
        num_features = X_bias.shape[1]
        I = np.eye(num_features)
        # Do not regularize the intercept term
        I[0, 0] = 0.0
        
        # XtX matrix formulation
        XtX = X_bias.T @ X_bias
        XtY = X_bias.T @ Y
        
        # solve analytical normal equation: (XtX + alpha * I) @ beta = XtY
        beta = np.linalg.solve(XtX + self.alpha * I, XtY)
        
        self.intercept_ = beta[0]
        self.weights_ = beta[1:]
        return self

    def predict(self, X):
        return X @ self.weights_ + self.intercept_


def train_model():
    """
    Load generated synthetic presentation reviews, vectorize text, and train Custom Ridge models.
    """
    dataset_path = 'instance/synthetic_dataset.json'
    
    if not os.path.exists(dataset_path):
        print(f"[ERROR] Dataset file '{dataset_path}' not found.")
        print("Please run 'python generate_dataset.py' to generate the training dataset first.")
        return
        
    print(f"[INFO] Loading dataset from {dataset_path}...")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"[INFO] Loaded {len(data)} presentation samples.")
    
    texts = [sample['text'] for sample in data]
    
    # 1. Prepare Y metrics for scores
    score_keys = [
        "Structure", "Clarity", "Persuasion", "Content_Quality", "Call_to_Action",
        "Grammar_and_Syntax", "Accuracy", "Tone_Appropriateness", "Audience_Alignment",
        "Purpose_Fulfillment", "overall_score"
    ]
    
    Y_scores = []
    for sample in data:
        row = [sample['scores'].get(key, 50) for key in score_keys]
        Y_scores.append(row)
    Y_scores = np.array(Y_scores)
    
    # 2. Prepare Y metrics for 7Cs evaluation
    cs_keys = ["Clear", "Concise", "Correct", "Complete", "Courteous", "Concrete", "Consistent"]
    Y_cs = []
    for sample in data:
        row = [sample['seven_cs'].get(key, 1) for key in cs_keys]
        Y_cs.append(row)
    Y_cs = np.array(Y_cs)
    
    # 3. Prepare Y metrics for context classification
    context_keys = [
        "Academic Thesis Defense",
        "Sales Pitch",
        "Corporate Business Proposal",
        "Technical Architecture Review",
        "Educational Lecture"
    ]
    context_map = {name: idx for idx, name in enumerate(context_keys)}
    
    Y_contexts = []
    for sample in data:
        row = [0] * len(context_keys)
        ctx_name = sample.get('context', 'Educational Lecture')
        if ctx_name in context_map:
            row[context_map[ctx_name]] = 1
        else:
            row[context_map["Educational Lecture"]] = 1
        Y_contexts.append(row)
    Y_contexts = np.array(Y_contexts)
    
    # ===== VECTORIZE TEXT & FUSE METADATA =====
    print("[INFO] Fitting Unigram & Bigram TF-IDF Vectorizer with structural feature fusion...")
    vectorizer = CustomTfidfVectorizer(max_features=1000)
    X_features = vectorizer.fit_transform(texts)
    
    # ===== TRAIN SCORE MODEL =====
    print("[INFO] Training Custom Ridge Regressor for numeric scores...")
    score_model = CustomRidgeRegressor(alpha=1.0)
    score_model.fit(X_features, Y_scores)
    
    # Validate Score predictions
    pred_scores = score_model.predict(X_features)
    pred_scores = np.clip(pred_scores, 10, 100)
    mae = np.mean(np.abs(Y_scores - pred_scores))
    print(f"   Score Prediction MAE: {mae:.2f} points")
    
    # ===== TRAIN 7Cs CLASSIFIER =====
    print("[INFO] Training Custom Ridge Classifier for 7Cs binary parameters...")
    cs_model = CustomRidgeRegressor(alpha=1.0)
    cs_model.fit(X_features, Y_cs)
    
    # Validate binary evaluations
    pred_cs = cs_model.predict(X_features)
    pred_cs_binary = (pred_cs >= 0.5).astype(int)
    cs_mae = np.mean(np.abs(Y_cs - pred_cs_binary))
    print(f"   7Cs Classifier binary MAE: {cs_mae:.2f}")
    
    # ===== TRAIN CONTEXT CLASSIFIER =====
    print("[INFO] Training Custom Ridge Classifier for presentation contexts...")
    context_model = CustomRidgeRegressor(alpha=1.0)
    context_model.fit(X_features, Y_contexts)
    
    # Validate context predictions
    pred_contexts = context_model.predict(X_features)
    pred_indices = np.argmax(pred_contexts, axis=1)
    true_indices = np.argmax(Y_contexts, axis=1)
    context_accuracy = np.mean(pred_indices == true_indices)
    print(f"   Context Classifier Accuracy: {context_accuracy * 100:.2f}%")
    
    # ===== SAVE MODELS =====
    model_checkpoint = {
        "vocabulary": vectorizer.vocabulary_,
        "idf": vectorizer.idf_.tolist(),
        "score_weights": score_model.weights_.tolist(),
        "score_intercept": score_model.intercept_.tolist(),
        "cs_weights": cs_model.weights_.tolist(),
        "cs_intercept": cs_model.intercept_.tolist(),
        "context_weights": context_model.weights_.tolist(),
        "context_intercept": context_model.intercept_.tolist(),
        "score_keys": score_keys,
        "cs_keys": cs_keys,
        "context_keys": context_keys
    }
    
    os.makedirs('instance', exist_ok=True)
    model_save_path = 'instance/custom_nlp_model.json'
    print(f"[INFO] Saving trained model checkpoint to {model_save_path}...")
    with open(model_save_path, 'w', encoding='utf-8') as f:
        json.dump(model_checkpoint, f, indent=2)
        
    print("[SUCCESS] Custom NLP module trained successfully and saved locally!")

if __name__ == "__main__":
    train_model()
    

