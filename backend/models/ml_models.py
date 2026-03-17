# backend/models/ml_models.py
"""
ML Models Loader and Manager
Handles loading and caching of SBERT, NLI, and ANN models
"""
import os
import json
import numpy as np
import joblib
import torch
import tensorflow as tf
import h5py
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
            self.load_errors = {}
            self.load_models()
    
    def load_models(self):
        """Load all ML models"""
        print("🔄 Loading ML models...")

        self.load_errors = {}
        self.ann_model = None
        self.scaler = None
        self.features = None
        self.sbert = None
        self.nli_tokenizer = None
        self.nli_model = None

        try:
            self._load_ann_model()
        except Exception as e:
            self.load_errors['ann'] = str(e)
            print(f"❌ ANN load failed: {e}")

        try:
            self._load_scaler_and_features()
        except Exception as e:
            self.load_errors['scaler_features'] = str(e)
            print(f"❌ Scaler/features load failed: {e}")

        try:
            self._load_sbert()
        except Exception as e:
            self.load_errors['sbert'] = str(e)
            print(f"❌ SBERT load failed: {e}")

        try:
            self._load_nli_model()
        except Exception as e:
            self.load_errors['nli'] = str(e)
            print(f"⚠️ NLI load failed, fallback mode enabled: {e}")

        required_loaded = all([
            self.ann_model is not None,
            self.scaler is not None,
            self.features is not None,
            self.sbert is not None
        ])

        self._models_loaded = required_loaded

        if self._models_loaded:
            if self.nli_model is None or self.nli_tokenizer is None:
                print("✅ Core ML models loaded (without NLI fallback)")
            else:
                print("✅ All ML models loaded successfully!")
        else:
            print("❌ Core ML models are not fully loaded")
    
    def _load_ann_model(self):
        """Load ANN semantic grader model"""
        try:
            print("Loading ANN model...")
            # Prefer standalone keras (model was saved with keras 3.x)
            try:
                import keras
                self.ann_model = keras.models.load_model(
                    Config.ANN_MODEL_PATH,
                    compile=False
                )
            except Exception as e:
                print(f"Trying alternative loading method: {e}")
                try:
                    # Try with tensorflow.keras
                    self.ann_model = tf.keras.models.load_model(
                        Config.ANN_MODEL_PATH,
                        compile=False,
                        safe_mode=False
                    )
                except Exception as e2:
                    print(f"Trying legacy H5 compatibility mode: {e2}")

                    with h5py.File(Config.ANN_MODEL_PATH, 'r') as model_file:
                        model_config = model_file.attrs.get('model_config')
                        if model_config is None:
                            raise Exception('model_config not found in H5 file')

                        if isinstance(model_config, bytes):
                            model_config = model_config.decode('utf-8')

                    config_json = json.loads(model_config)

                    def patch_input_layers(node):
                        if isinstance(node, dict):
                            class_name = node.get('class_name')
                            config = node.get('config')
                            if class_name == 'InputLayer' and isinstance(config, dict):
                                if 'batch_shape' in config and 'batch_input_shape' not in config:
                                    config['batch_input_shape'] = config.pop('batch_shape')

                            for value in node.values():
                                patch_input_layers(value)
                        elif isinstance(node, list):
                            for item in node:
                                patch_input_layers(item)

                    patch_input_layers(config_json)

                    patched_config = json.dumps(config_json)

                    try:
                        import keras
                        self.ann_model = keras.models.model_from_json(patched_config)
                        self.ann_model.load_weights(Config.ANN_MODEL_PATH)
                    except Exception as e3:
                        print(f"keras model_from_json failed: {e3}")
                        self.ann_model = tf.keras.models.model_from_json(patched_config)
                        self.ann_model.load_weights(Config.ANN_MODEL_PATH)
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

    def ensure_loaded(self, force_reload=False):
        """Ensure core models are loaded, with optional force reload"""
        if force_reload or not self._models_loaded:
            self.load_models()
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

        if self.nli_tokenizer is None or self.nli_model is None:
            return "NEUTRAL", 0.0
        
        # Tokenize input
        try:
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
        except Exception:
            return "NEUTRAL", 0.0
    
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
