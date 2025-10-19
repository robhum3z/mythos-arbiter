class Architect:
    def reflect(self, text):
        return {"text": text, "scores": {"coherence": 0.7}}

class Oracle:
    def reflect(self, text):
        return {"text": text, "scores": {"coherence": 0.7}}

class Union:
    def reflect(self, a_text, o_text):
        return {"text": a_text + o_text, "scores": {"coherence": 0.7}}
