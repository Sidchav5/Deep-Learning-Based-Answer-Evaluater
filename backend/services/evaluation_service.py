# backend/services/evaluation_service.py
"""
Evaluation Service
Handles answer evaluation using external Llama pipeline.
"""
import re
from typing import Dict, List

from services.llama_service import llama_service


class EvaluationService:
    """Service for evaluating student answers"""

    @staticmethod
    def evaluate_answer(question: str, reference: str, student: str, marks: float) -> Dict:
        """
        Evaluate a single answer with hybrid scoring system
        
        Args:
            question: The question text
            reference: Model/correct answer
            student: Student's answer
            marks: Maximum marks for this question
            use_rag: Whether to use RAG for enhanced feedback
            
        Returns:
            Dictionary with evaluation results
        """
        
        if not student or not isinstance(student, str):
            return {
                'finalScore': 0,
                'maxMarks': float(marks),
                'similarity': 0.0,
                'nliLabel': 'EMPTY_ANSWER',
                'nliConfidence': 0.0,
                'feedback': 'No answer provided. Please submit a response to receive marks.',
                'llamaEnabled': False,
                'contextUsed': 0
            }

        if len(student.strip()) < 10:
            return {
                'finalScore': 0,
                'maxMarks': float(marks),
                'similarity': 0.0,
                'nliLabel': 'INSUFFICIENT_LENGTH',
                'nliConfidence': 0.0,
                'feedback': 'Answer is too short. Please provide a more complete response with sufficient detail.',
                'llamaEnabled': False,
                'contextUsed': 0
            }

        if not llama_service.is_available():
            raise Exception('Llama API is not configured. Set LLAMA_API_BASE_URL in backend/.env.')

        marks_int = int(round(float(marks)))
        question_with_marks = (
            question
            if re.search(r'Marks\s*:\s*\d+', question, re.IGNORECASE)
            else f"{question}\nMarks: {marks_int}"
        )

        llama_result = llama_service.evaluate_answer(
            question=question_with_marks,
            student_answer=student,
            semantic_weight=0.7,
            keyword_weight=0.3
        )

        if not llama_result:
            raise Exception('No response from Llama evaluation API')

        semantic_similarity = float(llama_result.get('semantic_similarity', 0.0))
        awarded_marks = llama_result.get('awarded_marks')
        if awarded_marks is None:
            awarded_marks = float(llama_result.get('final_score', 0.0)) * float(marks)

        final_score = max(0.0, min(float(awarded_marks), float(marks)))
        final_score = round(final_score)

        grade = str(llama_result.get('grade', 'evaluated'))
        feedback = (
            f"Llama pipeline evaluation: {grade}. "
            f"Semantic similarity: {semantic_similarity:.2%}, "
            f"awarded marks: {final_score}/{marks_int}."
        )

        return {
            'finalScore': int(final_score),
            'maxMarks': float(marks),
            'similarity': float(round(semantic_similarity, 4)),
            'nliLabel': grade.upper().replace(' ', '_'),
            'nliConfidence': 0.0,
            'feedback': feedback,
            'llamaEnabled': True,
            'contextUsed': 0,
            'referenceAnswer': llama_result.get('reference_answer', reference),
            'grade': grade
        }

    @staticmethod
    def evaluate_batch(questions: List[Dict], model_answers: List[Dict], student_answers: List[Dict]) -> Dict:
        """
        Evaluate multiple Q&A pairs
        
        Args:
            questions: List of question dicts with {number, question, marks}
            model_answers: List of answer dicts with {number, answer}
            student_answers: List of answer dicts with {number, answer}
        Returns:
            Dictionary with overall results and individual question results
        """
        
        # Map questions to answers
        model_dict = {a['number']: a['answer'] for a in model_answers}
        student_dict = {a['number']: a['answer'] for a in student_answers}
        
        results_list = []
        total_score = 0
        total_max_marks = 0
        total_similarity = 0
        
        for q in questions:
            q_num = q['number']
            model_ans = model_dict.get(q_num, '')
            student_ans = student_dict.get(q_num, '')
            
            if not model_ans or not student_ans:
                continue
            
            # Evaluate this question
            eval_result = EvaluationService.evaluate_answer(
                question=q['question'],
                reference=model_ans,
                student=student_ans,
                marks=q['marks']
            )
            
            # Build result for this question
            question_result = {
                'questionNumber': q_num,
                'question': q['question'],
                'modelAnswer': model_ans,
                'studentAnswer': student_ans,
                'score': float(eval_result['finalScore']),
                'maxMarks': float(eval_result['maxMarks']),
                'similarity': float(eval_result['similarity']),
                'nliLabel': eval_result['nliLabel'].lower().replace('_', ' '),
                'feedback': eval_result['feedback'],
                'llamaEnabled': eval_result.get('llamaEnabled', True),
                'contextUsed': eval_result.get('contextUsed', 0),
                'grade': eval_result.get('grade', '')
            }
            
            results_list.append(question_result)
            total_score += eval_result['finalScore']
            total_max_marks += eval_result['maxMarks']
            total_similarity += eval_result['similarity']
        
        # Calculate overall metrics
        total_questions = len(results_list)
        percentage = (total_score / total_max_marks * 100) if total_max_marks > 0 else 0
        average_similarity = total_similarity / total_questions if total_questions > 0 else 0
        
        return {
            'totalScore': float(round(total_score, 2)),
            'totalMaxMarks': float(total_max_marks),
            'percentage': float(round(percentage, 2)),
            'totalQuestions': int(total_questions),
            'averageSimilarity': float(round(average_similarity, 4)),
            'questions': results_list
        }


# Create singleton instance
evaluation_service = EvaluationService()
