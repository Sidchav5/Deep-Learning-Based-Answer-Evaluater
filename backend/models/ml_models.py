# backend/models/ml_models.py
"""
ML Models Loader and Manager
Handles loading and caching of SBERT, NLI, and ANN models
"""
import os
import numpy as np
import joblib
import torch
import tensorflow as tf
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics.pairwise import cosine_similarity

from config import Config


class MLModels:
    """Singleton class to manage ML models"""
    
    _instance = None
    _models_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLModels, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._models_loaded:
            self.ann_model = None
            self.scaler = None
            self.features = None
            self.sbert = None
            self.nli_tokenizer = None
            self.nli_model = None
            self.load_models()
    
    def load_models(self):
        """Load all ML models"""
        print("🔄 Loading ML models...")
        
        try:
            # Load ANN model
            self._load_ann_model()
            
            # Load scaler and features
            self._load_scaler_and_features()
            
            # Load SBERT model
            self._load_sbert()
            
            # Load NLI model
            self._load_nli_model()
            
            self._models_loaded = True
            print("✅ All ML models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading ML models: {e}")
            import traceback
            traceback.print_exc()
            self._models_loaded = False
    
    def _load_ann_model(self):
        """Load ANN semantic grader model"""
        try:
            print("Loading ANN model...")
            # Try with tf_keras first
            try:
                import tf_keras
                self.ann_model = tf_keras.models.load_model(
                    Config.ANN_MODEL_PATH,
                    compile=False
                )
            except Exception as e:
                print(f"Trying alternative loading method: {e}")
                # Try with tensorflow.keras
                self.ann_model = tf.keras.models.load_model(
                    Config.ANN_MODEL_PATH,
                    compile=False,
                    safe_mode=False
                )
            print("✅ ANN model loaded")
        except Exception as e:
            raise Exception(f"Failed to load ANN model: {e}")
    
    def _load_scaler_and_features(self):
        """Load StandardScaler and feature definitions"""
        try:
            print("Loading scaler and features...")
            self.scaler = joblib.load(Config.SCALER_PATH)
            self.features = joblib.load(Config.FEATURES_PATH)
            print(f"✅ Scaler and features loaded: {self.features}")
        except Exception as e:
            raise Exception(f"Failed to load scaler/features: {e}")
    
    def _load_sbert(self):
        """Load Sentence-BERT model"""
        try:
            print(f"Loading SBERT model: {Config.SBERT_MODEL_NAME}...")
            self.sbert = SentenceTransformer(Config.SBERT_MODEL_NAME)
            print("✅ SBERT model loaded")
        except Exception as e:
            raise Exception(f"Failed to load SBERT: {e}")
    
    def _load_nli_model(self):
        """Load NLI (Natural Language Inference) model"""
        try:
            print(f"Loading NLI model: {Config.NLI_MODEL_NAME}...")
            self.nli_tokenizer = AutoTokenizer.from_pretrained(Config.NLI_MODEL_NAME)
            self.nli_model = AutoModelForSequenceClassification.from_pretrained(Config.NLI_MODEL_NAME)
            self.nli_model.eval()
            print("✅ NLI model loaded")
        except Exception as e:
            raise Exception(f"Failed to load NLI model: {e}")
    
    @property
    def is_loaded(self):
        """Check if all models are loaded"""
        return self._models_loaded
    
    def extract_features(self, student, reference, marks):
        """Extract features for ANN model"""
        if not self._models_loaded:
            raise Exception("ML models not loaded")
        
        # Generate embeddings
        emb_student = self.sbert.encode(student)
        emb_ref = self.sbert.encode(reference)
        
        # Calculate similarity
        similarity = cosine_similarity(
            emb_student.reshape(1, -1),
            emb_ref.reshape(1, -1)
        )[0][0]
        
        # Calculate distance
        distance = np.linalg.norm(emb_student - emb_ref)
        
        # Calculate length ratio
        len_student = len(student.split())
        len_ref = max(len(reference.split()), 1)
        length_ratio = len_student / len_ref
        
        # Calculate coverage
        coverage = similarity * min(length_ratio, 1.0)
        
        # Create feature array
        features = np.array([
            similarity,
            distance,
            length_ratio,
            coverage,
            marks
        ]).reshape(1, -1)
        
        return features, similarity
    
    def nli_inference(self, student, reference):
        """Perform NLI inference using RoBERTa-MNLI"""
        if not self._models_loaded:
            raise Exception("ML models not loaded")
        
        # Tokenize input
        inputs = self.nli_tokenizer(
            reference,
            student,
            return_tensors="pt",
            truncation=True,
            padding=True
        )
        
        # Perform inference
        with torch.no_grad():
            logits = self.nli_model(**inputs).logits
        
        # Get probabilities
        probs = torch.softmax(logits, dim=1)[0]
        
        # Map to labels
        label_mapping = ['CONTRADICTION', 'NEUTRAL', 'ENTAILMENT']
        predicted_label = label_mapping[torch.argmax(probs).item()]
        confidence = probs.max().item()
        
        return predicted_label, confidence
    
    def predict_score(self, features):
        """Predict score using ANN model"""
        if not self._models_loaded:
            raise Exception("ML models not loaded")
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.ann_model.predict(features_scaled, verbose=0)[0][0]
        
        return float(prediction)
    
    def get_embeddings(self, text):
        """Get SBERT embeddings for text"""
        if not self._models_loaded:
            raise Exception("ML models not loaded")
        
        return self.sbert.encode(text)


# Create singleton instance
ml_models = MLModels()
