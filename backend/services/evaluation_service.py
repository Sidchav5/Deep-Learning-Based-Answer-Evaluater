# backend/services/evaluation_service.py
"""
Evaluation Service
Handles answer evaluation using ML models and RAG
"""
import numpy as np
import re
from typing import Dict, List

from config import Config
from models import ml_models
from services.llama_service import llama_service, LlamaApiError
from services.rag_service import rag_service


class EvaluationService:
    """Service for evaluating student answers"""

    @staticmethod
    def _safe_float(value, default=0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _tokenize(text: str) -> set:
        """Tokenize text for fallback lexical similarity"""
        if not text or not isinstance(text, str):
            return set()
        return set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower()))

    @staticmethod
    def _fallback_similarity(reference: str, student: str) -> float:
        """Compute a simple lexical overlap similarity for fallback mode"""
        reference_tokens = EvaluationService._tokenize(reference)
        student_tokens = EvaluationService._tokenize(student)

        if not reference_tokens or not student_tokens:
            return 0.0

        intersection = len(reference_tokens.intersection(student_tokens))
        union = len(reference_tokens.union(student_tokens))

        if union == 0:
            return 0.0

        return float(intersection / union)
    
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
    def evaluate_answer_llama(
        question: str,
        reference: str,
        student: str,
        marks: float
    ) -> Dict:
        """Evaluate one answer using external Llama pipeline."""

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

        try:
            llama_result = llama_service.evaluate_answer(
                question=question,
                reference=reference,
                student=student,
                marks=marks,
                use_generated_reference=bool(Config.LLAMA_USE_GENERATED_REFERENCE)
            )
        except LlamaApiError as e:
            raise Exception(str(e))

        if not llama_result:
            raise Exception('No response payload from Llama evaluation API')

        similarity = EvaluationService._safe_float(
            llama_result.get('semantic_similarity', llama_result.get('similarity', 0.0)),
            0.0
        )

        awarded_marks = llama_result.get('awarded_marks')
        if awarded_marks is None:
            awarded_marks = llama_result.get('final_score', 0.0)

        score = EvaluationService._safe_float(awarded_marks, 0.0)
        # Some APIs return normalized score (0..1); map to marks if needed.
        if score <= 1.0 and float(marks) > 1.0:
            score *= float(marks)

        nli_label = str(
            llama_result.get('nli_label')
            or llama_result.get('nliLabel')
            or 'ENTAILMENT'
        ).upper().replace(' ', '_')

        feedback = str(
            llama_result.get('feedback')
            or llama_result.get('explanation')
            or 'Llama pipeline evaluation completed.'
        )

        if feedback == 'Llama pipeline evaluation completed.':
            grade = str(llama_result.get('grade', '')).strip()
            keyword_coverage = EvaluationService._safe_float(llama_result.get('keyword_coverage', 0.0), 0.0)
            if grade:
                feedback = (
                    f"Llama grade: {grade}. "
                    f"Semantic similarity: {round(similarity, 4)}, "
                    f"keyword coverage: {round(keyword_coverage, 4)}."
                )

        score = max(0.0, min(score, float(marks)))

        return {
            'finalScore': int(round(score)),
            'maxMarks': float(marks),
            'similarity': float(round(similarity, 4)),
            'nliLabel': nli_label,
            'nliConfidence': float(round(EvaluationService._safe_float(llama_result.get('confidence', 0.0), 0.0), 4)),
            'feedback': feedback,
            'llamaEnabled': True,
            'contextUsed': int(EvaluationService._safe_float(llama_result.get('context_used', 0), 0)),
            'llamaReferenceAnswer': str(llama_result.get('reference_answer') or '').strip()
        }

    @staticmethod
    def evaluate_answer_combined(
        question: str,
        reference: str,
        student: str,
        marks: float,
        use_rag: bool = False
    ) -> Dict:
        """Evaluate with both local ML and Llama, then blend scores."""
        local_result = EvaluationService.evaluate_answer(
            question=question,
            reference=reference,
            student=student,
            marks=marks,
            use_rag=use_rag
        )
        llama_result = EvaluationService.evaluate_answer_llama(
            question=question,
            reference=reference,
            student=student,
            marks=marks
        )

        local_score = EvaluationService._safe_float(local_result.get('finalScore', 0.0))
        llama_score = EvaluationService._safe_float(llama_result.get('finalScore', 0.0))
        local_similarity = EvaluationService._safe_float(local_result.get('similarity', 0.0))
        llama_similarity = EvaluationService._safe_float(llama_result.get('similarity', 0.0))

        combined_score = (local_score * 0.5) + (llama_score * 0.5)
        combined_similarity = (local_similarity * 0.5) + (llama_similarity * 0.5)
        combined_score = max(0.0, min(combined_score, float(marks)))

        local_feedback = str(local_result.get('feedback', '')).strip()
        llama_feedback = str(llama_result.get('feedback', '')).strip()
        combined_feedback = (
            f"Combined evaluation completed. Local ML score: {int(round(local_score))}/{int(float(marks))}, "
            f"Llama score: {int(round(llama_score))}/{int(float(marks))}. "
            f"Local feedback: {local_feedback} Llama feedback: {llama_feedback}"
        )

        return {
            'finalScore': int(round(combined_score)),
            'maxMarks': float(marks),
            'similarity': float(round(combined_similarity, 4)),
            'nliLabel': local_result.get('nliLabel', 'COMBINED'),
            'nliConfidence': float(round(EvaluationService._safe_float(local_result.get('nliConfidence', 0.0), 0.0), 4)),
            'feedback': combined_feedback,
            'ragEnabled': local_result.get('ragEnabled', False),
            'llamaEnabled': llama_result.get('llamaEnabled', True),
            'contextUsed': int(local_result.get('contextUsed', 0)) + int(llama_result.get('contextUsed', 0)),
            'llamaReferenceAnswer': str(llama_result.get('llamaReferenceAnswer') or '').strip()
        }

    @staticmethod
    def evaluate_batch_mode(
        questions: List[Dict],
        model_answers: List[Dict],
        student_answers: List[Dict],
        mode: str,
        use_rag: bool = False
    ) -> Dict:
        """Evaluate in selected mode: local, llama, or auto(combined)."""
        selected_mode = (mode or Config.EVALUATION_MODE or 'auto').lower()
        if selected_mode == 'combined':
            selected_mode = 'auto'

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

            if selected_mode == 'local':
                eval_result = EvaluationService.evaluate_answer(
                    question=q['question'],
                    reference=model_ans,
                    student=student_ans,
                    marks=q['marks'],
                    use_rag=use_rag
                )
            elif selected_mode == 'llama':
                eval_result = EvaluationService.evaluate_answer_llama(
                    question=q['question'],
                    reference=model_ans,
                    student=student_ans,
                    marks=q['marks']
                )
            else:
                eval_result = EvaluationService.evaluate_answer_combined(
                    question=q['question'],
                    reference=model_ans,
                    student=student_ans,
                    marks=q['marks'],
                    use_rag=use_rag
                )

            question_result = {
                'questionNumber': q_num,
                'question': q['question'],
                'modelAnswer': model_ans,
                'teacherModelAnswer': model_ans,
                'llamaModelAnswer': str(eval_result.get('llamaReferenceAnswer') or '').strip(),
                'studentAnswer': student_ans,
                'score': float(eval_result['finalScore']),
                'maxMarks': float(eval_result['maxMarks']),
                'similarity': float(eval_result['similarity']),
                'nliLabel': str(eval_result['nliLabel']).lower().replace('_', ' '),
                'feedback': eval_result['feedback'],
                'ragEnabled': eval_result.get('ragEnabled', False),
                'llamaEnabled': eval_result.get('llamaEnabled', selected_mode in ['llama', 'auto']),
                'contextUsed': eval_result.get('contextUsed', 0)
            }

            results_list.append(question_result)
            total_score += eval_result['finalScore']
            total_max_marks += eval_result['maxMarks']
            total_similarity += eval_result['similarity']

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
    def evaluate_answer_fallback(
        question: str,
        reference: str,
        student: str,
        marks: float,
        use_rag: bool = False
    ) -> Dict:
        """
        Evaluate a single answer using fallback lexical scoring when ML models are unavailable
        """
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

        similarity = EvaluationService._fallback_similarity(reference, student)

        if similarity >= 0.75:
            nli_label = 'ENTAILMENT'
        elif similarity >= 0.4:
            nli_label = 'NEUTRAL'
        else:
            nli_label = 'LOW_SIMILARITY'

        final_score = max(0.0, min(similarity * float(marks), float(marks)))
        final_score = round(final_score)

        feedback = EvaluationService._generate_basic_feedback(
            similarity=similarity,
            nli_label=nli_label,
            score=final_score,
            max_marks=marks
        )

        feedback += ' (Fallback scoring mode used: lexical overlap.)'

        return {
            'finalScore': int(final_score),
            'maxMarks': float(marks),
            'similarity': float(round(similarity, 4)),
            'nliLabel': nli_label,
            'nliConfidence': 0.0,
            'feedback': feedback,
            'ragEnabled': False,
            'contextUsed': 0
        }

    @staticmethod
    def evaluate_batch_fallback(
        questions: List[Dict],
        model_answers: List[Dict],
        student_answers: List[Dict],
        use_rag: bool = False
    ) -> Dict:
        """Evaluate multiple Q&A pairs using fallback mode"""
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

            eval_result = EvaluationService.evaluate_answer_fallback(
                question=q['question'],
                reference=model_ans,
                student=student_ans,
                marks=q['marks'],
                use_rag=use_rag
            )

            question_result = {
                'questionNumber': q_num,
                'question': q['question'],
                'modelAnswer': model_ans,
                'teacherModelAnswer': model_ans,
                'llamaModelAnswer': '',
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
                'teacherModelAnswer': model_ans,
                'llamaModelAnswer': '',
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
