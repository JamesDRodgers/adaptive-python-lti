import json
import os
import random
from typing import Optional, Dict, List
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
            "bloom": "Remember",
            "difficulty": 1,
            "question": "What is a variable in Python?",
            "answer": "A variable is a named container that stores a value in memory",
            "misconceptions": []
        },
        {
            "id": 2,
            "bloom": "Remember",
            "difficulty": 2,
            "question": "What data type does the input() function return?",
            "answer": "string (str)",
            "misconceptions": []
        }
    ]
    print(f"Using {len(QUESTIONS)} fallback questions")


def select_question(bloom: str, difficulty: int, last_misconception: Optional[str], 
                    asked_question_ids: set) -> Optional[Dict]:
    """
    Select an appropriate question based on Bloom level, difficulty, and misconceptions.
    Avoids asking the same question twice.
    
    Args:
        bloom: Bloom's taxonomy verb (Remember, Understand, Apply, Analyze, Evaluate)
        difficulty: Difficulty level (1-5)
        last_misconception: String describing misconception, or None
        asked_question_ids: Set of question IDs already asked
    
    Returns:
        Question dictionary or None if no suitable question found
    """
    # If the last question revealed a misconception, generate a follow-up question
    if last_misconception:
        try:
            followup = generate_followup_question(bloom, difficulty, last_misconception)
            if followup:
                return followup
        except Exception as e:
            print(f"Error generating follow-up question: {e}")
            # Fall through to search preloaded questions
    
    # Filter out already-asked questions
    available_questions = [q for q in QUESTIONS if q.get("id") not in asked_question_ids]
    
    if not available_questions:
        print("Warning: All questions have been asked. Allowing repeats.")
        available_questions = QUESTIONS
    
    # Priority 1: Exact match (bloom AND difficulty)
    exact_matches = [
        q for q in available_questions 
        if q.get("bloom") == bloom and q.get("difficulty") == difficulty
    ]
    if exact_matches:
        return random.choice(exact_matches)
    
    # Priority 2: Same bloom level, adjacent difficulty (±1)
    adjacent_diff_matches = [
        q for q in available_questions
        if q.get("bloom") == bloom and abs(q.get("difficulty", 0) - difficulty) <= 1
    ]
    if adjacent_diff_matches:
        return random.choice(adjacent_diff_matches)
    
    # Priority 3: Same bloom level, any difficulty
    bloom_matches = [q for q in available_questions if q.get("bloom") == bloom]
    if bloom_matches:
        return random.choice(bloom_matches)
    
    # Priority 4: Adjacent bloom level, same difficulty
    bloom_order = ["Remember", "Understand", "Apply", "Analyze", "Evaluate"]
    try:
        current_idx = bloom_order.index(bloom)
        adjacent_blooms = []
        if current_idx > 0:
            adjacent_blooms.append(bloom_order[current_idx - 1])
        if current_idx < len(bloom_order) - 1:
            adjacent_blooms.append(bloom_order[current_idx + 1])
        
        adjacent_bloom_matches = [
            q for q in available_questions
            if q.get("bloom") in adjacent_blooms and q.get("difficulty") == difficulty
        ]
        if adjacent_bloom_matches:
            return random.choice(adjacent_bloom_matches)
    except (ValueError, IndexError):
        pass
    
    # Priority 5: Same difficulty, any bloom level
    diff_matches = [q for q in available_questions if q.get("difficulty") == difficulty]
    if diff_matches:
        return random.choice(diff_matches)
    
    # Fallback: Random available question
    if available_questions:
        return random.choice(available_questions)
    
    # Emergency fallback if no questions available
    return {
        "id": 0,
        "bloom": bloom,
        "difficulty": difficulty,
        "question": "What is Python?",
        "answer": "Python is a high-level programming language",
        "misconceptions": []
    }


