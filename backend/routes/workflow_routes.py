# backend/routes/workflow_routes.py
"""
Role-based assignment and submission workflow routes
"""
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

from config import Config
from models import ml_models
from services import evaluation_service, rag_service
from utils.auth import token_required
from utils.file_processing import allowed_file, extract_text_from_file
from utils.parsers import parse_answers, parse_questions


workflow_bp = Blueprint('workflow', __name__, url_prefix='/api')

client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]

users_collection = db['users']
assignments_collection = db['assignments']
submissions_collection = db['submissions']
evaluations_collection = db['evaluations']


DEFAULT_SUBJECTS = [
    'Mathematics',
    'Physics',
    'Chemistry',
    'Biology',
    'Computer Science',
    'English'
]


def convert_numpy_types(obj):
    """Convert numpy and complex objects into JSON-safe values"""
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


def parse_object_id(id_value):
    """Safely parse ObjectId"""
    try:
        return ObjectId(id_value)
    except Exception:
        return None


def role_guard(payload, role):
    """Ensure user has expected role"""
    if payload.get('role') != role:
        return False
    return True


def get_user(user_id):
    """Fetch user by ID"""
    object_id = parse_object_id(user_id)
    if not object_id:
        return None
    return users_collection.find_one({'_id': object_id})


@workflow_bp.route('/subjects', methods=['GET'])
@token_required
def get_subjects(payload):
    """Get available subjects for dropdown selection"""
    try:
        subjects = set(DEFAULT_SUBJECTS)
        teacher_docs = users_collection.find({'role': 'teacher'}, {'subjects': 1})
        for teacher in teacher_docs:
            for subject in teacher.get('subjects', []):
                if isinstance(subject, str) and subject.strip():
                    subjects.add(subject.strip())

        user = get_user(payload['user_id'])
        user_subjects = user.get('subjects', []) if user else []

        return jsonify({
            'subjects': sorted(list(subjects)),
            'userSubjects': user_subjects
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch subjects: {str(e)}'}), 500


@workflow_bp.route('/teacher/assignments', methods=['POST'])
@token_required
def create_assignment(payload):
    """Teacher creates assignment by uploading question/model/rag docs"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can create assignments'}), 403

        teacher = get_user(payload['user_id'])
        if not teacher:
            return jsonify({'message': 'Teacher not found'}), 404

        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        due_date_raw = request.form.get('dueDate', '').strip()

        if not subject:
            return jsonify({'message': 'Subject is required'}), 400

        teacher_subjects = teacher.get('subjects', [])
        if teacher_subjects and subject not in teacher_subjects:
            return jsonify({'message': 'You can create assignments only for your registered subjects'}), 403

        if 'questionsFile' not in request.files or 'modelAnswersFile' not in request.files:
            return jsonify({'message': 'Questions and model answers files are required'}), 400

        questions_file = request.files['questionsFile']
        model_answers_file = request.files['modelAnswersFile']
        study_material_file = request.files.get('studyMaterialFile')

        files_to_validate = [questions_file, model_answers_file]
        if study_material_file:
            files_to_validate.append(study_material_file)

        if not all(allowed_file(file.filename, Config.ALLOWED_EXTENSIONS) for file in files_to_validate):
            return jsonify({'message': 'Invalid file format. Allowed: TXT, PDF, DOCX'}), 400

        questions_text = extract_text_from_file(questions_file)
        model_answers_text = extract_text_from_file(model_answers_file)
        study_material_text = extract_text_from_file(study_material_file) if study_material_file else ''

        questions = parse_questions(questions_text)
        model_answers = parse_answers(model_answers_text)

        if not questions:
            return jsonify({'message': 'Invalid questions format. Use Q1: [5 marks] Question text'}), 400
        if not model_answers:
            return jsonify({'message': 'Invalid model answers format. Use A1: Answer text'}), 400

        due_date = None
        if due_date_raw:
            try:
                due_date = datetime.fromisoformat(due_date_raw)
            except Exception:
                return jsonify({'message': 'Invalid dueDate format. Use ISO format'}), 400

        assignment = {
            'title': title or f'{subject} Assignment',
            'subject': subject,
            'teacher_id': payload['user_id'],
            'teacher_name': teacher.get('name', ''),
            'questions_text': questions_text,
            'model_answers_text': model_answers_text,
            'study_material_text': study_material_text,
            'questions_filename': questions_file.filename,
            'model_answers_filename': model_answers_file.filename,
            'study_material_filename': study_material_file.filename if study_material_file else None,
            'due_date': due_date,
            'status': 'active',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        assignment_result = assignments_collection.insert_one(assignment)

        return jsonify({
            'message': 'Assignment created successfully',
            'assignment': {
                'id': str(assignment_result.inserted_id),
                'title': assignment['title'],
                'subject': subject,
                'dueDate': due_date.isoformat() if due_date else None,
                'status': assignment['status']
            }
        }), 201
    except Exception as e:
        return jsonify({'message': f'Assignment creation failed: {str(e)}'}), 500


@workflow_bp.route('/teacher/assignments', methods=['GET'])
@token_required
def list_teacher_assignments(payload):
    """List assignments created by logged-in teacher"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can access this endpoint'}), 403

        assignment_docs = assignments_collection.find(
            {'teacher_id': payload['user_id']},
            sort=[('created_at', -1)]
        )

        assignments = []
        for assignment in assignment_docs:
            assignment_id = str(assignment['_id'])
            submission_count = submissions_collection.count_documents({'assignment_id': assignment_id})

            assignments.append({
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', ''),
                'status': assignment.get('status', 'active'),
                'dueDate': assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                'submissionCount': submission_count,
                'createdAt': assignment.get('created_at').isoformat() if assignment.get('created_at') else None
            })

        return jsonify({'assignments': assignments}), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch assignments: {str(e)}'}), 500


@workflow_bp.route('/student/assignments', methods=['GET'])
@token_required
def list_student_assignments(payload):
    """List assignments available for the logged-in student"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can access this endpoint'}), 403

        student = get_user(payload['user_id'])
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        subject_filter = request.args.get('subject', '').strip()
        query = {'status': 'active'}

        student_subjects = student.get('subjects', [])
        if subject_filter:
            query['subject'] = subject_filter
        elif student_subjects:
            query['subject'] = {'$in': student_subjects}

        assignment_docs = list(assignments_collection.find(query, sort=[('created_at', -1)]))
        assignment_ids = [str(assignment['_id']) for assignment in assignment_docs]

        existing_submissions = submissions_collection.find({
            'student_id': payload['user_id'],
            'assignment_id': {'$in': assignment_ids}
        })
        submitted_ids = {submission['assignment_id'] for submission in existing_submissions}

        assignments = []
        for assignment in assignment_docs:
            assignment_id = str(assignment['_id'])
            assignments.append({
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', ''),
                'teacherName': assignment.get('teacher_name', ''),
                'dueDate': assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                'alreadySubmitted': assignment_id in submitted_ids
            })

        return jsonify({
            'assignments': assignments,
            'studentSubjects': student_subjects
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch student assignments: {str(e)}'}), 500


@workflow_bp.route('/student/submissions', methods=['POST'])
@token_required
def submit_student_answers(payload):
    """Student submits only answer file for selected assignment"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can submit answers'}), 403

        assignment_id = request.form.get('assignmentId', '').strip()
        if not assignment_id:
            return jsonify({'message': 'assignmentId is required'}), 400

        if 'studentAnswersFile' not in request.files:
            return jsonify({'message': 'Student answers file is required'}), 400

        assignment_object_id = parse_object_id(assignment_id)
        if not assignment_object_id:
            return jsonify({'message': 'Invalid assignmentId'}), 400

        assignment = assignments_collection.find_one({'_id': assignment_object_id, 'status': 'active'})
        if not assignment:
            return jsonify({'message': 'Assignment not found or inactive'}), 404

        student = get_user(payload['user_id'])
        if not student:
            return jsonify({'message': 'Student not found'}), 404

        student_subjects = student.get('subjects', [])
        assignment_subject = assignment.get('subject', '')
        if student_subjects and assignment_subject not in student_subjects:
            return jsonify({'message': 'You are not enrolled in this subject'}), 403

        if assignment.get('due_date') and datetime.utcnow() > assignment.get('due_date'):
            return jsonify({'message': 'Assignment submission deadline has passed'}), 400

        student_answers_file = request.files['studentAnswersFile']
        if not allowed_file(student_answers_file.filename, Config.ALLOWED_EXTENSIONS):
            return jsonify({'message': 'Invalid file format. Allowed: TXT, PDF, DOCX'}), 400

        student_answers_text = extract_text_from_file(student_answers_file)
        student_answers = parse_answers(student_answers_text)
        if not student_answers:
            return jsonify({'message': 'Invalid student answers format. Use A1: Answer text'}), 400

        existing_submission = submissions_collection.find_one({
            'assignment_id': assignment_id,
            'student_id': payload['user_id']
        })

        if existing_submission and existing_submission.get('status') in ['evaluated', 'released']:
            return jsonify({'message': 'Submission is already evaluated. Resubmission is not allowed.'}), 400

        now = datetime.utcnow()
        submission_payload = {
            'assignment_id': assignment_id,
            'student_id': payload['user_id'],
            'student_name': student.get('name', ''),
            'student_email': student.get('email', ''),
            'student_answers_text': student_answers_text,
            'student_answers_filename': student_answers_file.filename,
            'status': 'submitted',
            'submitted_at': now,
            'updated_at': now
        }

        if existing_submission:
            submissions_collection.update_one(
                {'_id': existing_submission['_id']},
                {'$set': submission_payload}
            )
            submission_id = str(existing_submission['_id'])
            message = 'Submission updated successfully'
        else:
            submission_result = submissions_collection.insert_one(submission_payload)
            submission_id = str(submission_result.inserted_id)
            message = 'Submission uploaded successfully'

        return jsonify({
            'message': message,
            'submission': {
                'id': submission_id,
                'assignmentId': assignment_id,
                'status': 'submitted'
            }
        }), 201
    except Exception as e:
        return jsonify({'message': f'Submission failed: {str(e)}'}), 500


@workflow_bp.route('/teacher/assignments/<assignment_id>/submissions', methods=['GET'])
@token_required
def list_assignment_submissions(payload, assignment_id):
    """Teacher views all student submissions for one assignment"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can access this endpoint'}), 403

        assignment_object_id = parse_object_id(assignment_id)
        if not assignment_object_id:
            return jsonify({'message': 'Invalid assignment ID'}), 400

        assignment = assignments_collection.find_one({'_id': assignment_object_id})
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        if assignment.get('teacher_id') != payload['user_id']:
            return jsonify({'message': 'You can only view your own assignment submissions'}), 403

        submission_docs = submissions_collection.find(
            {'assignment_id': assignment_id},
            sort=[('submitted_at', -1)]
        )

        submissions = []
        for submission in submission_docs:
            submission_id = str(submission['_id'])
            evaluation = evaluations_collection.find_one({'submission_id': submission_id})

            submissions.append({
                'id': submission_id,
                'studentId': submission.get('student_id', ''),
                'studentName': submission.get('student_name', ''),
                'studentEmail': submission.get('student_email', ''),
                'status': submission.get('status', 'submitted'),
                'submittedAt': submission.get('submitted_at').isoformat() if submission.get('submitted_at') else None,
                'evaluatedAt': submission.get('evaluated_at').isoformat() if submission.get('evaluated_at') else None,
                'released': bool(evaluation and evaluation.get('released')),
                'finalScore': evaluation.get('results', {}).get('totalScore') if evaluation else None,
                'totalMaxMarks': evaluation.get('results', {}).get('totalMaxMarks') if evaluation else None,
                'percentage': evaluation.get('results', {}).get('percentage') if evaluation else None
            })

        return jsonify({
            'assignment': {
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', '')
            },
            'submissions': submissions
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch submissions: {str(e)}'}), 500


@workflow_bp.route('/teacher/submissions/<submission_id>/evaluate', methods=['POST'])
@token_required
def evaluate_submission(payload, submission_id):
    """Teacher evaluates a submission and stores results"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can evaluate submissions'}), 403

        if not ml_models.is_loaded:
            ml_models.ensure_loaded(force_reload=True)

        model_mode = 'ml' if ml_models.is_loaded else 'fallback'

        submission_object_id = parse_object_id(submission_id)
        if not submission_object_id:
            return jsonify({'message': 'Invalid submission ID'}), 400

        submission = submissions_collection.find_one({'_id': submission_object_id})
        if not submission:
            return jsonify({'message': 'Submission not found'}), 404

        assignment = assignments_collection.find_one({'_id': parse_object_id(submission.get('assignment_id'))})
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        if assignment.get('teacher_id') != payload['user_id']:
            return jsonify({'message': 'You can evaluate only your own assignment submissions'}), 403

        questions_text = assignment.get('questions_text', '')
        model_answers_text = assignment.get('model_answers_text', '')
        student_answers_text = submission.get('student_answers_text', '')
        study_material_text = assignment.get('study_material_text', '')

        if 'questionsFile' in request.files:
            override_questions = request.files['questionsFile']
            if not allowed_file(override_questions.filename, Config.ALLOWED_EXTENSIONS):
                return jsonify({'message': 'Invalid override questions file format'}), 400
            questions_text = extract_text_from_file(override_questions)

        if 'modelAnswersFile' in request.files:
            override_model_answers = request.files['modelAnswersFile']
            if not allowed_file(override_model_answers.filename, Config.ALLOWED_EXTENSIONS):
                return jsonify({'message': 'Invalid override model answers file format'}), 400
            model_answers_text = extract_text_from_file(override_model_answers)

        if 'studentAnswersFile' in request.files:
            override_student_answers = request.files['studentAnswersFile']
            if not allowed_file(override_student_answers.filename, Config.ALLOWED_EXTENSIONS):
                return jsonify({'message': 'Invalid override student answers file format'}), 400
            student_answers_text = extract_text_from_file(override_student_answers)

        if 'studyMaterialFile' in request.files:
            override_study_material = request.files['studyMaterialFile']
            if not allowed_file(override_study_material.filename, Config.ALLOWED_EXTENSIONS):
                return jsonify({'message': 'Invalid override study material file format'}), 400
            study_material_text = extract_text_from_file(override_study_material)

        questions = parse_questions(questions_text)
        model_answers = parse_answers(model_answers_text)
        student_answers = parse_answers(student_answers_text)

        if not questions or not model_answers or not student_answers:
            return jsonify({'message': 'Invalid question/answer formatting for evaluation'}), 400

        use_rag = request.form.get('useRAG', 'true').lower() == 'true'
        rag_enabled_for_eval = use_rag and bool(study_material_text)

        if rag_enabled_for_eval:
            rag_service.ingest_document(
                study_material_text,
                metadata={
                    'assignment_id': str(assignment['_id']),
                    'teacher_id': payload['user_id'],
                    'timestamp': datetime.utcnow()
                }
            )

        if model_mode == 'ml':
            results = evaluation_service.evaluate_batch(
                questions=questions,
                model_answers=model_answers,
                student_answers=student_answers,
                use_rag=rag_enabled_for_eval
            )
        else:
            results = evaluation_service.evaluate_batch_fallback(
                questions=questions,
                model_answers=model_answers,
                student_answers=student_answers,
                use_rag=False
            )

        results = convert_numpy_types(results)

        evaluation_payload = {
            'submission_id': submission_id,
            'assignment_id': submission.get('assignment_id'),
            'teacher_id': payload['user_id'],
            'student_id': submission.get('student_id'),
            'results': results,
            'evaluation_mode': model_mode,
            'released': False,
            'evaluated_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        evaluations_collection.update_one(
            {'submission_id': submission_id},
            {'$set': evaluation_payload},
            upsert=True
        )

        submissions_collection.update_one(
            {'_id': submission_object_id},
            {
                '$set': {
                    'status': 'evaluated',
                    'evaluated_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

        return jsonify({
            'message': 'Submission evaluated successfully' if model_mode == 'ml' else 'Submission evaluated using fallback mode (ML unavailable)',
            'submissionId': submission_id,
            'evaluationMode': model_mode,
            **results
        }), 200
    except Exception as e:
        return jsonify({'message': f'Evaluation failed: {str(e)}'}), 500


@workflow_bp.route('/teacher/submissions/<submission_id>/release', methods=['POST'])
@token_required
def release_result(payload, submission_id):
    """Teacher releases evaluated result to student"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can release results'}), 403

        submission_object_id = parse_object_id(submission_id)
        if not submission_object_id:
            return jsonify({'message': 'Invalid submission ID'}), 400

        submission = submissions_collection.find_one({'_id': submission_object_id})
        if not submission:
            return jsonify({'message': 'Submission not found'}), 404

        assignment = assignments_collection.find_one({'_id': parse_object_id(submission.get('assignment_id'))})
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        if assignment.get('teacher_id') != payload['user_id']:
            return jsonify({'message': 'You can release only your own assignment results'}), 403

        evaluation = evaluations_collection.find_one({'submission_id': submission_id})
        if not evaluation:
            return jsonify({'message': 'Submission is not evaluated yet'}), 400

        evaluations_collection.update_one(
            {'submission_id': submission_id},
            {
                '$set': {
                    'released': True,
                    'released_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

        submissions_collection.update_one(
            {'_id': submission_object_id},
            {
                '$set': {
                    'status': 'released',
                    'released_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

        return jsonify({'message': 'Result released successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Could not release result: {str(e)}'}), 500


@workflow_bp.route('/student/submissions', methods=['GET'])
@token_required
def list_student_submissions(payload):
    """Student views own submissions and release status"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can access this endpoint'}), 403

        submission_docs = submissions_collection.find(
            {'student_id': payload['user_id']},
            sort=[('submitted_at', -1)]
        )

        submissions = []
        for submission in submission_docs:
            assignment = assignments_collection.find_one({'_id': parse_object_id(submission.get('assignment_id'))})
            evaluation = evaluations_collection.find_one({'submission_id': str(submission['_id'])})

            submissions.append({
                'id': str(submission['_id']),
                'assignmentId': submission.get('assignment_id', ''),
                'assignmentTitle': assignment.get('title', '') if assignment else '',
                'subject': assignment.get('subject', '') if assignment else '',
                'status': submission.get('status', 'submitted'),
                'submittedAt': submission.get('submitted_at').isoformat() if submission.get('submitted_at') else None,
                'canViewResult': bool(evaluation and evaluation.get('released')),
                'finalScore': evaluation.get('results', {}).get('totalScore') if evaluation and evaluation.get('released') else None,
                'totalMaxMarks': evaluation.get('results', {}).get('totalMaxMarks') if evaluation and evaluation.get('released') else None,
                'percentage': evaluation.get('results', {}).get('percentage') if evaluation and evaluation.get('released') else None
            })

        return jsonify({'submissions': submissions}), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch submissions: {str(e)}'}), 500


@workflow_bp.route('/student/results/<submission_id>', methods=['GET'])
@token_required
def get_student_result(payload, submission_id):
    """Student fetches released evaluation result in report-ready format"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can access this endpoint'}), 403

        submission_object_id = parse_object_id(submission_id)
        if not submission_object_id:
            return jsonify({'message': 'Invalid submission ID'}), 400

        submission = submissions_collection.find_one({'_id': submission_object_id})
        if not submission:
            return jsonify({'message': 'Submission not found'}), 404

        if submission.get('student_id') != payload['user_id']:
            return jsonify({'message': 'You can view only your own results'}), 403

        evaluation = evaluations_collection.find_one({'submission_id': submission_id})
        if not evaluation or not evaluation.get('released'):
            return jsonify({'message': 'Result not released by teacher yet'}), 403

        assignment = assignments_collection.find_one({'_id': parse_object_id(submission.get('assignment_id'))})
        results = convert_numpy_types(evaluation.get('results', {}))

        return jsonify({
            'message': 'Result fetched successfully',
            'submissionId': submission_id,
            'assignment': {
                'id': submission.get('assignment_id'),
                'title': assignment.get('title', '') if assignment else '',
                'subject': assignment.get('subject', '') if assignment else ''
            },
            **results
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch result: {str(e)}'}), 500


@workflow_bp.route('/teacher/results/<submission_id>', methods=['GET'])
@token_required
def get_teacher_result(payload, submission_id):
    """Teacher fetches evaluated result (released or unreleased) for own assignment"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can access this endpoint'}), 403

        submission_object_id = parse_object_id(submission_id)
        if not submission_object_id:
            return jsonify({'message': 'Invalid submission ID'}), 400

        submission = submissions_collection.find_one({'_id': submission_object_id})
        if not submission:
            return jsonify({'message': 'Submission not found'}), 404

        assignment = assignments_collection.find_one({'_id': parse_object_id(submission.get('assignment_id'))})
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        if assignment.get('teacher_id') != payload['user_id']:
            return jsonify({'message': 'You can view results only for your own assignments'}), 403

        evaluation = evaluations_collection.find_one({'submission_id': submission_id})
        if not evaluation:
            return jsonify({'message': 'Submission is not evaluated yet'}), 400

        results = convert_numpy_types(evaluation.get('results', {}))

        return jsonify({
            'message': 'Result fetched successfully',
            'submissionId': submission_id,
            'released': bool(evaluation.get('released', False)),
            'evaluationMode': evaluation.get('evaluation_mode', 'ml'),
            'student': {
                'id': submission.get('student_id', ''),
                'name': submission.get('student_name', ''),
                'email': submission.get('student_email', '')
            },
            'assignment': {
                'id': submission.get('assignment_id'),
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', '')
            },
            **results
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch teacher result: {str(e)}'}), 500