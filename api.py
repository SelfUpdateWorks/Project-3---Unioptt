"""
api.py — A small web API around the agent, so n8n (or any tool) can start a run.
Start:  uvicorn api:app --port 8000
Docs:   http://localhost:8000/docs   (try the endpoints in the browser)

Endpoints
  GET  /health       → {"status": "ok"}  (n8n checks the agent is running)
  GET  /programmes   → the programmes in data/programmes.json
  POST /research     → runs the agent (1–3 minutes) and returns a short summary + the report
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.graph import run_agent

PROGRAMMES = json.loads(Path("data/programmes.json").read_text(encoding="utf-8"))
SAMPLE_PROFILE = json.loads(Path("data/sample_profile.json").read_text(encoding="utf-8"))

app = FastAPI(title="Unioptt Programme Research Agent",
              description="Writes a Programme Due Diligence Report with a status and source for every fact.")


class ResearchRequest(BaseModel):
    programme_key: Optional[str] = Field(None, description="A key from /programmes, e.g. 'groningen' or 'tum'")
    programme: Optional[dict] = Field(None, description="Or a full programme: university, name, degree, "
                                                        "country, domain, teaching_language")
    profile: Optional[dict] = Field(None, description="Student profile; the synthetic sample if empty")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/programmes")
def programmes() -> dict:
    return PROGRAMMES


@app.post("/research")
def research(req: ResearchRequest) -> dict:
    if req.programme:
        programme = req.programme
    elif req.programme_key in PROGRAMMES:
        programme = PROGRAMMES[req.programme_key]
    else:
        raise HTTPException(status_code=400,
                            detail=f"Give a programme or one of these keys: {', '.join(PROGRAMMES)}")
    required = ["university", "name", "degree", "country", "domain"]
    missing = [k for k in required if not programme.get(k)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Programme is missing: {', '.join(missing)}")

    try:
        result = run_agent(programme, req.profile or SAMPLE_PROFILE, live=True)
    except Exception as e:   # n8n's error branch receives this message
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    facts, costs, gaps = result["facts"], result["costs"], result["gaps"]
    count = lambda s: sum(1 for f in facts.values() if f["status"] == s)
    return {
        "programme": f"{programme['university']} — {programme['name']}",
        "intake": result["intake"],
        "verified": count("Verified"),
        "needs_review": count("Needs Review"),
        "inferred": count("Inferred"),
        "unknown": count("Unknown"),
        "total_facts": len(facts),
        "main_gaps": [g["area"] for g in gaps if g["status"] == "gap"],
        "total_eur_per_year": costs["total_eur"],
        "total_try_per_year": costs["total_try"],
        "gaps": [f"{g['status'].upper()} · {g['area']}: {g['finding']}" for g in gaps],
        "report_markdown": result["report_md"],
    }
