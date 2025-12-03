class SessionState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.bloom_level=1
        self.difficulty=1
        self.max_questions=15
        self.question_number=1
        self.current_question=None
        self.finished=False
        self.history=[]
        self.last_misconception=None

    def record_evaluation(self, e):
        self.history.append(e)

    def summary(self):
        acc=sum(i['accuracy'] for i in self.history)/len(self.history)
        exp=sum(i['explanation_score'] for i in self.history)/len(self.history)
        final=sum(i['final_score'] for i in self.history)/len(self.history)
        return {"final_score":final,"average_accuracy":acc,"average_explanation":exp,"responses":self.history}
