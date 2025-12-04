"""
AI-Driven Adaptive Engine
AI autonomously determines Bloom level, difficulty, and generates all questions
"""

import json
import os
from typing import Optional, Dict, List
from engine.scoring import evaluate_answer
from models.session import SessionState
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def next_question(session: SessionState) -> Optional[Dict]:
    """
    AI generates the next question based on complete session analysis.
    
    Args:
        session: Current session state
    
    Returns:
        AI-generated question with autonomously determined Bloom level and difficulty
    """
    # Check if we've reached the maximum number of questions
    if session.question_number > session.max_questions:
        session.finished = True
        return None
    
    try:
        # Let AI analyze performance and generate next question
        q = generate_adaptive_question(session)
        
        if q is None:
            print("Error: No question generated")
            session.finished = True
            return None
        
        # Add question number to the question object
        q["number"] = session.question_number
        
        session.current_question = q
        
        # Update session with AI's chosen levels
        session.bloom_level = q.get("bloom", session.bloom_level)
        session.difficulty = q.get("difficulty", session.difficulty)
        
        return q
        
    except Exception as e:
        print(f"Error generating next question: {e}")
        session.finished = True
        return None


def generate_adaptive_question(session: SessionState) -> Optional[Dict]:
    """
    AI autonomously analyzes student performance and generates optimal next question.
    
    Args:
        session: Session state with complete history
    
    Returns:
        Generated question with AI-determined parameters
    """
    try:
        # Build context from session history
        history_context = build_history_summary(session.history)
        
        prompt = f"""You are an adaptive Python assessment AI. Analyze the student's complete learning trajectory and autonomously generate the optimal next question.

ASSESSMENT PROGRESS: Question {session.question_number} of {session.max_questions}

STUDENT PERFORMANCE HISTORY:
{history_context}

YOUR AUTONOMOUS DECISION-MAKING:

1. ANALYZE the student's:
   - Accuracy trends
   - Explanation quality patterns
   - Misconceptions and gaps
   - Learning velocity
   - Concept mastery
   - Response depth

2. DETERMINE optimal next question parameters:
   - Bloom's Taxonomy Level: Remember → Understand → Apply → Analyze → Evaluate
   - Difficulty: 1 (basic) → 5 (expert)
   - Topic focus based on performance patterns

3. GENERATE a targeted Python question that will:
   - Meet the student at their current level
   - Challenge them appropriately
   - Address any misconceptions
   - Build on demonstrated strengths
   - Advance their learning

BLOOM'S TAXONOMY LEVELS:
- Remember (1): "What is a variable?" "What does print() do?"
- Understand (2): "Explain why strings are immutable" "Describe how loops work"
- Apply (3): "Write code to reverse a list" "Create a function that..."
- Analyze (4): "Debug this code" "Compare two approaches" "What's wrong with..."
- Evaluate (5): "Justify when to use recursion" "Critique this implementation"

DIFFICULTY GUIDELINES:
1 = Basic syntax, simple concepts, direct recall
2 = Common patterns, straightforward problems
3 = Multiple concepts, moderate complexity
4 = Complex logic, edge cases, debugging
5 = Optimization, best practices, architectural decisions

ADAPTATION STRATEGY:
- Strong performance (>85%): Increase challenge (Bloom +1 or Difficulty +1)
- Good performance (70-85%): Maintain or slight increase
- Struggling (50-70%): Maintain level, provide practice
- Serious difficulty (<50%): Decrease complexity, reinforce fundamentals
- Misconceptions detected: Target them directly with focused questions
- High explanation quality: Explore conceptual depth
- Low explanation quality: Focus on understanding, not just answers

Return ONLY valid JSON:
{{
  "bloom": "Remember|Understand|Apply|Analyze|Evaluate",
  "bloom_number": 1-5,
  "difficulty": 1-5,
  "question": "Your generated Python question here",
  "answer": "Expected correct answer or approach",
  "ai_rationale": "Why you chose this level/difficulty/topic for this student",
  "targets": ["misconception or concept being assessed"]
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Structure the AI-generated question
        question = {
            "id": f"ai_{session.question_number}",
            "bloom": result.get("bloom", "Understand"),
            "bloom_number": result.get("bloom_number", 2),
            "difficulty": result.get("difficulty", 2),
            "question": result.get("question", ""),
            "answer": result.get("answer", ""),
            "ai_rationale": result.get("ai_rationale", ""),
            "targets": result.get("targets", []),
            "generated_by": "ai_adaptive_engine"
        }
        
        # Validate
        if not question["question"] or not question["answer"]:
            raise ValueError("AI did not generate complete question")
        
        print(f"AI generated Q{session.question_number}: Bloom={question['bloom']}, Difficulty={question['difficulty']}")
        print(f"AI Rationale: {question['ai_rationale'][:100]}...")
        
        return question
        
    except Exception as e:
        print(f"Error in AI question generation: {e}")
        return fallback_question(session.question_number, session.bloom_level, session.difficulty)


def build_history_summary(history: List[Dict]) -> str:
    """Build formatted summary of student's performance history."""
    if not history:
        return """No previous questions yet. This is the first question.

STARTING APPROACH:
- Begin with foundational assessment
- Start at Bloom Level 1-2 (Remember/Understand)
- Use Difficulty 1-2 to establish baseline
- Focus on core Python concepts (variables, types, basic operations)"""
    
    summary_parts = []
    
    # Overall statistics
    total = len(history)
    avg_accuracy = sum(e.get('accuracy', 0) for e in history) / total
    avg_explanation = sum(e.get('explanation_score', 0) for e in history) / total
    avg_overall = sum(e.get('final_score', 0) for e in history) / total
    
    summary_parts.append(f"""OVERALL PERFORMANCE ({total} questions completed):
- Average Accuracy: {avg_accuracy*100:.1f}%
- Average Explanation Quality: {avg_explanation*100:.1f}%
- Average Overall Score: {avg_overall*100:.1f}%
""")
    
    # Recent performance (last 3 questions)
    recent = history[-3:]
    summary_parts.append("\nRECENT QUESTIONS:")
    
    for i, evaluation in enumerate(recent, start=len(history)-len(recent)+1):
        question = evaluation.get('question', {})
        
        summary_parts.append(f"""
Question {i}:
  - Bloom: {question.get('bloom', 'N/A')} (Level {question.get('bloom_number', 'N/A')})
  - Difficulty: {question.get('difficulty', 'N/A')}/5
  - Accuracy: {evaluation.get('accuracy', 0)*100:.0f}%
  - Explanation: {evaluation.get('explanation_score', 0)*100:.0f}%
  - Score: {evaluation.get('final_score', 0)*100:.0f}%
  - Misconceptions: {', '.join(evaluation.get('misconceptions', [])) or 'None detected'}""")
    
    # Identify patterns
    summary_parts.append("\nPERFORMANCE PATTERNS:")
    
    # Accuracy trend
    if len(history) >= 3:
        recent_scores = [e.get('final_score', 0) for e in history[-3:]]
        if all(recent_scores[i] >= recent_scores[i-1] for i in range(1, len(recent_scores))):
            summary_parts.append("- ✓ Improving trend - scores increasing")
        elif all(recent_scores[i] <= recent_scores[i-1] for i in range(1, len(recent_scores))):
            summary_parts.append("- ⚠ Declining trend - scores decreasing")
        else:
            summary_parts.append("- • Mixed performance - inconsistent results")
    
    # Misconceptions tracking
    all_misconceptions = []
    for e in history:
        all_misconceptions.extend(e.get('misconceptions', []))
    
    if all_misconceptions:
        unique_misconceptions = list(set(all_misconceptions))
        summary_parts.append(f"- ⚠ Recurring issues: {', '.join(unique_misconceptions[:3])}")
    else:
        summary_parts.append("- ✓ No major misconceptions detected")
    
    # Explanation quality
    if avg_explanation < 0.5:
        summary_parts.append("- ⚠ Low explanation quality - may not fully understand concepts")
    elif avg_explanation > 0.8:
        summary_parts.append("- ✓ Strong explanations - demonstrates deep understanding")
    
    return '\n'.join(summary_parts)


