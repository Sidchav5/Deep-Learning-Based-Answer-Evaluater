# backend/routes/evaluation_routes.py
"""
Evaluation API routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from pymongo import MongoClient

from config import Config
from utils.auth import token_required
from utils.parsers import parse_questions, parse_answers
from utils.file_processing import extract_text_from_file, allowed_file
from services import evaluation_service, llama_service


def convert_numpy_types(obj):
    """Convert complex objects into JSON-safe values"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    if hasattr(obj, 'item'):
        try:
            return obj.item()
        except Exception:
            return obj
    return obj

# Create Blueprint
eval_bp = Blueprint('evaluation', __name__, url_prefix='/api')

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]


@eval_bp.route('/generate-answer', methods=['POST'])
@token_required
def generate_answer(payload):
    """Generate answer for a question using Llama pipeline"""
    try:
        # Get JSON data
        data = request.get_json()
        print(f"[GENERATE-ANSWER] Received data: {data}")
        
        if not data:
            print("[GENERATE-ANSWER] ERROR: No JSON data provided")
            return jsonify({'message': 'Request body must be JSON'}), 400
        
        question = data.get('question', '').strip()
        marks = data.get('marks', 5)
        
        print(f"[GENERATE-ANSWER] Question: {question}, Marks: {marks}")
        
        if not question:
            print("[GENERATE-ANSWER] ERROR: Question is empty")
            return jsonify({'message': 'Question is required'}), 400
        
        # Check if Llama API is available
        if not llama_service.is_available():
            print("[GENERATE-ANSWER] ERROR: Llama API not configured")
            return jsonify({'message': 'Llama API is not configured or unavailable'}), 503
        
        print(f"[GENERATE-ANSWER] Calling Llama API with question: {question[:50]}...")
        # Call Llama service to generate answer
        result = llama_service.generate_answer(question, marks)
        
        print(f"[GENERATE-ANSWER] Llama result: {result}")
        
        if not result:
            print("[GENERATE-ANSWER] ERROR: Llama returned None")
            return jsonify({'message': 'Failed to generate answer from Llama'}), 500

        answer = (
            result.get('answer')
            or result.get('reference_answer')
            or result.get('generated_answer')
            or result.get('model_answer')
        )

        if not answer and result.get('raw_response'):
            print("[GENERATE-ANSWER] ERROR: Upstream returned non-JSON/invalid payload")
            return jsonify({'message': 'Llama API returned invalid response format'}), 502

        if not answer:
            print("[GENERATE-ANSWER] ERROR: No answer field in upstream response")
            return jsonify({'message': 'Llama API response did not include an answer'}), 502
        
        print(f"[GENERATE-ANSWER] SUCCESS: Generated answer received")
        return jsonify({
            'success': True,
            'answer': answer,
            'question': question,
            'marks': marks,
            'reference_answer': answer
        }), 200
        
    except Exception as e:
        print(f"[GENERATE-ANSWER] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Error generating answer: {str(e)}'}), 500


@eval_bp.route('/evaluate', methods=['POST'])
@token_required
def evaluate(payload):
    """Batch evaluation endpoint using external Llama pipeline"""
    try:
        if payload.get('role') != 'teacher':
            return jsonify({
                'message': 'Students are not allowed to upload question/model documents. Use student submission workflow.'
            }), 403

        if not llama_service.is_available():
            return jsonify({'message': 'Llama API is not configured or unavailable'}), 503

        # Get upload mode
        upload_mode = request.form.get('uploadMode', 'file')
        
        # Extract text based on mode
        if upload_mode == 'file':
            # File upload mode
            if 'questionsFile' not in request.files or \
               'modelAnswersFile' not in request.files or \
               'studentAnswersFile' not in request.files:
                return jsonify({'message': 'Missing required files'}), 400
            
            questions_file = request.files['questionsFile']
            model_answers_file = request.files['modelAnswersFile']
            student_answers_file = request.files['studentAnswersFile']
            
            # Validate files
            files_to_check = [questions_file, model_answers_file, student_answers_file]
            if not all([allowed_file(f.filename, Config.ALLOWED_EXTENSIONS) for f in files_to_check]):
                return jsonify({'message': 'Invalid file format. Allowed: TXT, PDF, DOCX'}), 400
            
            # Extract text from files
            try:
                questions_text = extract_text_from_file(questions_file)
                model_answers_text = extract_text_from_file(model_answers_file)
                student_answers_text = extract_text_from_file(student_answers_file)
            except Exception as e:
                return jsonify({'message': f'Error extracting text: {str(e)}'}), 400
            
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
        
        # Perform batch evaluation
        try:
            results = evaluation_service.evaluate_batch(
                questions=questions,
                model_answers=model_answers,
                student_answers=student_answers
            )
        except Exception as e:
            print(f"Evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'message': f'Evaluation error: {str(e)}'}), 500
        
        # Log evaluation for analytics (optional)
        try:
            evaluation_log = {
                'user_id': payload['user_id'],
                'total_questions': results['totalQuestions'],
                'total_score': float(results['totalScore']),
                'total_max_marks': float(results['totalMaxMarks']),
                'percentage': float(results['percentage']),
                'llama_pipeline': True,
                'timestamp': datetime.utcnow()
            }
            db['evaluations'].insert_one(evaluation_log)
        except Exception as e:
            print(f"Warning: Could not log evaluation: {e}")
        
        # Convert numpy types to native Python types for JSON serialization
        results = convert_numpy_types(results)
        
        # Build response
        response = {
            'message': 'Evaluation completed successfully',
            'evaluationMode': 'llama',
            **results
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Evaluation endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Server error: {str(e)}'}), 500


@eval_bp.route('/rag/ingest', methods=['POST'])
@token_required
def ingest_study_material(payload):
    """Deprecated endpoint retained for compatibility"""
    try:
        return jsonify({
            'message': 'Study material ingestion is no longer required.',
            'llamaConfigured': llama_service.is_available()
        }), 200
    except Exception as e:
        print(f"Ingestion error: {e}")
        return jsonify({'message': f'Ingestion error: {str(e)}'}), 500


@eval_bp.route('/rag/clear', methods=['POST'])
@token_required
def clear_rag_store(payload):
    """Deprecated endpoint retained for compatibility"""
    try:
        return jsonify({'message': 'No vector store is used in Llama pipeline mode.'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@eval_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    llama_health = llama_service.health() if llama_service.is_available() else None
    return jsonify({
        'status': 'healthy',
        'models_loaded': False,
        'llama_api_configured': llama_service.is_available(),
        'llama_api_healthy': bool(llama_health and llama_health.get('status') == 'ok')
    }), 200
