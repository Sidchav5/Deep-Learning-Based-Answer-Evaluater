# backend/routes/auth_routes.py
"""
Authentication API routes
"""
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from config import Config
from utils.auth import generate_token

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]
users_collection = db['users']


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'password', 'role']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400
        
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        
        # Validate role
        if role not in ['teacher', 'student']:
            return jsonify({'message': 'Invalid role. Must be "teacher" or "student"'}), 400
        
        # Check if user already exists
        if users_collection.find_one({'email': email}):
            return jsonify({'message': 'Email already registered'}), 409
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        # Create user document
        user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert into database
        result = users_collection.insert_one(user)
        user_id = str(result.inserted_id)
        
        # Generate token
        token = generate_token(user_id, email, role)
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'role': role
            }
        }), 201
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(field in data for field in ['email', 'password']):
            return jsonify({'message': 'Missing email or password'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        # Find user
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # Verify password
        if not check_password_hash(user['password'], password):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # Generate token
        user_id = str(user['_id'])
        token = generate_token(user_id, email, user['role'])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': f'Login failed: {str(e)}'}), 500


@auth_bp.route('/verify', methods=['GET'])
def verify():
    """Verify token validity"""
    from utils.auth import verify_token
    
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'message': 'Invalid token format'}), 401
    
    if not token:
        return jsonify({'message': 'Token is missing'}), 401
    
    payload = verify_token(token)
    if not payload:
        return jsonify({'message': 'Invalid or expired token'}), 401
    
    return jsonify({
        'message': 'Token is valid',
        'user': {
            'id': payload['user_id'],
            'email': payload['email'],
            'role': payload['role']
        }
    }), 200
