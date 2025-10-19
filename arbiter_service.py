import traceback
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
from sqlmodel import Session, select
from sqlalchemy import func

from config import settings
from db_init import engine, init_db, Interaction, Weights
from model_client import call_model
from scoring.engine import self_eval, adapt

app = FastAPI(title="Mythos Arbiter", version="0.3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    print("⚙️  Initializing Mythos Arbiter...")
    init_db()

def check_key(x_api_key: Optional[str] = Header(default=None)):
    if settings.ARBITER_API_KEY and x_api_key != settings.ARBITER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

class AskBody(BaseModel):
    prompt: str
    session_id: str = "default"

class ScoreOut(BaseModel):
    coherence: float
    grounding: float
    illumination: float

class AskOut(BaseModel):
    final_text: str
    scores: ScoreOut
    arbitrated: bool
    delta_coherence: float
    weights: Dict[str, float]
    ema: Dict[str, float]

@app.get("/health")
def health():
    return {"status": "arbiter-ok"}

@app.get("/metrics")
def metrics():
    with Session(engine) as s:
        total = s.exec(select(func.count()).select_from(Interaction)).one()
    return {"interactions": total}

@app.post("/ask")
def ask(body: AskBody, _: None = Depends(check_key)):
    try:
        print(f"🧭 Received prompt: {body.prompt[:60]}...")
        model_out = call_model(body.prompt, "", body.session_id)
        text = model_out.get("response", "")

        print("🧠 Running self-eval...")
        sc = self_eval(text)
        scores = ScoreOut(**sc)

        with Session(engine) as s:
            s.add(
                Interaction(
                    prompt=body.prompt,
                    response=text,
                    coherence=scores.coherence,
                    grounding=scores.grounding,
                    illumination=scores.illumination,
                )
            )
            s.commit()

        adaptive = adapt(scores)
        print("✅ Arbitration complete.")
        return AskOut(
            final_text=text,
            scores=scores,
            arbitrated=True,
            delta_coherence=0.0,
            weights=adaptive["weights"],
            ema=adaptive["ema"],
        )

    except Exception as e:
        tb = traceback.format_exc()
        print(f"🔥 Internal error: {e}\n{tb}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": tb.splitlines()[-5:],
                "message": "Internal error during arbitration — see logs.",
            },
        )
