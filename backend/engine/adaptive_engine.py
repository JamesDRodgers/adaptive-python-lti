import json
import os
from engine.scoring import evaluate_answer, generate_followup_question
from models.session import SessionState

# Load questions with error handling
QUESTIONS = []
try:
    questions_path = os.path.join(os.path.dirname(__file__), "questions.jsonl")
    with open(questions_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                try:
                    QUESTIONS.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error parsing question line: {line[:50]}... Error: {e}")
    
    if not QUESTIONS:
        raise ValueError("No valid questions loaded from questions.jsonl")
    
    print(f"Loaded {len(QUESTIONS)} questions successfully")
    
except FileNotFoundError:
    print("ERROR: questions.jsonl not found!")
    # Add fallback questions
    QUESTIONS = [
        {
            "id": 1,
            "bloom": 1,
            "difficulty": 1,
            "question": "What is a variable in Python?",
            "answer": "A variable is a named container that stores a value in memory",
            "misconceptions": []
        },
        {
            "id": 2,
            "bloom": 1,
            "difficulty": 2,
            "question": "What data type does the input() function return?",
            "answer": "string (str)",
            "misconceptions": []
        }
    ]
    print(f"Using {len(QUESTIONS)} fallback questions")


def select_question(bloom, difficulty, last_misconception):
    """
    Select an appropriate question based on Bloom level, difficulty, and misconceptions.
    
    Args:
        bloom: Bloom's taxonomy level (1-5)
        difficulty: Difficulty level (1-5)
        last_misconception: String describing misconception, or None
    
    Returns:
        Question dictionary
    """
    # If the last question revealed a misconception, generate a follow-up question
    if last_misconception:
        try:
            return generate_followup_question(bloom, difficulty, last_misconception)
        except Exception as e:
            print(f"Error generating follow-up question: {e}")
            # Fall through to search preloaded questions
    
    # Search for exact match
    for q in QUESTIONS:
        if q.get("bloom") == bloom and q.get("difficulty") == difficulty:
            return q
    
    # Search for same bloom level, any difficulty
    for q in QUESTIONS:
        if q.get("bloom") == bloom:
            return q
    
    # Search for same difficulty, any bloom level
    for q in QUESTIONS:
        if q.get("difficulty") == difficulty:
            return q
    
    # Fallback — first question
    if QUESTIONS:
        return QUESTIONS[0]
    
    # Emergency fallback if no questions loaded
    return {
        "id": 0,
        "bloom": 1,
        "difficulty": 1,
        "question": "What is Python?",
        "answer": "Python is a high-level programming language",
        "misconceptions": []
    }


def next_question(session: SessionState):
    """
    Get the next question for the session based on adaptive logic.
    
    Args:
        session: Current session state
    
    Returns:
        Question dictionary or None if assessment is finished
    """
    if session.question_number > session.max_questions:
        session.finished = True
        return None
    
    try:
        q = select_question(
            session.bloom_level,
            session.difficulty,
            session.last_misconception,
        )
        
        session.current_question = q
        return q
        
    except Exception as e:
        print(f"Error selecting next question: {e}")
        session.finished = True
        return None


def score_response(session: SessionState, resp):
    """
    Score a student's response and update session state adaptively.
    
    Args:
        session: Current session state
        resp: Dictionary with 'student_answer' and 'explanation' keys
    
    Returns:
        Evaluation dictionary with scores and misconceptions
    """
    try:
        # Evaluate the answer
        evaluation = evaluate_answer(session.current_question, resp)
        session.record_evaluation(evaluation)
        
        # Adaptive difficulty and Bloom level adjustment
        final_score = evaluation.get("final_score", 0)
        
        if final_score >= 0.85:
            # Student doing well - increase difficulty
            session.difficulty = min(5, session.difficulty + 1)
            session.bloom_level = min(5, session.bloom_level + 1)
        elif final_score < 0.5:
            # Student struggling - decrease difficulty
            session.difficulty = max(1, session.difficulty - 1)
            # Optionally decrease Bloom level for very low scores
            if final_score < 0.3:
                session.bloom_level = max(1, session.bloom_level - 1)
        
        # Update misconception tracking
        misconceptions = evaluation.get("misconceptions", [])
        if misconceptions and len(misconceptions) > 0:
            session.last_misconception = misconceptions[0]
        else:
            session.last_misconception = None
        
        # Advance question counter
        session.question_number += 1
        
        return evaluation
        
    except Exception as e:
        print(f"Error scoring response: {e}")
        # Return error evaluation
        session.question_number += 1
        error_eval = {
            "accuracy": 0.0,
            "explanation_score": 0.0,
            "final_score": 0.0,
            "misconceptions": ["Error processing response"]
        }
        session.record_evaluation(error_eval)
        return error_eval
