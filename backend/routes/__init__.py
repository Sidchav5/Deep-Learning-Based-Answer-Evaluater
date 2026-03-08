# backend/routes/__init__.py
from .auth_routes import auth_bp
from .evaluation_routes import eval_bp

__all__ = ['auth_bp', 'eval_bp']
