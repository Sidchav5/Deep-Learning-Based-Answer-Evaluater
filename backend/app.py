# backend/app.py - Flask Authentication Backend
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import jwt
import os

# Try to import ML dependencies (optional)
try:
    import numpy as np
    import joblib
    import torch
    import tensorflow as tf
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    ML_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML libraries not installed: {e}")
    print("⚠️ Install with: pip install -r requirements-ml.txt")
    ML_IMPORTS_AVAILABLE = False

# Try to import file processing libraries
try:
    import PyPDF2
    import docx
    import io
    FILE_PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ File processing libraries not installed: {e}")
    FILE_PROCESSING_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_EXPIRATION_HOURS'] = 24
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# MongoDB Connection
MONGO_URI = "mongodb+srv://DL_user:Edaigrp1@dl.pmyowfm.mongodb.net/"
try:
    client = MongoClient(MONGO_URI)
    db = client['dl_database']  # Database name
    users_collection = db['users']  # Users collection
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")

# Load ML Models
print("🔄 Loading ML models...")
models_loaded = False

if ML_IMPORTS_AVAILABLE:
    try:
        # Get the Model directory path
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Model')
        
        # Load ANN model with custom object scope to handle old Keras models
        try:
            import tf_keras
            ann_model = tf_keras.models.load_model(
                os.path.join(model_dir, 'ann_semantic_grader.h5'),
                compile=False
            )
        except Exception as e:
            print(f"Trying alternative loading method: {e}")
            # Try with tensorflow.keras
            ann_model = tf.keras.models.load_model(
                os.path.join(model_dir, 'ann_semantic_grader.h5'),
                compile=False,
                safe_mode=False  # Disable safe mode for older models
            )
        
        # Load scaler
        scaler = joblib.load(os.path.join(model_dir, 'feature_scaler.pkl'))
        
        # Load feature order
        FEATURES = joblib.load(os.path.join(model_dir, 'model_features.pkl'))
        
        # Load SBERT
        sbert = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Load NLI model
        nli_tokenizer = AutoTokenizer.from_pretrained("roberta-large-mnli")
        nli_model = AutoModelForSequenceClassification.from_pretrained("roberta-large-mnli")
        nli_model.eval()
        
        print("✅ ML Models loaded successfully!")
        models_loaded = True
    except Exception as e:
        print(f"⚠️ ML Models loading error: {e}")
        print("⚠️ Evaluation endpoint will not work until models are loaded")
        import traceback
        traceback.print_exc()
        models_loaded = False
else:
    print("⚠️ ML libraries not available. Install with: pip install -r requirements-ml.txt")
    models_loaded = False

# Helper function to generate JWT token
def generate_token(user_id, email, role):
    payload = {
        'user_id': str(user_id),
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# Helper function to verify JWT token
def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to extract text from files
def extract_text_from_file(file):
    """Extract text from uploaded file (TXT, PDF, DOC, DOCX)"""
    if not FILE_PROCESSING_AVAILABLE:
        return "File processing libraries not installed"
    
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.txt'):
            return file.read().decode('utf-8')
        
        elif filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        
        elif filename.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file.read()))
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return text
        
        elif filename.endswith('.doc'):
            # Basic DOC support (may need python-docx2txt for better support)
            return "DOC format not fully supported. Please use DOCX."
        
        else:
            return None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

# Batch evaluation parser functions
def parse_questions(text):
    """
    Parse questions from text format: "Q1: [5 marks] Question? | Q2: [10 marks] Question?"
    Returns: list of dicts with {number, question, marks}
    """
    import re
    questions = []
    
    # Find all questions using regex pattern
    # Pattern matches: Q<number>: [<marks> marks] <question text until next Q<number>: or end>
    # Use negative lookahead to only stop at "Q<digit>:", not just any 'Q'
    pattern = r'Q(\d+):\s*\[(\d+)\s*marks?\]\s*((?:(?!Q\d+:).)+)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        number = int(match.group(1))
        marks = float(match.group(2))
        question = match.group(3).strip()
        # Remove trailing pipes and extra whitespace
        question = re.sub(r'[\|\s]+$', '', question).strip()
        
        if question:
            questions.append({
                'number': number,
                'question': question,
                'marks': marks
            })
    
    return questions

