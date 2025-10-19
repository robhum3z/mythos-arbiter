# Adaptive scoring engine with EMA baselines and gentle weight nudging.

from dataclasses import dataclass
from time import time
from sqlmodel import Session, select
from db_init import engine, Weights
from config import settings

@dataclass
class Scores:
    coherence: float
    grounding: float
    illumination: float

def clamp(x: float, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, x))

def normalize(a: float, b: float, c: float):
    total = max(1e-9, a + b + c)
    return a/total, b/total, c/total

def _get_weights(session: Session) -> Weights:
    row = session.exec(select(Weights)).first()
    if not row:
        row = Weights()
        session.add(row); session.commit(); session.refresh(row)
    return row

def _ema(prev: float, new: float, alpha: float) -> float:
    return alpha * new + (1 - alpha) * prev

def self_eval(text: str) -> dict:
    """
    Replace this naive scorer with your real Mythos metrics.
    For now, quick heuristic: length & punctuation give a stable, deterministic score.
    """
    n = len(text.strip())
    periods = text.count(".") + text.count("!") + text.count("?")
    coherence = clamp(0.4 + min(0.5, (periods / max(1, n)) * 25))
    grounding = clamp(0.3 + min(0.5, n / 8000))  # longer text tends to cite more
    illumination = clamp(0.3 + min(0.6, (len(set(text.lower().split())) / max(1, n)) * 12))
    return {"coherence": coherence, "grounding": grounding, "illumination": illumination}

def adapt(scores: Scores) -> dict:
    """
    Update EMA baselines and nudge weights slightly toward areas that lag their baselines.
    """
    with Session(engine) as s:
        w = _get_weights(s)

        # Update EMAs
        w.ema_coherence     = _ema(w.ema_coherence,     scores.coherence,   settings.EMA_ALPHA)
        w.ema_grounding     = _ema(w.ema_grounding,     scores.grounding,   settings.EMA_ALPHA)
        w.ema_illumination  = _ema(w.ema_illumination,  scores.illumination,settings.EMA_ALPHA)

        # Compare scores to baselines and adjust
        delta_c = scores.coherence   - w.ema_coherence
        delta_g = scores.grounding   - w.ema_grounding
        delta_i = scores.illumination- w.ema_illumination

        # small learning rate
        lr = 0.05

        # If coherence is below its baseline, upweight coherence and grounding slightly (stabilize).
        w.w_coherence   = clamp(w.w_coherence   + (-delta_c) * lr, 0.2, 3.0)
        w.w_grounding   = clamp(w.w_grounding   + (-delta_c) * (lr/2), 0.2, 3.0)

        # If grounding is too high vs baseline (over-cautious), give illumination a nudge.
        w.w_illumination= clamp(w.w_illumination+ (delta_g) * lr, 0.2, 3.0)

        # If illumination lags, slightly increase coherence weight to push structure.
        w.w_coherence   = clamp(w.w_coherence   + (-delta_i) * (lr/3), 0.2, 3.0)

        w.updated_at = __import__("datetime").datetime.utcnow()
        s.add(w); s.commit(); s.refresh(w)

        # Return normalized weights for transparency/metrics
        cw, gw, iw = normalize(w.w_coherence, w.w_grounding, w.w_illumination)
        return {
            "weights": {"coherence": cw, "grounding": gw, "illumination": iw},
            "ema": {"coherence": w.ema_coherence, "grounding": w.ema_grounding, "illumination": w.ema_illumination},
            "updated_at": w.updated_at.isoformat()
        }
