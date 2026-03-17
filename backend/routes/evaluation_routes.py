# backend/routes/evaluation_routes.py
"""
Evaluation API routes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from pymongo import MongoClient
import numpy as np

from config import Config
from utils.auth import token_required
from utils.parsers import parse_questions, parse_answers
from utils.file_processing import extract_text_from_file, allowed_file
from services import evaluation_service, rag_service
from models import ml_models


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

# Create Blueprint
eval_bp = Blueprint('evaluation', __name__, url_prefix='/api')

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]


@eval_bp.route('/evaluate', methods=['POST'])
@token_required
def evaluate(payload):
    """Batch evaluation endpoint with RAG support"""
    try:
        if payload.get('role') != 'teacher':
            return jsonify({
                'message': 'Students are not allowed to upload question/model documents. Use student submission workflow.'
            }), 403

        # Check if ML models are loaded
        if not ml_models.is_loaded:
            ml_models.ensure_loaded(force_reload=True)

        model_mode = 'ml' if ml_models.is_loaded else 'fallback'
        
        # Get upload mode
        upload_mode = request.form.get('uploadMode', 'file')
        use_rag = request.form.get('useRAG', 'false').lower() == 'true'
        
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
            
            # Process study material if RAG is enabled
            if use_rag and 'studyMaterialFile' in request.files:
                study_material_file = request.files['studyMaterialFile']
                if study_material_file and allowed_file(study_material_file.filename, Config.ALLOWED_EXTENSIONS):
                    try:
                        study_material_text = extract_text_from_file(study_material_file)
                        # Ingest study material into RAG system
                        rag_service.ingest_document(
                            study_material_text,
                            metadata={'user_id': payload['user_id'], 'timestamp': datetime.utcnow()}
                        )
                    except Exception as e:
                        print(f"Warning: Could not process study material: {e}")
        
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
            if model_mode == 'ml':
                results = evaluation_service.evaluate_batch(
                    questions=questions,
                    model_answers=model_answers,
                    student_answers=student_answers,
                    use_rag=use_rag
                )
            else:
                results = evaluation_service.evaluate_batch_fallback(
                    questions=questions,
                    model_answers=model_answers,
                    student_answers=student_answers,
                    use_rag=False
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
                'rag_enabled': use_rag,
                'timestamp': datetime.utcnow()
            }
            db['evaluations'].insert_one(evaluation_log)
        except Exception as e:
            print(f"Warning: Could not log evaluation: {e}")
        
        # Convert numpy types to native Python types for JSON serialization
        results = convert_numpy_types(results)
        
        # Build response
        response = {
            'message': 'Evaluation completed successfully' if model_mode == 'ml' else 'Evaluation completed using fallback mode (ML unavailable)',
            'evaluationMode': model_mode,
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
    """Endpoint to ingest study material into RAG system"""
    try:
        if not Config.RAG_ENABLED:
            return jsonify({'message': 'RAG is not enabled'}), 403
        
        # Get upload mode
        if 'file' in request.files:
            file = request.files['file']
            if not allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
                return jsonify({'message': 'Invalid file format'}), 400
            
            text = extract_text_from_file(file)
        else:
            text = request.form.get('text', '').strip()
            if not text:
                return jsonify({'message': 'No text provided'}), 400
        
        # Ingest into RAG system
        success = rag_service.ingest_document(
            text,
            metadata={
                'user_id': payload['user_id'],
                'timestamp': datetime.utcnow()
            }
        )
        
        if success:
            # Save vector store
            rag_service.save_vector_store(f"user_{payload['user_id']}")
            return jsonify({'message': 'Study material ingested successfully'}), 200
        else:
            return jsonify({'message': 'Failed to ingest study material'}), 500
        
    except Exception as e:
        print(f"Ingestion error: {e}")
        return jsonify({'message': f'Ingestion error: {str(e)}'}), 500


@eval_bp.route('/rag/clear', methods=['POST'])
@token_required
def clear_rag_store(payload):
    """Endpoint to clear RAG vector store"""
    try:
        rag_service.clear_vector_store()
        return jsonify({'message': 'RAG store cleared successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@eval_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'models_loaded': ml_models.is_loaded,
        'rag_enabled': Config.RAG_ENABLED,
        'groq_configured': bool(Config.GROQ_API_KEY)
    }), 200
