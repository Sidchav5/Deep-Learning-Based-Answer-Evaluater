# backend/main.py - Refactored Flask Application
"""
Main Flask application entry point
Clean, modular architecture using external Llama pipeline
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, config
from routes import auth_bp, eval_bp, workflow_bp
from services import llama_service


def create_app(config_name='development'):
    """
    Application factory pattern
    
    Args:
        config_name: Configuration environment ('development' or 'production')
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    Config.init_app(app)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(eval_bp)
    app.register_blueprint(workflow_bp)
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'message': 'AI Answer Evaluation API',
            'version': '2.0',
            'status': 'running',
            'features': {
                'authentication': True,
                'batch_evaluation': True,
                'llama_pipeline': llama_service.is_available(),
                'local_models_loaded': False
            }
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'message': 'Internal server error'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'message': 'Access forbidden'}), 403
    
    return app


def initialize_services():
    """Initialize application services"""
    print("\n" + "="*60)
    print("🚀 Starting AI Answer Evaluation System")
    print("="*60 + "\n")
    
    # Check configuration
    print("📋 Configuration:")
    print(f"   - Environment: {'Development' if Config.DEBUG else 'Production'}")
    print(f"   - Llama API URL: {'✅ Configured' if llama_service.is_available() else '❌ Not configured'}")
    print()
    print("✅ Local model loading disabled (using external Llama pipeline).\n")
    
    print("="*60)
    print("🎉 Application ready!")
    print("="*60 + "\n")


if __name__ == '__main__':
    # Initialize services
    initialize_services()
    
    # Create application
    app = create_app('development')
    
    # Run application
    print(f"🌐 Server starting on http://localhost:5000")
    print(f"📚 API Documentation: http://localhost:5000/\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # Disable reloader to prevent model reloading
    )
