class SessionState:
    """Manages the state of a student's assessment session."""
    
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset session to initial state."""
        self.bloom_level = 1
        self.difficulty = 1
        self.max_questions = 15
        self.question_number = 1
        self.current_question = None
        self.finished = False
        self.history = []
        self.last_misconception = None
        self.asked_question_ids = set()  # Track questions already asked

    def record_evaluation(self, evaluation):
        """Record an evaluation result in history."""
        self.history.append(evaluation)

    def summary(self):
        """Generate summary statistics for the session."""
        if not self.history:
            return {
                "final_score": 0.0,
                "average_accuracy": 0.0,
                "average_explanation": 0.0,
                "responses": []
            }
        
        acc = sum(i['accuracy'] for i in self.history) / len(self.history)
        exp = sum(i['explanation_score'] for i in self.history) / len(self.history)
        final = sum(i['final_score'] for i in self.history) / len(self.history)
        
        return {
            "final_score": final,
            "average_accuracy": acc,
            "average_explanation": exp,
            "responses": self.history
        }
