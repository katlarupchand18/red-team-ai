from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import csv
import io
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .core import ATTACKS, call_model, judge, improved_prompt

load_dotenv()
app = FastAPI(title="RED TEAM AI - Prompt Safety Tester", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
DATA = Path(__file__).resolve().parents[1] / "runs"
DATA.mkdir(exist_ok=True)

class TestRequest(BaseModel):
    system_prompt: str = Field(min_length=10, max_length=12000)
    provider: str = Field(pattern="^(openai|gemini)$")
    attack_ids: list[str] = Field(default_factory=list, max_length=20)
    compare_improved: bool = True

@app.get("/api/health")
def health():
    return {"status": "ok", "available_providers": [p for p, env in [("openai", "OPENAI_API_KEY"), ("gemini", "GEMINI_API_KEY")] if os.getenv(env)]}

@app.get("/api/attacks")
def attacks():
    return [a.__dict__ for a in ATTACKS]

@app.post("/api/test")
async def test(request: TestRequest):
    chosen = [a for a in ATTACKS if not request.attack_ids or a.id in request.attack_ids]
    if not chosen:
        raise HTTPException(400, "No valid attack IDs")
    variants = {"baseline": request.system_prompt}
    if request.compare_improved:
        variants["improved"] = improved_prompt(request.system_prompt)
    rows = []
    for version, prompt in variants.items():
        for attack in chosen:
            try:
                response = await call_model(request.provider, prompt, attack.text)
                verdict, reason = judge(attack, response, prompt)
            except Exception as exc:
                # Provider failures must never count as passed security tests.
                response, verdict, reason = "", "NEEDS REVIEW", f"Provider execution error: {type(exc).__name__}: {str(exc)[:250]}"
            rows.append({"version": version, "attack_id": attack.id, "category": attack.category, "attack": attack.text, "response": response, "verdict": verdict, "reason": reason})
    run_id = str(uuid4())
    payload = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "provider": request.provider, "prompts": variants, "results": rows, "limitations": "Heuristic verdicts; NEEDS REVIEW requires human inspection. Prompt-only defenses are not a security guarantee."}
    (DATA / f"{run_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    try:
        uid = str(uuid4()) if not __import__("uuid").UUID(run_id) else str(__import__("uuid").UUID(run_id))
    except ValueError:
        raise HTTPException(400, "Invalid run ID")
    file = DATA / f"{uid}.json"
    if not file.exists():
        raise HTTPException(404, "Run not found")
    return json.loads(file.read_text(encoding="utf-8"))

@app.get("/api/runs/{run_id}/csv")
def download_csv(run_id: str):
    run = get_run(run_id)
    stream = io.StringIO()
    columns = ["version", "attack_id", "category", "attack", "response", "verdict", "reason"]
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in run["results"]:
        writer.writerow({key: ("'" + str(value) if str(value).startswith(("=", "+", "-", "@")) else value) for key, value in row.items()})
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=redteam-{run_id}.csv"})
