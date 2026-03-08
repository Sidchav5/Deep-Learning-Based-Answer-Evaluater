# backend/utils/auth.py
"""
Authentication utilities for JWT token management
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from functools import wraps
from flask import request, jsonify

from config import Config


def generate_token(user_id: str, email: str, role: str) -> str:
    """
    Generate JWT token for user
    
    Args:
        user_id: User's unique ID
        email: User's email
        role: User's role (e.g., 'teacher', 'student')
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': str(user_id),
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """
    Decorator to protect routes that require authentication
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'message': 'Access granted'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Extract token from "Bearer <token>"
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401
        
        # Pass payload to the route function
        return f(payload, *args, **kwargs)
    
    return decorated


def role_required(required_role: str):
    """
    Decorator to protect routes that require a specific role
    
    Usage:
        @app.route('/admin')
        @role_required('admin')
        def admin_route(current_user):
            return jsonify({'message': 'Admin access granted'})
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            # Get token from Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(' ')[1]
                except IndexError:
                    return jsonify({'message': 'Invalid token format'}), 401
            
            if not token:
                return jsonify({'message': 'Token is missing'}), 401
            
            # Verify token
            payload = verify_token(token)
            if not payload:
                return jsonify({'message': 'Invalid or expired token'}), 401
            
            # Check role
            if payload.get('role') != required_role:
                return jsonify({'message': 'Insufficient permissions'}), 403
            
            return f(payload, *args, **kwargs)
        
        return decorated
    return decorator