def parse_answers(text):
    """
    Parse answers from text format: "A1: Answer text | A2: Answer text"
    Returns: list of dicts with {number, answer}
    """
    import re
    answers = []
    
    # Find all answers using regex pattern
    # Pattern matches: A<number>: <answer text until next A<number>: or end>
    # Use negative lookahead to only stop at "A<digit>:", not just any 'A'
    pattern = r'A(\d+):\s*((?:(?!A\d+:).)+)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        number = int(match.group(1))
        answer = match.group(2).strip()
        # Remove trailing pipes and extra whitespace
        answer = re.sub(r'[\|\s]+$', '', answer).strip()
        
        if answer:
            answers.append({
                'number': number,
                'answer': answer
            })
    
    return answers

def map_qa_pairs(questions, model_answers, student_answers):
    """
    Map questions to their corresponding model and student answers
    Returns: list of tuples (question_dict, model_answer, student_answer)
    """
    paired = []
    
    # Create lookup dictionaries
    model_dict = {a['number']: a['answer'] for a in model_answers}
    student_dict = {a['number']: a['answer'] for a in student_answers}
    
    for q in questions:
        q_num = q['number']
        model_ans = model_dict.get(q_num, '')
        student_ans = student_dict.get(q_num, '')
        
        if model_ans and student_ans:
            paired.append((q, model_ans, student_ans))
    
    return paired

# ML Helper Functions (only available if ML libraries are installed)
if ML_IMPORTS_AVAILABLE:
    def extract_features(student, reference, marks):
        """Extract features for ANN model"""
        if not models_loaded:
            raise Exception("ML models not loaded")
        
        emb_student = sbert.encode(student)
        emb_ref = sbert.encode(reference)
        
        similarity = cosine_similarity(
            emb_student.reshape(1, -1),
            emb_ref.reshape(1, -1)
        )[0][0]
        
        distance = np.linalg.norm(emb_student - emb_ref)
        
        len_student = len(student.split())
        len_ref = max(len(reference.split()), 1)
        
        length_ratio = len_student / len_ref
        
        coverage = similarity * min(length_ratio, 1.0)
        
        features = np.array([
            similarity,
            distance,
            length_ratio,
            coverage,
            marks
        ]).reshape(1, -1)
        
        return features, similarity

    def nli_inference(student, reference):
        """Perform NLI inference using RoBERTa-MNLI"""
        if not models_loaded:
            raise Exception("ML models not loaded")
        
        inputs = nli_tokenizer(
            reference,
            student,
            return_tensors="pt",
            truncation=True,
            padding=True
        )
        
        with torch.no_grad():
            logits = nli_model(**inputs).logits
        
        probs = torch.softmax(logits, dim=1)[0].numpy()
        
        labels = ["CONTRADICTION", "NEUTRAL", "ENTAILMENT"]
        
        result = labels[np.argmax(probs)]
        
        return result, probs

    def evaluate_answer(question, reference, student, marks):
        """Main evaluation function"""
        if not models_loaded:
            raise Exception("ML models not loaded")
        
        # Extract features
        features, similarity = extract_features(student, reference, marks)
        
        # Semantic gate
        if similarity < 0.30:
            return {
                'finalScore': 0.0,
                'maxMarks': marks,
                'similarity': similarity,
                'nliLabel': 'LOW_SIMILARITY',
                'feedback': 'The answer has low semantic relevance to the model answer.'
            }
        
        # Scale features and predict with ANN
        features_scaled = scaler.transform(features)
        ann_score = ann_model.predict(features_scaled, verbose=0)[0][0]
        
        # NLI inference
        nli_label, probs = nli_inference(student, reference)
        
        # Hybrid scoring: Blend ANN prediction with similarity-based score
        # For high similarity (>0.8), give more weight to similarity
        similarity_score = similarity * marks  # Direct proportional score
        
        # Weighted blend based on similarity level
        if similarity >= 0.85:
            # High similarity: 70% similarity-based, 30% ANN
            blended_score = 0.7 * similarity_score + 0.3 * ann_score
        elif similarity >= 0.75:
            # Medium-high similarity: 50-50 blend
            blended_score = 0.5 * similarity_score + 0.5 * ann_score
        else:
            # Lower similarity: trust ANN more
            blended_score = 0.3 * similarity_score + 0.7 * ann_score
        
        # Fusion logic with NLI
        if nli_label == "CONTRADICTION":
            final_score = blended_score * 0.3
            feedback = "The answer contradicts the model answer."
        elif nli_label == "NEUTRAL":
            final_score = blended_score * 0.7
            feedback = "The answer is partially related to the model answer."
        elif nli_label == "ENTAILMENT":
            final_score = blended_score * 1.0
            feedback = "The answer is well-aligned with the model answer."
        else:
            final_score = blended_score
            feedback = "Answer evaluated successfully."
        
        # Ensure score is within bounds
        final_score = max(0, min(final_score, marks))
        
        # Round to nearest integer: 3.5+ → 4, <3.5 → 3
        final_score = round(final_score)
        
        return {
            'finalScore': int(final_score),  # Already rounded, convert to int
            'maxMarks': marks,
            'similarity': round(float(similarity), 4),
            'nliLabel': nli_label,
            'feedback': feedback
        }

