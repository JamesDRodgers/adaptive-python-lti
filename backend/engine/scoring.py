import os
import json
from openai import OpenAI

# For deployment: Set OPENAI_API_KEY in your hosting platform's environment variables
# Render: Dashboard → Environment → Add OPENAI_API_KEY
# Railway: Variables tab → Add OPENAI_API_KEY
# Fly.io: fly secrets set OPENAI_API_KEY=sk-...

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def evaluate_answer(question, resp):
    """Evaluate a student's answer using OpenAI API with error handling."""
    try:
        prompt = f"""Evaluate the student's response to this Python question.

Question: {question['question']}
Correct Answer: {question['answer']}
Student Answer: {resp.get('student_answer', '')}
Student Explanation: {resp.get('explanation', '')}

Evaluate the response and return ONLY valid JSON in this exact format:
{{
 "accuracy": 0.0,
 "explanation_score": 0.0,
 "final_score": 0.0,
 "misconceptions": []
}}

Where:
- accuracy: 0.0-1.0 score for correctness of the answer
- explanation_score: 0.0-1.0 score for quality of explanation
- final_score: weighted average of accuracy and explanation
- misconceptions: array of strings describing any misconceptions (empty if none)
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate required fields
        required_fields = ["accuracy", "explanation_score", "final_score", "misconceptions"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return {
            "accuracy": 0.0,
            "explanation_score": 0.0,
            "final_score": 0.0,
            "misconceptions": ["Error evaluating response"]
        }
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {
            "accuracy": 0.0,
            "explanation_score": 0.0,
            "final_score": 0.0,
            "misconceptions": ["System error during evaluation"]
        }


def generate_followup_question(bloom, difficulty, misconception):
    """Generate a follow-up question targeting a specific misconception."""
    try:
        prompt = f"""Generate a Python programming question for a first-year student.

Target Bloom's Taxonomy Level: {bloom} (1=Remember, 2=Understand, 3=Apply, 4=Analyze, 5=Evaluate)
Difficulty: {difficulty} (1-5 scale)
Address this misconception: {misconception}

Return ONLY valid JSON in this exact format:
{{
 "id": 999,
 "bloom": {bloom},
 "difficulty": {difficulty},
 "question": "Clear, specific question text here",
 "answer": "Correct answer here",
 "misconceptions": []
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate required fields
        required_fields = ["id", "bloom", "difficulty", "question", "answer", "misconceptions"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        return result
        
    except Exception as e:
        print(f"Error generating follow-up question: {e}")
        # Return a safe fallback question
        return {
            "id": 999,
            "bloom": bloom,
            "difficulty": difficulty,
            "question": "Explain the concept that caused difficulty in the previous question.",
            "answer": "A clear explanation of the concept",
            "misconceptions": []
        }
