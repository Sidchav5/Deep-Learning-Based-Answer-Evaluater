# backend/services/evaluation_service.py
"""
Evaluation Service
Handles answer evaluation using ML models and RAG
"""
import numpy as np
from typing import Dict, List

from config import Config
from models import ml_models
from services.rag_service import rag_service


class EvaluationService:
    """Service for evaluating student answers"""
    
    @staticmethod
    def evaluate_answer(
        question: str,
        reference: str,
        student: str,
        marks: float,
        use_rag: bool = False
    ) -> Dict:
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
        
        # Validate student answer - check for empty or very short answers
        if not student or not isinstance(student, str):
            return {
                'finalScore': 0,
                'maxMarks': float(marks),
                'similarity': 0.0,
                'nliLabel': 'EMPTY_ANSWER',
                'nliConfidence': 0.0,
                'feedback': 'No answer provided. Please submit a response to receive marks.',
                'ragEnabled': False,
                'contextUsed': 0
            }
        
        # Check if answer is too short (less than 10 characters)
        if len(student.strip()) < 10:
            return {
                'finalScore': 0,
                'maxMarks': float(marks),
                'similarity': 0.0,
                'nliLabel': 'INSUFFICIENT_LENGTH',
                'nliConfidence': 0.0,
                'feedback': 'Answer is too short. Please provide a more complete response with sufficient detail.',
                'ragEnabled': False,
                'contextUsed': 0
            }
        
        # Extract features and get similarity
        features, similarity = ml_models.extract_features(student, reference, marks)
        
        # Perform NLI inference
        nli_label, nli_confidence = ml_models.nli_inference(student, reference)
        
        # Semantic gate: Very low similarity
        if similarity < 0.30:
            final_score = 0.0
            feedback = "Answer shows very low semantic similarity to the model answer. Please review the question and provide a more relevant response."
            nli_label = "LOW_SIMILARITY"
        else:
            # Get ANN prediction
            ann_score = ml_models.predict_score(features)
            ann_score = max(0, min(ann_score, marks))  # Clamp to valid range
            
            # Calculate similarity-based score
            similarity_score = similarity * marks
            
            # Hybrid scoring based on similarity level
            if similarity >= 0.85:
                # High similarity: Trust similarity more
                blended_score = 0.7 * similarity_score + 0.3 * ann_score
            elif similarity >= 0.75:
                # Medium-high similarity: Balanced blend
                blended_score = 0.5 * similarity_score + 0.5 * ann_score
            else:
                # Lower similarity: Trust ANN more
                blended_score = 0.3 * similarity_score + 0.7 * ann_score
            
            # Apply NLI-based modifiers
            if nli_label == "CONTRADICTION":
                blended_score *= 0.3  # Severe penalty
            elif nli_label == "NEUTRAL":
                blended_score *= 0.7  # Moderate penalty
            elif nli_label == "ENTAILMENT":
                blended_score *= 1.0  # No penalty
            
            # Final score (clamped to valid range)
            final_score = max(0.0, min(blended_score, marks))
            
            # Round to nearest integer: 3.5+ → 4, <3.5 → 3
            final_score = round(final_score)
            
            # Generate basic feedback
            feedback = EvaluationService._generate_basic_feedback(
                similarity, nli_label, final_score, marks
            )
        
        # Get RAG context and enhanced feedback if enabled
        rag_data = {}
        enhanced_feedback = None
        
        if use_rag:
            rag_data = rag_service.evaluate_with_rag(
                question=question,
                model_answer=reference,
                student_answer=student,
                marks=marks,
                use_rag=True
            )
            
            # Generate enhanced feedback with Groq if RAG is enabled
            if rag_data.get('rag_enabled'):
                enhanced_feedback = rag_service.generate_enhanced_feedback(
                    question=question,
                    model_answer=reference,
                    student_answer=student,
                    score=final_score,
                    max_marks=marks,
                    similarity=similarity,
                    nli_label=nli_label,
                    context=rag_data.get('context', [])
                )
        
        # Build result
        result = {
            'finalScore': int(final_score),  # Already rounded, convert to int
            'maxMarks': float(marks),
            'similarity': float(round(similarity, 4)),
            'nliLabel': nli_label,
            'nliConfidence': float(round(nli_confidence, 4)),
            'feedback': enhanced_feedback if enhanced_feedback else feedback,
            'ragEnabled': rag_data.get('rag_enabled', False),
            'contextUsed': len(rag_data.get('context', []))
        }
        
        return result
    
    @staticmethod
    def _generate_basic_feedback(similarity: float, nli_label: str, score: float, max_marks: float) -> str:
        """Generate basic feedback without LLM"""
        percentage = (score / max_marks * 100) if max_marks > 0 else 0
        
        # Base feedback on score
        if percentage >= 90:
            quality = "Excellent work!"
        elif percentage >= 75:
            quality = "Good answer with room for minor improvements."
        elif percentage >= 60:
            quality = "Satisfactory answer, but some key points are missing."
        elif percentage >= 40:
            quality = "Partial understanding shown, but significant gaps remain."
        else:
            quality = "Answer needs substantial improvement."
        
        # Add similarity info
        if similarity >= 0.85:
            sim_note = "Your answer is highly aligned with the model answer."
        elif similarity >= 0.70:
            sim_note = "Your answer shows good alignment with the model answer."
        elif similarity >= 0.50:
            sim_note = "Your answer shows moderate alignment with the model answer."
        else:
            sim_note = "Your answer shows limited alignment with the model answer."
        
        # Add NLI info
        if nli_label == "ENTAILMENT":
            nli_note = "Your answer is logically consistent with the model answer."
        elif nli_label == "NEUTRAL":
            nli_note = "Your answer is partially related but lacks complete coverage."
        elif nli_label == "CONTRADICTION":
            nli_note = "Your answer contains contradictory information."
        else:
            nli_note = ""
        
        return f"{quality} {sim_note} {nli_note}"
    
    @staticmethod
    def evaluate_batch(
        questions: List[Dict],
        model_answers: List[Dict],
        student_answers: List[Dict],
        use_rag: bool = False
    ) -> Dict:
        """
        Evaluate multiple Q&A pairs
        
        Args:
            questions: List of question dicts with {number, question, marks}
            model_answers: List of answer dicts with {number, answer}
            student_answers: List of answer dicts with {number, answer}
            use_rag: Whether to use RAG for enhanced feedback
            
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
                marks=q['marks'],
                use_rag=use_rag
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
                'ragEnabled': eval_result.get('ragEnabled', False),
                'contextUsed': eval_result.get('contextUsed', 0)
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
