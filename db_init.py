from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select
from config import settings
import os

# --- Build database URL dynamically ---
# Prefer DB_URL (for cloud), else fall back to local DB_PATH
db_url = getattr(settings, "DB_URL", None)
if not db_url:
    db_path = getattr(settings, "DB_PATH", "arbiter.db")
    db_url = f"sqlite:///{os.path.abspath(db_path)}"

# Create SQLModel engine
engine = create_engine(db_url, echo=False)


# --- Define Tables ---
class Interaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prompt: str
    response: str
    coherence: float
    grounding: float
    illumination: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Weights(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # current adaptive weights used by the scorer
    w_coherence: float = 1.0
    w_grounding: float = 1.0
    w_illumination: float = 1.0
    # EMA baselines (the “memory” Mythos adapts to)
    ema_coherence: float = 0.0
    ema_grounding: float = 0.0
    ema_illumination: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Initialize the database ---
def init_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        exists = s.exec(select(Weights)).first()
        if not exists:
            s.add(Weights())
            s.commit()
    print(f"✅ Arbiter database ready at: {db_url}")


if __name__ == "__main__":
    init_db()