def next_question(session: SessionState) -> Optional[Dict]:
    """
    Get the next question for the session based on adaptive logic.
    
    Args:
        session: Current session state
    
    Returns:
        Question dictionary or None if assessment is finished
    """
    # Check if assessment is complete
    if session.question_number > session.max_questions:
        session.finished = True
        return None
    
    try:
        # Select question based on current session state
        q = select_question(
            bloom=session.bloom_level,
            difficulty=session.difficulty,
            last_misconception=session.last_misconception,
            asked_question_ids=session.asked_question_ids
        )
        
        if q is None:
            print("Error: No question selected")
            session.finished = True
            return None
        
        # Track that we're asking this question
        if q.get("id"):
            session.asked_question_ids.add(q["id"])
        
        session.current_question = q
        return q
        
    except Exception as e:
        print(f"Error selecting next question: {e}")
        session.finished = True
        return None


def score_response(session: SessionState, resp: Dict) -> Dict:
    """
    Score a student's response and update session state adaptively.
    
    Args:
        session: Current session state
        resp: Dictionary with 'student_answer' and 'explanation' keys
    
    Returns:
        Evaluation dictionary with scores and misconceptions
    """
    try:
        # Validate response has required fields
        if "student_answer" not in resp or "explanation" not in resp:
            raise ValueError("Response missing required fields")
        
        # Evaluate the answer
        evaluation = evaluate_answer(session.current_question, resp)
        
        # Record evaluation in history
        session.record_evaluation(evaluation)
        
        # Advance question counter FIRST (so next_question check works correctly)
        session.question_number += 1
        
        # Extract final score for adaptive logic
        final_score = evaluation.get("final_score", 0)
        
        # Bloom progression order
        bloom_order = ["Remember", "Understand", "Apply", "Analyze", "Evaluate"]
        current_bloom_idx = bloom_order.index(session.bloom_level) if session.bloom_level in bloom_order else 0
        
        # Adaptive difficulty and Bloom level adjustment
        if final_score >= 0.85:
            # Student doing very well - increase both
            session.difficulty = min(5, session.difficulty + 1)
            if current_bloom_idx < len(bloom_order) - 1:
                session.bloom_level = bloom_order[current_bloom_idx + 1]
            print(f"Performance excellent ({final_score:.2f}). Increasing to Bloom '{session.bloom_level}', Difficulty {session.difficulty}")
            
        elif final_score >= 0.70:
            # Student doing well - increase difficulty only
            session.difficulty = min(5, session.difficulty + 1)
            print(f"Performance good ({final_score:.2f}). Increasing difficulty to {session.difficulty}")
            
        elif final_score < 0.50:
            # Student struggling - decrease difficulty
            session.difficulty = max(1, session.difficulty - 1)
            print(f"Performance struggling ({final_score:.2f}). Decreasing difficulty to {session.difficulty}")
            
            # For very low scores, also decrease Bloom level
            if final_score < 0.30 and current_bloom_idx > 0:
                session.bloom_level = bloom_order[current_bloom_idx - 1]
                print(f"Performance very low ({final_score:.2f}). Decreasing to Bloom '{session.bloom_level}'")
        else:
            # Score between 0.50-0.70: maintain current level
            print(f"Performance adequate ({final_score:.2f}). Maintaining Bloom '{session.bloom_level}', Difficulty {session.difficulty}")
        
        # Update misconception tracking
        misconceptions = evaluation.get("misconceptions", [])
        if misconceptions and len(misconceptions) > 0:
            session.last_misconception = misconceptions[0]
            print(f"Misconception detected: {session.last_misconception}")
        else:
            session.last_misconception = None
        
        return evaluation
        
    except Exception as e:
        print(f"Error scoring response: {e}")
        
        # Still advance question counter on error
        session.question_number += 1
        
        # Return error evaluation
        error_eval = {
            "accuracy": 0.0,
            "explanation_score": 0.0,
            "final_score": 0.0,
            "misconceptions": [f"Error processing response: {str(e)}"]
        }
        session.record_evaluation(error_eval)
        return error_eval