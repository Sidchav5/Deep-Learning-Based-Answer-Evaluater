# backend/config/settings.py
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application Configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # JWT Configuration
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    JWT_ALGORITHM = 'HS256'
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://DL_user:Edaigrp1@dl.pmyowfm.mongodb.net/')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'dl_database')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
    
    # ML Models Configuration
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Model')
    ANN_MODEL_PATH = os.path.join(MODEL_DIR, 'ann_semantic_grader.h5')
    SCALER_PATH = os.path.join(MODEL_DIR, 'feature_scaler.pkl')
    FEATURES_PATH = os.path.join(MODEL_DIR, 'model_features.pkl')
    
    # SBERT Configuration
    SBERT_MODEL_NAME = 'all-MiniLM-L6-v2'
    
    # NLI Configuration
    NLI_MODEL_NAME = 'roberta-large-mnli'
    
    # Groq API Configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    GROQ_MAX_TOKENS = int(os.getenv('GROQ_MAX_TOKENS', 1024))
    GROQ_TEMPERATURE = float(os.getenv('GROQ_TEMPERATURE', 0.3))
    
    # RAG Configuration
    RAG_ENABLED = os.getenv('RAG_ENABLED', 'True').lower() == 'true'
    RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', 500))
    RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', 50))
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', 3))
    RAG_SIMILARITY_THRESHOLD = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.3))
    
    # Vector Store Configuration
    VECTOR_STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vector_store')
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Create necessary directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.VECTOR_STORE_PATH, exist_ok=True)

# Development configuration
class DevelopmentConfig(Config):
    DEBUG = True

# Production configuration
class ProductionConfig(Config):
    DEBUG = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
