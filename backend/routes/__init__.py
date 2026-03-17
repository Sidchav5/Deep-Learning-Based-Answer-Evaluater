# backend/routes/__init__.py
from .auth_routes import auth_bp
from .evaluation_routes import eval_bp
from .workflow_routes import workflow_bp

__all__ = ['auth_bp', 'eval_bp', 'workflow_bp']
