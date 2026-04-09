# backend/routes/workflow_routes.py
"""
Role-based assignment and submission workflow routes
"""
from datetime import datetime
from typing import Dict, List

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

from config import Config
from services import evaluation_service, llama_service
from services.llama_service import LlamaServiceError
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


def normalize_questions(question_items: List[Dict]) -> List[Dict]:
    """Normalize incoming question list into parser-compatible structure"""
    normalized = []
    for index, raw_question in enumerate(question_items or [], start=1):
        if not isinstance(raw_question, dict):
            continue

        question_text = str(raw_question.get('question', '')).strip()
        if not question_text:
            continue

        marks_raw = raw_question.get('marks', 0)
        try:
            marks = float(marks_raw)
        except (TypeError, ValueError):
            continue

        if marks <= 0:
            continue

        normalized.append({
            'number': index,
            'question': question_text,
            'marks': marks
        })

    return normalized


def format_questions_text(questions: List[Dict]) -> str:
    """Convert question list to Q1:[marks] format text"""
    lines = []
    for question in questions:
        marks_value = int(question['marks']) if float(question['marks']).is_integer() else question['marks']
        lines.append(f"Q{question['number']}: [{marks_value} marks] {question['question']}")
    return "\n".join(lines)


def format_answers_text(answers: List[Dict]) -> str:
    """Convert answer list to A1: format text"""
    lines = []
    for answer in answers:
        lines.append(f"A{answer['number']}: {answer['answer']}")
    return "\n".join(lines)


def generate_model_answers_for_questions(questions: List[Dict]) -> List[Dict]:
    """Generate model answers from Llama for each assignment question"""
    generated_answers = []
    for question in questions:
        marks_int = int(round(float(question.get('marks', 0))))
        generated = llama_service.generate_answer(question.get('question', ''), marks=marks_int)
        if not generated:
            raise Exception(f"Failed to generate model answer for Q{question.get('number')}")

        answer_text = str(generated.get('answer') or generated.get('reference_answer') or '').strip()
        if not answer_text:
            raise Exception(f"Empty model answer generated for Q{question.get('number')}")

        generated_answers.append({
            'number': question.get('number'),
            'answer': answer_text
        })

    return generated_answers


def parse_assignment_questions(assignment: Dict) -> List[Dict]:
    """Fetch structured questions from assignment"""
    questions = assignment.get('questions', [])
    if isinstance(questions, list) and questions:
        return questions

    return parse_questions(assignment.get('questions_text', ''))