# Routes
@app.route('/')
def home():
    return jsonify({
        'message': 'AI Answer Evaluator API',
        'status': 'running',
        'endpoints': ['/api/signup', '/api/login', '/api/verify']
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(key in data for key in ['name', 'email', 'password', 'role']):
            return jsonify({'message': 'Missing required fields'}), 400
        
        name = data['name']
        email = data['email'].lower().strip()
        password = data['password']
        role = data['role']
        
        # Validate role
        if role not in ['student', 'teacher']:
            return jsonify({'message': 'Invalid role. Must be student or teacher'}), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return jsonify({'message': 'Email already registered'}), 409
        
        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create user document
        user_doc = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert user into database
        result = users_collection.insert_one(user_doc)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': str(result.inserted_id),
            'role': role
        }), 201
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(key in data for key in ['email', 'password']):
            return jsonify({'message': 'Email and password required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user by email
        user = users_collection.find_one({'email': email})
        
        if not user:
            return jsonify({'message': 'Invalid email or password'}), 401
        
        # Check password
        if not check_password_hash(user['password'], password):
            return jsonify({'message': 'Invalid email or password'}), 401
        
        # Generate JWT token
        token = generate_token(user['_id'], user['email'], user['role'])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/verify', methods=['GET'])
def verify():
    """Verify JWT token from Authorization header"""
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401
        
        # Get user details from database
        user = users_collection.find_one({'_id': payload['user_id']})
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({
            'valid': True,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        print(f"Verification error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (for testing purposes)"""
    try:
        users = list(users_collection.find({}, {'password': 0}))  # Exclude password field
        
        # Convert ObjectId to string
        for user in users:
            user['_id'] = str(user['_id'])
        
        return jsonify({
            'count': len(users),
            'users': users
        }), 200
        
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """Evaluate student answers against model answers (batch processing)"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401
        
        # Check if models are loaded
        if not models_loaded:
            return jsonify({'message': 'ML models not loaded. Please contact administrator.'}), 503
        
        # Get form data
        upload_mode = request.form.get('uploadMode', 'file')
        
        # Extract text based on upload mode
        if upload_mode == 'file':
            # File upload mode
            if 'questionsFile' not in request.files or 'modelAnswersFile' not in request.files or 'studentAnswersFile' not in request.files:
                return jsonify({'message': 'Missing required files'}), 400
            
            questions_file = request.files['questionsFile']
            model_answers_file = request.files['modelAnswersFile']
            student_answers_file = request.files['studentAnswersFile']
            
            # Validate files
            if not all([allowed_file(f.filename) for f in [questions_file, model_answers_file, student_answers_file]]):
                return jsonify({'message': 'Invalid file format. Allowed: TXT, PDF, DOC, DOCX'}), 400
            
            # Extract text from files
            questions_text = extract_text_from_file(questions_file)
            model_answers_text = extract_text_from_file(model_answers_file)
            student_answers_text = extract_text_from_file(student_answers_file)
            
            if not all([questions_text, model_answers_text, student_answers_text]):
                return jsonify({'message': 'Error extracting text from files'}), 400
        
        else:
            # Text input mode
            questions_text = request.form.get('questionsText', '').strip()
            model_answers_text = request.form.get('modelAnswersText', '').strip()
            student_answers_text = request.form.get('studentAnswersText', '').strip()
            
            if not all([questions_text, model_answers_text, student_answers_text]):
                return jsonify({'message': 'Missing required text fields'}), 400
        
        # Parse questions and answers
        try:
            questions = parse_questions(questions_text)
            model_answers = parse_answers(model_answers_text)
            student_answers = parse_answers(student_answers_text)
            
            if not questions:
                return jsonify({'message': 'No valid questions found. Use format: Q1: [5 marks] Question?'}), 400
            
            if not model_answers:
                return jsonify({'message': 'No valid model answers found. Use format: A1: Answer text'}), 400
            
            if not student_answers:
                return jsonify({'message': 'No valid student answers found. Use format: A1: Answer text'}), 400
            
        except Exception as e:
            return jsonify({'message': f'Parsing error: {str(e)}'}), 400
        
        # Map questions to answers
        qa_pairs = map_qa_pairs(questions, model_answers, student_answers)
        
        if not qa_pairs:
            return jsonify({'message': 'No matching question-answer pairs found. Ensure question and answer numbers match.'}), 400
        
        # Evaluate each Q&A pair
        results_list = []
        total_score = 0
        total_max_marks = 0
        total_similarity = 0
        
        for q_dict, model_ans, student_ans in qa_pairs:
            # Perform evaluation
            eval_result = evaluate_answer(
                question=q_dict['question'],
                reference=model_ans,
                student=student_ans,
                marks=q_dict['marks']
            )
            
            # Build result object for this question
            question_result = {
                'questionNumber': q_dict['number'],
                'question': q_dict['question'],
                'modelAnswer': model_ans,
                'studentAnswer': student_ans,
                'score': eval_result['finalScore'],
                'maxMarks': eval_result['maxMarks'],
                'similarity': eval_result['similarity'],
                'nliLabel': eval_result['nliLabel'].lower().replace('_', ' '),
                'feedback': eval_result['feedback']
            }
            
            results_list.append(question_result)
            total_score += eval_result['finalScore']
            total_max_marks += eval_result['maxMarks']
            total_similarity += eval_result['similarity']
        
        # Calculate overall metrics
        total_questions = len(results_list)
        percentage = (total_score / total_max_marks * 100) if total_max_marks > 0 else 0
        average_similarity = total_similarity / total_questions if total_questions > 0 else 0
        
        # Build response
        response = {
            'message': 'Evaluation completed successfully',
            'totalScore': round(total_score, 2),
            'totalMaxMarks': total_max_marks,
            'percentage': round(percentage, 2),
            'totalQuestions': total_questions,
            'averageSimilarity': round(average_similarity, 4),
            'questions': results_list
        }
        
        # Log evaluation for analytics (optional)
        evaluation_log = {
            'user_id': payload['user_id'],
            'total_questions': total_questions,
            'total_score': total_score,
            'total_max_marks': total_max_marks,
            'percentage': percentage,
            'timestamp': datetime.utcnow()
        }
        # You can store this in MongoDB if needed
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Evaluation error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