def fallback_question(question_num: int, bloom: str, difficulty: int) -> Dict:
    """Fallback question if AI generation fails."""
    fallback_questions = {
        "Remember": "What is a variable in Python?",
        "Understand": "Explain the difference between a list and a tuple.",
        "Apply": "Write a function that returns the sum of numbers in a list.",
        "Analyze": "What's wrong with this code: def add(x, y): return x + y + z",
        "Evaluate": "When should you use a dictionary instead of a list?"
    }
    
    return {
        "id": f"fallback_{question_num}",
        "bloom": bloom,
        "difficulty": difficulty,
        "question": fallback_questions.get(bloom, "What is Python?"),
        "answer": "Expected answer varies based on question",
        "generated_by": "fallback_system"
    }


def score_response(session: SessionState, resp: Dict) -> Dict:
    """
    Score student response. Session levels are now set by AI, not rules.
    
    Args:
        session: Current session state
        resp: Dictionary with 'student_answer' and 'explanation' keys
    
    Returns:
        Evaluation dictionary with scores and misconceptions
    """
    try:
        # Validate response
        if "student_answer" not in resp or "explanation" not in resp:
            raise ValueError("Response missing required fields")
        
        # Evaluate the answer using AI
        evaluation = evaluate_answer(session.current_question, resp)
        
        # Store question info with evaluation for AI's future analysis
        evaluation['question'] = session.current_question
        
        # Record in history
        session.record_evaluation(evaluation)
        
        # Advance question counter
        session.question_number += 1
        
        # Note: We NO LONGER manually adjust difficulty/Bloom here
        # The AI will analyze complete history and make those decisions autonomously
        
        print(f"Scored response: Accuracy={evaluation.get('accuracy', 0)*100:.0f}%, "
              f"Explanation={evaluation.get('explanation_score', 0)*100:.0f}%, "
              f"Overall={evaluation.get('final_score', 0)*100:.0f}%")
        
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
            "misconceptions": [f"Error processing response: {str(e)}"],
            "question": session.current_question
        }
        session.record_evaluation(error_eval)
        return error_eval