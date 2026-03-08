# backend/utils/parsers.py
"""
Text parsing utilities for questions and answers
"""
import re
from typing import List, Dict, Tuple


def parse_questions(text: str) -> List[Dict]:
    """
    Parse questions from text format: "Q1: [5 marks] Question? | Q2: [10 marks] Question?"
    
    Args:
        text: Raw text containing questions
        
    Returns:
        List of dicts with {number, question, marks}
    """
    questions = []
    
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


def parse_answers(text: str) -> List[Dict]:
    """
    Parse answers from text format: "A1: Answer text | A2: Answer text"
    
    Args:
        text: Raw text containing answers
        
    Returns:
        List of dicts with {number, answer}
    """
    answers = []
    
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


def map_qa_pairs(
    questions: List[Dict],
    model_answers: List[Dict],
    student_answers: List[Dict]
) -> List[Tuple[Dict, str, str]]:
    """
    Map questions to their corresponding model and student answers
    
    Args:
        questions: List of question dicts
        model_answers: List of model answer dicts
        student_answers: List of student answer dicts
        
    Returns:
        List of tuples (question_dict, model_answer, student_answer)
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
