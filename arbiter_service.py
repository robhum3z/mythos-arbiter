from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict
from sqlmodel import Session, select
from sqlalchemy import func
import requests

from config import settings
from db_init import engine, init_db, Interaction, Weights
from model_client import call_model
from scoring.engine import self_eval, adapt


# -------------------------------------------------------------------
# App setup
# -------------------------------------------------------------------
app = FastAPI(title="Mythos Arbiter", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Startup
# -------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()


# -------------------------------------------------------------------
# Optional API-Key Protection
# -------------------------------------------------------------------
def check_key(x_api_key: Optional[str] = Header(default=None)):
    if settings.ARBITER_API_KEY and x_api_key != settings.ARBITER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------
class AskBody(BaseModel):
    prompt: str
    session_id: str = "default"


class ScoreOut(BaseModel):
    coherence: float
    grounding: float
    illumination: float


class AskOut(BaseModel):
    final_text: str
    nest_context: list
    scores: ScoreOut
    arbitrated: bool
    delta_coherence: float
    weights: Dict[str, float]
    ema: Dict[str, float]


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------
def query_nest(prompt: str) -> list:
    """
    Query Mythos Nest for contextual passages.
    """
    try:
        nest_url = settings.NEST_URL.rstrip("/") + "/search"
        payload = {"query": prompt, "limit": 3}
        r = requests.post(nest_url, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json().get("matches", [])
        else:
            print(f"[Nest] Error {r.status_code}: {r.text}")
            return []
    except Exception as e:
        print("[Nest] Connection failed:", e)
        return []


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "arbiter-ok", "nest_linked": bool(settings.NEST_URL)}


@app.get("/metrics")
def metrics():
    with Session(engine) as s:
        total = s.exec(select(func.count()).select_from(Interaction)).one()
    return {"interactions": total}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with Session(engine) as s:
        total = s.exec(select(func.count()).select_from(Interaction)).one()
        w = s.exec(select(Weights)).first()
        if not w:
            w_data = {"coherence": 1.0, "grounding": 1.0, "illumination": 1.0}
            ema_data = {"coherence": 0.0, "grounding": 0.0, "illumination": 0.0}
            recent = []
        else:
            w_data = {
                "coherence": w.w_coherence,
                "grounding": w.w_grounding,
                "illumination": w.w_illumination,
            }
            ema_data = {
                "coherence": w.ema_coherence,
                "grounding": w.ema_grounding,
                "illumination": w.ema_illumination,
            }
            recent = s.exec(select(Interaction).order_by(Interaction.id.desc()).limit(10)).all()

    html = f"""
    <html>
    <head>
        <title>Mythos Arbiter Dashboard</title>
        <style>
            body {{
                font-family: system-ui, sans-serif;
                margin: 40px;
                background: #f9fafb;
                color: #222;
            }}
            h1 {{ color: #0077aa; }}
            .grid {{ display: flex; gap: 2em; margin-bottom: 2em; }}
            .card {{
                background: white; padding: 1.5em; border-radius: 10px;
                box-shadow: 0 3px 8px rgba(0,0,0,0.1);
            }}
            table {{
                width: 100%; border-collapse: collapse;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }}
            th {{ background-color: #0077aa; color: white; }}
        </style>
    </head>
    <body>
        <h1>Mythos Arbiter — Live Metrics</h1>
        <div class="grid">
            <div class="card">
                <h3>Total Interactions</h3>
                <p><b>{total}</b></p>
            </div>
            <div class="card">
                <h3>Weights</h3>
                <p>Coherence: {w_data["coherence"]}<br>
                   Grounding: {w_data["grounding"]}<br>
                   Illumination: {w_data["illumination"]}</p>
            </div>
            <div class="card">
                <h3>EMA</h3>
                <p>Coherence: {ema_data["coherence"]}<br>
                   Grounding: {ema_data["grounding"]}<br>
                   Illumination: {ema_data["illumination"]}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/ask", response_model=AskOut)
def ask(body: AskBody, _: None = Depends(check_key)):
    """
    4-phase reasoning:
      1. Query MythosModel.
      2. Query Nest for cross-reference.
      3. Score & adapt (triadic evaluation).
      4. Return fused response.
    """
    # Phase 1 — Model response
    model_out = call_model(body.prompt, "", body.session_id)
    text = model_out.get("response", "[Model returned no text]")

    # Phase 2 — Cross-reference from Nest
    nest_context = query_nest(body.prompt)

    # Phase 3 — Triadic scoring
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

    # Phase 4 — Adaptive weighting
    adaptive = adapt(scores)

    return AskOut(
        final_text=text,
        nest_context=nest_context,
        scores=scores,
        arbitrated=True,
        delta_coherence=0.0,
        weights=adaptive["weights"],
        ema=adaptive["ema"],
    )
