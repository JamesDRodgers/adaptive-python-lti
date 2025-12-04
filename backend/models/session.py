class SessionState:
    """Manages the state of a student's assessment session with AI-driven adaptation."""
    
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset session to initial state."""
        # Starting parameters (AI will adjust these)
        self.bloom_level = "Remember"
        self.difficulty = 1
        
        # Session configuration
        self.max_questions = 10
        self.question_number = 1
        
        # Current state
        self.current_question = None
        self.finished = False
        
        # Performance tracking
        self.history = []  # Full evaluation history with questions
        
        # AI adaptation tracking
        self.ai_decisions = []  # Track AI's rationale for each question
        
        # Legacy fields (kept for compatibility, but AI now decides these)
        self.last_misconception = None
        self.asked_question_ids = set()

    def record_evaluation(self, evaluation):
        """Record an evaluation result with question context in history."""
        self.history.append(evaluation)
        
        # Track AI's decision rationale if present
        if isinstance(evaluation.get('question'), dict):
            question = evaluation['question']
            if 'ai_rationale' in question:
                self.ai_decisions.append({
                    'question_number': self.question_number - 1,
                    'bloom': question.get('bloom'),
                    'difficulty': question.get('difficulty'),
                    'rationale': question.get('ai_rationale'),
                    'score': evaluation.get('final_score', 0)
                })

    def summary(self):
        """Generate summary statistics for the session."""
        if not self.history:
            return {
                "final_score": 0.0,
                "average_accuracy": 0.0,
                "average_explanation": 0.0,
                "responses": [],
                "ai_adaptation_summary": "No questions completed"
            }
        
        acc = sum(i['accuracy'] for i in self.history) / len(self.history)
        exp = sum(i['explanation_score'] for i in self.history) / len(self.history)
        final = sum(i['final_score'] for i in self.history) / len(self.history)
        
        # Generate AI adaptation narrative
        adaptation_summary = self._generate_adaptation_summary()
        
        return {
            "final_score": final,
            "average_accuracy": acc,
            "average_explanation": exp,
            "responses": self.history,
            "total_questions": len(self.history),
            "ai_adaptation_summary": adaptation_summary,
            "ai_decisions": self.ai_decisions
        }
    
    def _generate_adaptation_summary(self) -> str:
        """Generate human-readable summary of AI's adaptation decisions."""
        if not self.ai_decisions:
            return "AI-driven adaptive assessment with autonomous question generation"
        
        summary_parts = []
        
        # Starting and ending levels
        first = self.ai_decisions[0]
        last = self.ai_decisions[-1]
        
        summary_parts.append(
            f"Started at Bloom Level '{first['bloom']}' (Difficulty {first['difficulty']}), "
            f"progressed to '{last['bloom']}' (Difficulty {last['difficulty']})"
        )
        
        # Performance trend
        scores = [d['score'] for d in self.ai_decisions]
        avg_first_half = sum(scores[:len(scores)//2]) / max(len(scores)//2, 1)
        avg_second_half = sum(scores[len(scores)//2:]) / max(len(scores) - len(scores)//2, 1)
        
        if avg_second_half > avg_first_half + 0.1:
            summary_parts.append("Performance improved throughout assessment")
        elif avg_second_half < avg_first_half - 0.1:
            summary_parts.append("Challenges increased to maintain appropriate difficulty")
        else:
            summary_parts.append("Maintained consistent performance level")
        
        return ". ".join(summary_parts)