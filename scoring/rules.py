from dataclasses import dataclass

@dataclass
class HallucinationRule:
    min_coh: float = 0.6
    max_ground: float = 0.4

    def is_productive(self, scores):
        return (
            scores.get("coherence", 0) >= self.min_coh
            and scores.get("grounding", 1) <= self.max_ground
        )