def evaluate_submission_with_assignment(submission: Dict, assignment: Dict, teacher_id: str) -> Dict:
    """Evaluate one submission against assignment and persist results"""
    questions_text = assignment.get('questions_text', '')
    model_answers_text = ensure_model_answers_for_assignment(assignment)
    student_answers_text = submission.get('student_answers_text', '')

    questions = parse_questions(questions_text)
    model_answers = parse_answers(model_answers_text)
    student_answers = parse_answers(student_answers_text)

    if not questions or not model_answers or not student_answers:
        raise Exception('Invalid question/answer formatting for evaluation')

    results = evaluation_service.evaluate_batch(
        questions=questions,
        model_answers=model_answers,
        student_answers=student_answers
    )
    results = convert_numpy_types(results)

    submission_id = str(submission['_id'])
    evaluation_payload = {
        'submission_id': submission_id,
        'assignment_id': submission.get('assignment_id'),
        'teacher_id': teacher_id,
        'student_id': submission.get('student_id'),
        'results': results,
        'evaluation_mode': 'llama',
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
        {'_id': submission['_id']},
        {
            '$set': {
                'status': 'evaluated',
                'evaluated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        }
    )

    return results


def ensure_model_answers_for_assignment(assignment: Dict) -> str:
    """Ensure assignment has model answers; lazily generate and persist when missing"""
    existing_text = str(assignment.get('model_answers_text', '') or '').strip()
    if existing_text:
        return existing_text

    questions = parse_assignment_questions(assignment)
    if not questions:
        raise Exception('Assignment has no valid questions for model answer generation')

    if not llama_service.is_available():
        raise Exception('Llama API is not configured or unavailable')

    persisted_answers = assignment.get('model_answers', [])
    if not isinstance(persisted_answers, list):
        persisted_answers = []

    answer_map = {}
    for item in persisted_answers:
        if not isinstance(item, dict):
            continue
        number = item.get('number')
        answer_text = str(item.get('answer', '')).strip()
        if number is None or not answer_text:
            continue
        try:
            number = int(number)
        except Exception:
            continue
        answer_map[number] = answer_text

    generated_any_new = False
    for question in questions:
        question_number = int(question.get('number', 0) or 0)
        if question_number <= 0:
            continue

        if answer_map.get(question_number):
            continue

        marks_int = int(round(float(question.get('marks', 0))))
        generated = llama_service.generate_answer(question.get('question', ''), marks=marks_int)
        if not generated:
            raise Exception(
                f"Failed to generate model answer for Q{question_number}. "
                "Try again; completed answers are already saved."
            )

        answer_text = str(generated.get('answer') or generated.get('reference_answer') or '').strip()
        if not answer_text:
            raise Exception(f'Empty model answer generated for Q{question_number}')

        answer_map[question_number] = answer_text
        generated_any_new = True

        partial_answers = []
        for item in questions:
            number = int(item.get('number', 0) or 0)
            if number <= 0:
                continue
            resolved = answer_map.get(number)
            if resolved:
                partial_answers.append({'number': number, 'answer': resolved})

        partial_text = format_answers_text(partial_answers)
        assignments_collection.update_one(
            {'_id': assignment['_id']},
            {
                '$set': {
                    'model_answers': partial_answers,
                    'model_answers_text': partial_text,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    generated_answers = []
    for question in questions:
        question_number = int(question.get('number', 0) or 0)
        resolved_answer = answer_map.get(question_number)
        if resolved_answer:
            generated_answers.append({'number': question_number, 'answer': resolved_answer})

    if len(generated_answers) != len(questions):
        missing_numbers = [
            int(question.get('number', 0) or 0)
            for question in questions
            if not answer_map.get(int(question.get('number', 0) or 0))
        ]
        raise Exception(f'Missing model answers for questions: {missing_numbers}')

    generated_text = format_answers_text(generated_answers)

    if generated_any_new or not assignment.get('model_answers_text'):
        assignments_collection.update_one(
            {'_id': assignment['_id']},
            {
                '$set': {
                    'model_answers': generated_answers,
                    'model_answers_text': generated_text,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    assignment['model_answers'] = generated_answers
    assignment['model_answers_text'] = generated_text
    return generated_text


def build_question_with_marks(question_text: str, marks: float) -> str:
    """Ensure question contains marks metadata expected by evaluator"""
    marks_int = int(round(float(marks)))
    if 'marks:' in question_text.lower():
        return question_text
    return f"{question_text}\nMarks: {marks_int}"


def extract_batch_results_map(batch_response: Dict) -> Dict:
    """Extract student-wise results map from batch response using tolerant keys"""
    if not isinstance(batch_response, dict):
        return {}

    for key in ['results', 'evaluations', 'scores', 'students', 'data']:
        candidate = batch_response.get(key)
        if isinstance(candidate, dict):
            return candidate

    nested_dict_values = [value for value in batch_response.values() if isinstance(value, dict)]
    if nested_dict_values:
        return batch_response

    return {}


def normalize_batch_question_result(
    raw_result: Dict,
    question_number: int,
    question_text: str,
    max_marks: float,
    model_answer: str,
    student_answer: str
) -> Dict:
    """Normalize one student's one-question batch response into app result schema"""
    raw_result = raw_result or {}

    semantic_similarity = float(
        raw_result.get('semantic_similarity', raw_result.get('similarity', 0.0)) or 0.0
    )

    awarded_marks = raw_result.get('awarded_marks', raw_result.get('score'))
    if awarded_marks is None:
        final_score_ratio = raw_result.get('final_score', raw_result.get('finalScore'))
        if final_score_ratio is not None:
            try:
                awarded_marks = float(final_score_ratio) * float(max_marks)
            except Exception:
                awarded_marks = 0.0
        else:
            awarded_marks = 0.0

    try:
        numeric_score = float(awarded_marks)
    except Exception:
        numeric_score = 0.0

    numeric_score = max(0.0, min(numeric_score, float(max_marks)))
    rounded_score = int(round(numeric_score))

    grade = str(raw_result.get('grade', raw_result.get('nli_label', 'evaluated')))
    reference_answer = str(
        raw_result.get('reference_answer')
        or raw_result.get('referenceAnswer')
        or model_answer
    )

    feedback = str(raw_result.get('feedback') or '').strip()
    if not feedback:
        feedback = (
            f"Llama batch evaluation: {grade}. "
            f"Semantic similarity: {semantic_similarity:.2%}, "
            f"awarded marks: {rounded_score}/{int(round(float(max_marks)))}."
        )

    return {
        'questionNumber': int(question_number),
        'question': question_text,
        'modelAnswer': reference_answer,
        'studentAnswer': student_answer,
        'score': float(rounded_score),
        'maxMarks': float(max_marks),
        'similarity': float(round(semantic_similarity, 4)),
        'nliLabel': grade.lower().replace('_', ' '),
        'feedback': feedback,
        'llamaEnabled': True,
        'contextUsed': 0,
        'grade': grade
    }


def sort_question_results(question_results: List[Dict]) -> List[Dict]:
    """Sort question-level results by question number"""
    return sorted(
        question_results,
        key=lambda item: int(item.get('questionNumber', 0) or 0)
    )


def upsert_question_result(question_results: List[Dict], question_result: Dict) -> List[Dict]:
    """Insert or replace a question result by questionNumber"""
    question_number = int(question_result.get('questionNumber', 0) or 0)
    if question_number <= 0:
        return sort_question_results(question_results)

    updated = []
    replaced = False
    for existing in question_results:
        existing_number = int(existing.get('questionNumber', 0) or 0)
        if existing_number == question_number:
            updated.append(question_result)
            replaced = True
        else:
            updated.append(existing)

    if not replaced:
        updated.append(question_result)

    return sort_question_results(updated)


def build_aggregate_results(question_results: List[Dict]) -> Dict:
    """Build aggregate score summary from question-level results"""
    normalized = sort_question_results(question_results)
    total_score = sum(float(item.get('score', 0)) for item in normalized)
    total_max_marks = sum(float(item.get('maxMarks', 0)) for item in normalized)
    total_questions = len(normalized)
    total_similarity = sum(float(item.get('similarity', 0)) for item in normalized)

    percentage = (total_score / total_max_marks * 100) if total_max_marks > 0 else 0
    average_similarity = (total_similarity / total_questions) if total_questions > 0 else 0

    return {
        'totalScore': float(round(total_score, 2)),
        'totalMaxMarks': float(round(total_max_marks, 2)),
        'percentage': float(round(percentage, 2)),
        'totalQuestions': int(total_questions),
        'averageSimilarity': float(round(average_similarity, 4)),
        'questions': normalized
    }


def persist_evaluation_checkpoint(submission: Dict, teacher_id: str, question_results: List[Dict]) -> None:
    """Persist in-progress evaluation checkpoint to survive long-running timeouts"""
    submission_id = str(submission.get('_id'))
    aggregate = build_aggregate_results(question_results)

    evaluations_collection.update_one(
        {'submission_id': submission_id},
        {
            '$set': {
                'submission_id': submission_id,
                'assignment_id': submission.get('assignment_id'),
                'teacher_id': teacher_id,
                'student_id': submission.get('student_id'),
                'evaluation_mode': 'llama',
                'released': False,
                'checkpoint_results': aggregate,
                'in_progress': True,
                'updated_at': datetime.utcnow()
            }
        },
        upsert=True
    )


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
    """Teacher creates assignment via multi-question JSON or file uploads"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can create assignments'}), 403

        teacher = get_user(payload['user_id'])
        if not teacher:
            return jsonify({'message': 'Teacher not found'}), 404

        body = request.get_json(silent=True) if request.is_json else {}
        title = str((body.get('title') if body else None) or request.form.get('title', '')).strip()
        subject = str((body.get('subject') if body else None) or request.form.get('subject', '')).strip()
        due_date_raw = str((body.get('dueDate') if body else None) or request.form.get('dueDate', '')).strip()

        if not subject:
            return jsonify({'message': 'Subject is required'}), 400

        teacher_subjects = teacher.get('subjects', [])
        if teacher_subjects and subject not in teacher_subjects:
            return jsonify({'message': 'You can create assignments only for your registered subjects'}), 403

        questions_file = None
        model_answers_file = None
        study_material_file = None
        questions = []
        model_answers = []
        questions_text = ''
        model_answers_text = ''
        study_material_text = ''

        if request.is_json:
            questions = normalize_questions((body or {}).get('questions', []))
            if not questions:
                return jsonify({'message': 'Provide at least one question with valid marks'}), 400
            questions_text = format_questions_text(questions)
        else:
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
            'questions': questions,
            'model_answers': model_answers,
            'questions_text': questions_text,
            'model_answers_text': model_answers_text,
            'study_material_text': study_material_text,
            'questions_filename': questions_file.filename if questions_file else None,
            'model_answers_filename': model_answers_file.filename if model_answers_file else None,
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
                'questionCount': len(questions),
                'totalMarks': sum(float(item.get('marks', 0)) for item in questions),
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
            question_items = parse_assignment_questions(assignment)
            total_marks = sum(float(item.get('marks', 0)) for item in question_items)

            assignments.append({
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', ''),
                'status': assignment.get('status', 'active'),
                'questionCount': len(question_items),
                'totalMarks': total_marks,
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
            question_items = parse_assignment_questions(assignment)
            total_marks = sum(float(item.get('marks', 0)) for item in question_items)
            assignments.append({
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', ''),
                'teacherName': assignment.get('teacher_name', ''),
                'questionCount': len(question_items),
                'totalMarks': total_marks,
                'dueDate': assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                'alreadySubmitted': assignment_id in submitted_ids
            })

        return jsonify({
            'assignments': assignments,
            'studentSubjects': student_subjects
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch student assignments: {str(e)}'}), 500


@workflow_bp.route('/teacher/assignments/<assignment_id>', methods=['GET'])
@token_required
def get_teacher_assignment_detail(payload, assignment_id):
    """Teacher views assignment details including all questions"""
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
            return jsonify({'message': 'You can only view your own assignments'}), 403

        question_items = parse_assignment_questions(assignment)

        return jsonify({
            'assignment': {
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment.get('subject', ''),
                'status': assignment.get('status', 'active'),
                'dueDate': assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                'questionCount': len(question_items),
                'totalMarks': sum(float(item.get('marks', 0)) for item in question_items),
                'questions': question_items
            }
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch assignment: {str(e)}'}), 500


@workflow_bp.route('/student/assignments/<assignment_id>', methods=['GET'])
@token_required
def get_student_assignment_detail(payload, assignment_id):
    """Student views assignment details including all questions"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can access this endpoint'}), 403

        assignment_object_id = parse_object_id(assignment_id)
        if not assignment_object_id:
            return jsonify({'message': 'Invalid assignment ID'}), 400

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

        existing_submission = submissions_collection.find_one({
            'assignment_id': assignment_id,
            'student_id': payload['user_id']
        })

        question_items = parse_assignment_questions(assignment)

        return jsonify({
            'assignment': {
                'id': assignment_id,
                'title': assignment.get('title', ''),
                'subject': assignment_subject,
                'teacherName': assignment.get('teacher_name', ''),
                'dueDate': assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                'questionCount': len(question_items),
                'totalMarks': sum(float(item.get('marks', 0)) for item in question_items),
                'alreadySubmitted': bool(existing_submission),
                'questions': question_items
            }
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch assignment: {str(e)}'}), 500


@workflow_bp.route('/student/submissions', methods=['POST'])
@token_required
def submit_student_answers(payload):
    """Student submits answers for selected assignment (file or structured text)"""
    try:
        if not role_guard(payload, 'student'):
            return jsonify({'message': 'Only students can submit answers'}), 403

        request_body = request.get_json(silent=True) if request.is_json else {}
        assignment_id = str(
            (request_body.get('assignmentId') if request_body else None)
            or request.form.get('assignmentId', '')
        ).strip()
        if not assignment_id:
            return jsonify({'message': 'assignmentId is required'}), 400

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

        student_answers_file = None
        student_answers_text = ''

        if request.is_json:
            answers_payload = request_body.get('answers', []) if request_body else []
            normalized_answers = []
            for item in answers_payload:
                if not isinstance(item, dict):
                    continue
                question_number = item.get('questionNumber')
                answer_text = str(item.get('answer', '')).strip()
                try:
                    question_number = int(question_number)
                except (TypeError, ValueError):
                    continue
                if question_number <= 0:
                    continue

                normalized_answers.append({
                    'number': question_number,
                    'answer': answer_text
                })

            if not normalized_answers:
                return jsonify({'message': 'At least one answer is required'}), 400
            student_answers_text = format_answers_text(normalized_answers)
        else:
            upload_mode = request.form.get('uploadMode', 'file').strip().lower()
            if upload_mode == 'text':
                student_answers_text = request.form.get('studentAnswersText', '').strip()
            else:
                if 'studentAnswersFile' not in request.files:
                    return jsonify({'message': 'Student answers file is required'}), 400

                student_answers_file = request.files['studentAnswersFile']
                if not allowed_file(student_answers_file.filename, Config.ALLOWED_EXTENSIONS):
                    return jsonify({'message': 'Invalid file format. Allowed: TXT, PDF, DOCX'}), 400

                student_answers_text = extract_text_from_file(student_answers_file)

        if not student_answers_text:
            return jsonify({'message': 'Student answers are required'}), 400

        student_answers = parse_answers(student_answers_text)
        if not student_answers:
            return jsonify({'message': 'Invalid student answers format. Use A1: Answer text'}), 400

        assignment_questions = parse_assignment_questions(assignment)
        expected_question_numbers = {int(item.get('number')) for item in assignment_questions}
        answered_question_numbers = {int(item.get('number')) for item in student_answers}

        if expected_question_numbers and not expected_question_numbers.issubset(answered_question_numbers):
            missing_numbers = sorted(list(expected_question_numbers - answered_question_numbers))
            return jsonify({'message': f'Please answer all questions before submitting. Missing: {missing_numbers}'}), 400

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
            'student_answers': student_answers,
            'student_answers_filename': student_answers_file.filename if student_answers_file else None,
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
            has_evaluation = bool(evaluation and evaluation.get('results'))
            submission_status = str(submission.get('status', 'submitted') or 'submitted')
            if has_evaluation and submission_status == 'submitted':
                submission_status = 'evaluated'

            submissions.append({
                'id': submission_id,
                'studentId': submission.get('student_id', ''),
                'studentName': submission.get('student_name', ''),
                'studentEmail': submission.get('student_email', ''),
                'status': submission_status,
                'isEvaluated': has_evaluation,
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
                'subject': assignment.get('subject', ''),
                'questions': parse_assignment_questions(assignment)
            },
            'submissions': submissions
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch submissions: {str(e)}'}), 500


@workflow_bp.route('/teacher/submissions/<submission_id>', methods=['GET'])
@token_required
def get_teacher_submission_detail(payload, submission_id):
    """Teacher views one student's submitted answers for an assignment"""
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
            return jsonify({'message': 'You can only view your own assignment submissions'}), 403

        questions = parse_assignment_questions(assignment)
        student_answers = submission.get('student_answers', [])
        if not student_answers:
            student_answers = parse_answers(submission.get('student_answers_text', ''))

        answer_map = {int(item.get('number')): item.get('answer', '') for item in student_answers}
        answer_rows = []
        for question in questions:
            question_number = int(question.get('number'))
            answer_rows.append({
                'questionNumber': question_number,
                'question': question.get('question', ''),
                'marks': float(question.get('marks', 0)),
                'studentAnswer': answer_map.get(question_number, '')
            })

        return jsonify({
            'submission': {
                'id': submission_id,
                'status': submission.get('status', 'submitted'),
                'submittedAt': submission.get('submitted_at').isoformat() if submission.get('submitted_at') else None,
                'student': {
                    'id': submission.get('student_id', ''),
                    'name': submission.get('student_name', ''),
                    'email': submission.get('student_email', '')
                },
                'assignment': {
                    'id': submission.get('assignment_id', ''),
                    'title': assignment.get('title', ''),
                    'subject': assignment.get('subject', '')
                },
                'answers': answer_rows
            }
        }), 200
    except Exception as e:
        return jsonify({'message': f'Could not fetch submission details: {str(e)}'}), 500


@workflow_bp.route('/teacher/assignments/<assignment_id>/evaluate-all', methods=['POST'])
@token_required
def evaluate_all_submissions(payload, assignment_id):
    """Teacher evaluates all submitted responses for one assignment"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can evaluate submissions'}), 403

        assignment_object_id = parse_object_id(assignment_id)
        if not assignment_object_id:
            return jsonify({'message': 'Invalid assignment ID'}), 400

        assignment = assignments_collection.find_one({'_id': assignment_object_id})
        if not assignment:
            return jsonify({'message': 'Assignment not found'}), 404

        if assignment.get('teacher_id') != payload['user_id']:
            return jsonify({'message': 'You can evaluate only your own assignments'}), 403

        force_recheck = str(request.args.get('force', 'false')).lower() in ['1', 'true', 'yes']

        print(f"[EVALUATE_ALL] Starting evaluation for assignment {assignment_id}")
        ensure_model_answers_for_assignment(assignment)

        assignment_questions = parse_assignment_questions(assignment)
        if not assignment_questions:
            return jsonify({'message': 'Assignment has no valid questions for evaluation'}), 400

        print(f"[EVALUATE_ALL] Found {len(assignment_questions)} questions to evaluate")

        model_answers_map = {
            int(item.get('number')): str(item.get('answer', ''))
            for item in assignment.get('model_answers', [])
            if isinstance(item, dict) and item.get('number') is not None
        }
        if not model_answers_map:
            parsed_model_answers = parse_answers(assignment.get('model_answers_text', ''))
            model_answers_map = {
                int(item.get('number')): str(item.get('answer', ''))
                for item in parsed_model_answers
                if isinstance(item, dict) and item.get('number') is not None
            }

        submission_docs = list(submissions_collection.find({'assignment_id': assignment_id}))
        if not submission_docs:
            return jsonify({'message': 'No submissions found for this assignment'}), 404

        print(f"[EVALUATE_ALL] Found {len(submission_docs)} submissions to evaluate")
        submission_state = {}
        skipped = []
        for submission in submission_docs:
            submission_id = str(submission['_id'])

            existing_evaluation = evaluations_collection.find_one({'submission_id': submission_id})
            existing_results = []
            if existing_evaluation and not force_recheck:
                checkpoint = existing_evaluation.get('checkpoint_results', {})
                if isinstance(checkpoint, dict):
                    existing_results = checkpoint.get('questions', []) or []

                completed_results = existing_evaluation.get('results', {})
                if isinstance(completed_results, dict):
                    completed_questions = completed_results.get('questions', []) or []
                    if completed_questions:
                        existing_results = completed_questions

            expected_question_numbers = {
                int(question.get('number', 0) or 0)
                for question in assignment_questions
                if int(question.get('number', 0) or 0) > 0
            }
            existing_question_numbers = {
                int(item.get('questionNumber', 0) or 0)
                for item in existing_results
                if int(item.get('questionNumber', 0) or 0) > 0
            }

            is_already_complete = (
                bool(expected_question_numbers)
                and expected_question_numbers.issubset(existing_question_numbers)
            )

            if is_already_complete and not force_recheck:
                skipped.append({
                    'submissionId': submission_id,
                    'studentName': submission.get('student_name', ''),
                    'reason': 'Already evaluated'
                })
                continue

            parsed_answers = submission.get('student_answers', [])
            if not parsed_answers:
                parsed_answers = parse_answers(submission.get('student_answers_text', ''))

            answer_map = {}
            for answer_item in parsed_answers:
                if not isinstance(answer_item, dict):
                    continue
                number = answer_item.get('number')
                answer_text = str(answer_item.get('answer', '')).strip()
                try:
                    number = int(number)
                except Exception:
                    continue
                answer_map[number] = answer_text

            submission_state[submission_id] = {
                'submission': submission,
                'answers': answer_map,
                'results': [] if force_recheck else sort_question_results(existing_results)
            }

        if not submission_state:
            return jsonify({
                'message': 'All submissions are already evaluated',
                'assignmentId': assignment_id,
                'evaluatedCount': 0,
                'failedCount': 0,
                'skippedCount': len(skipped),
                'evaluatedSubmissionIds': [],
                'failed': [],
                'skipped': skipped
            }), 200

        failure_map = {}
        batch_endpoint_unavailable = False
        batch_fallback_used = False
        
        print(f"[EVALUATE_ALL] Starting question-wise evaluation for {len(assignment_questions)} questions")
        
        for question in assignment_questions:
            question_number = int(question.get('number'))
            question_text = str(question.get('question', ''))
            max_marks = float(question.get('marks', 0))
            model_answer = model_answers_map.get(question_number, '')

            print(f"[EVALUATE_ALL] Processing question {question_number}")

            question_with_marks = build_question_with_marks(question_text, max_marks)

            answers_payload = {}
            for submission_id, state in submission_state.items():
                existing_numbers = {
                    int(item.get('questionNumber', 0) or 0)
                    for item in state['results']
                    if int(item.get('questionNumber', 0) or 0) > 0
                }
                if question_number in existing_numbers:
                    continue

                student_answer = str(state['answers'].get(question_number, '')).strip()
                if student_answer:
                    answers_payload[submission_id] = student_answer

            if not answers_payload:
                print(f"[EVALUATE_ALL] No new answers for question {question_number}, skipping")
                continue

            if not batch_endpoint_unavailable:
                print(f"[EVALUATE_ALL] Attempting batch evaluation for {len(answers_payload)} answers")
                try:
                    batch_response = llama_service.batch_evaluate(
                        question=question_with_marks,
                        answers=answers_payload,
                        reference_answer=model_answer or None
                    )
                    print(f"[EVALUATE_ALL] Batch evaluation successful for question {question_number}")
                except LlamaServiceError as exc:
                    message = str(exc)
                    if 'HTTP 404' in message and '/batch-evaluate' in message:
                        batch_endpoint_unavailable = True
                        batch_fallback_used = True
                        print(f"[EVALUATE_ALL] Batch endpoint not available in Colab, switching to per-answer mode")
                    else:
                        raise RuntimeError(message) from exc
                else:
                    batch_results_map = extract_batch_results_map(batch_response)
                    for submission_id, student_answer in answers_payload.items():
                        try:
                            raw_result = batch_results_map.get(submission_id, {}) if isinstance(batch_results_map, dict) else {}
                            normalized = normalize_batch_question_result(
                                raw_result=raw_result,
                                question_number=question_number,
                                question_text=question_text,
                                max_marks=max_marks,
                                model_answer=model_answer,
                                student_answer=student_answer
                            )
                            submission_state[submission_id]['results'] = upsert_question_result(
                                submission_state[submission_id]['results'],
                                normalized
                            )
                            persist_evaluation_checkpoint(
                                submission=submission_state[submission_id]['submission'],
                                teacher_id=payload['user_id'],
                                question_results=submission_state[submission_id]['results']
                            )
                        except Exception as exc:
                            failure_map[submission_id] = str(exc)
                    continue

            print(f"[EVALUATE_ALL] Using per-answer evaluation for {len(answers_payload)} answers on question {question_number}")
            for submission_id, student_answer in answers_payload.items():
                try:
                    single_eval = evaluation_service.evaluate_answer(
                        question=question_text,
                        reference=model_answer,
                        student=student_answer,
                        marks=max_marks
                    )

                    normalized = {
                        'questionNumber': int(question_number),
                        'question': question_text,
                        'modelAnswer': str(single_eval.get('referenceAnswer') or model_answer),
                        'studentAnswer': student_answer,
                        'score': float(single_eval.get('finalScore', 0)),
                        'maxMarks': float(single_eval.get('maxMarks', max_marks)),
                        'similarity': float(single_eval.get('similarity', 0.0)),
                        'nliLabel': str(single_eval.get('nliLabel', 'evaluated')).lower().replace('_', ' '),
                        'feedback': str(single_eval.get('feedback', '')),
                        'llamaEnabled': bool(single_eval.get('llamaEnabled', True)),
                        'contextUsed': int(single_eval.get('contextUsed', 0) or 0),
                        'grade': str(single_eval.get('grade', 'evaluated'))
                    }

                    submission_state[submission_id]['results'] = upsert_question_result(
                        submission_state[submission_id]['results'],
                        normalized
                    )
                    persist_evaluation_checkpoint(
                        submission=submission_state[submission_id]['submission'],
                        teacher_id=payload['user_id'],
                        question_results=submission_state[submission_id]['results']
                    )
                except Exception as exc:
                    failure_map[submission_id] = str(exc)
                    continue

        evaluated_ids = []
        failed = []

        for submission_id, state in submission_state.items():
            try:
                question_results = sort_question_results(state['results'])
                if not question_results:
                    prior_failure = failure_map.get(submission_id)
                    if prior_failure:
                        raise Exception(prior_failure)
                    raise Exception('No evaluated answers found for submission')

                results = build_aggregate_results(question_results)

                submission = state['submission']

                evaluation_payload = {
                    'submission_id': submission_id,
                    'assignment_id': submission.get('assignment_id'),
                    'teacher_id': payload['user_id'],
                    'student_id': submission.get('student_id'),
                    'results': results,
                    'evaluation_mode': 'llama',
                    'released': False,
                    'evaluated_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'in_progress': False
                }

                evaluations_collection.update_one(
                    {'submission_id': submission_id},
                    {
                        '$set': evaluation_payload,
                        '$unset': {
                            'checkpoint_results': ''
                        }
                    },
                    upsert=True
                )

                submissions_collection.update_one(
                    {'_id': submission['_id']},
                    {
                        '$set': {
                            'status': 'evaluated',
                            'evaluated_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        }
                    }
                )

                evaluated_ids.append(submission_id)
            except Exception as exc:
                failed.append({
                    'submissionId': submission_id,
                    'studentName': state['submission'].get('student_name', ''),
                    'reason': str(exc),
                    'progressQuestions': len(state.get('results', []))
                })

        print(f"[EVALUATE_ALL] Evaluation complete: {len(evaluated_ids)} successful, {len(failed)} failed, {len(skipped)} skipped")
        if batch_fallback_used:
            print(f"[EVALUATE_ALL] Batch endpoint was unavailable during this run - used per-answer mode")

        return jsonify({
            'message': 'Evaluate all completed',
            'assignmentId': assignment_id,
            'evaluatedCount': len(evaluated_ids),
            'failedCount': len(failed),
            'skippedCount': len(skipped),
            'batchFallbackUsed': batch_fallback_used,
            'evaluatedSubmissionIds': evaluated_ids,
            'failed': failed,
            'skipped': skipped
        }), 200
    except RuntimeError as e:
        return jsonify({'message': f'Evaluate all failed: {str(e)}'}), 503
    except Exception as e:
        return jsonify({'message': f'Evaluate all failed: {str(e)}'}), 500


@workflow_bp.route('/teacher/submissions/<submission_id>/evaluate', methods=['POST'])
@token_required
def evaluate_submission(payload, submission_id):
    """Teacher evaluates a submission and stores results"""
    try:
        if not role_guard(payload, 'teacher'):
            return jsonify({'message': 'Only teachers can evaluate submissions'}), 403

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
        model_answers_text = ensure_model_answers_for_assignment(assignment)
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

        results = evaluation_service.evaluate_batch(
            questions=questions,
            model_answers=model_answers,
            student_answers=student_answers
        )

        results = convert_numpy_types(results)

        evaluation_payload = {
            'submission_id': submission_id,
            'assignment_id': submission.get('assignment_id'),
            'teacher_id': payload['user_id'],
            'student_id': submission.get('student_id'),
            'results': results,
            'evaluation_mode': 'llama',
            'released': False,
            'evaluated_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        evaluations_collection.update_one(
            {'submission_id': submission_id},
            {
                '$set': {
                    **evaluation_payload,
                    'in_progress': False
                },
                '$unset': {
                    'checkpoint_results': ''
                }
            },
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
            'message': 'Submission evaluated successfully',
            'submissionId': submission_id,
            'evaluationMode': 'llama',
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