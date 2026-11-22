import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import csv
import io
import json
import os
import uuid
import httpx
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .core import ATTACKS, APIError, call_model, judge, improved_prompt, advanced_prompt, calculate_metrics
from .storage import save_run, load_run, DATA_DIR as DATA, _json_default, _sanitize_error_message

# Search for .env starting from current directory and parent directories
_env_file = find_dotenv(usecwd=True)
if not _env_file:
    for _parent in [Path(__file__).resolve().parent, Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[2]]:
        if (_parent / ".env").exists():
            _env_file = str(_parent / ".env")
            break
if _env_file:
    load_dotenv(_env_file, override=False)
else:
    load_dotenv(override=False)

app = FastAPI(title="RED TEAM AI - Prompt Safety Tester", version="1.0.0")

# Configure CORS: allow localhost:3000, configurable CORS_ORIGINS, and Vercel preview/production domains
cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]
if "http://localhost:3000" not in allowed_origins:
    allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class TestRequest(BaseModel):
    system_prompt: str = Field(min_length=10, max_length=12000)
    provider: str = Field(pattern="^(openai|gemini)$")
    attack_ids: list[str] = Field(default_factory=list, max_length=20)
    compare_improved: bool = True  # Kept for compatibility with older clients; all three versions are now evaluated.

@app.get("/api/health")
def health():
    providers = []
    if (os.getenv("OPENAI_API_KEY") or "").strip():
        providers.append("openai")
    if (os.getenv("GEMINI_API_KEY") or "").strip():
        providers.append("gemini")
    configured_gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    return {
        "status": "ok",
        "available_providers": providers,
        "gemini_model": configured_gemini_model,
    }

@app.get("/api/attacks")
def attacks():
    return [a.__dict__ for a in ATTACKS]

@app.get("/api/models")
async def list_available_models():
    """List available Gemini models for the current API key (never exposes keys)."""
    raw_key = os.getenv("GEMINI_API_KEY")
    key = (raw_key or "").strip().strip("'\"").strip()
    if not key:
        return {"gemini": []}
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
            if r.status_code == 200:
                names = [
                    m.get("name", "").replace("models/", "")
                    for m in r.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                return {"gemini": names}
            return {"gemini_error": r.status_code}
        except Exception:
            return {"gemini": []}

@app.post("/api/test")
async def test(request: TestRequest):
    chosen = [a for a in ATTACKS if not request.attack_ids or a.id in request.attack_ids]
    if not chosen:
        raise HTTPException(400, "No valid attack IDs")
    variants = {
        "baseline": request.system_prompt,
        "improved": improved_prompt(request.system_prompt),
        "advanced": advanced_prompt(request.system_prompt),
    }

    sem = asyncio.Semaphore(1)

    async def evaluate_single(version: str, prompt: str, attack) -> dict:
        try:
            async with sem:
                response = await call_model(request.provider, prompt, attack.text)
            verdict, reason = judge(attack, response, prompt)
            api_error = None
        except APIError as exc:
            # API failures are stored separately from security verdicts.
            # No verdict is assigned for API failures - they are excluded from security metrics.
            response, verdict, reason = "", None, None
            api_error = exc.to_dict()
        except Exception as exc:
            # Unexpected errors - also stored as API errors (sanitized against secret leakage)
            response, verdict, reason = "", None, None
            sanitized_msg = _sanitize_error_message(f"Unexpected error: {type(exc).__name__}: {str(exc)[:250]}")
            api_error = APIError(
                error_type="UNKNOWN_ERROR",
                message=sanitized_msg,
                provider=request.provider,
            ).to_dict()
        row = {
            "version": version,
            "attack_id": attack.id,
            "category": attack.category,
            "attack": attack.text,
            "response": response,
            "verdict": verdict,
            "reason": reason,
        }
        if api_error is not None:
            row["api_error"] = api_error
        return row

    tasks = [
        evaluate_single(version, prompt, attack)
        for version, prompt in variants.items()
        for attack in chosen
    ]
    rows = list(await asyncio.gather(*tasks))

    # Calculate comparison metrics
    metrics = calculate_metrics(rows)

    run_id = str(uuid4())
    active_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() if request.provider == "gemini" else os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    payload = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": request.provider,
        "model": active_model,
        "prompts": variants,
        "results": rows,
        "metrics": _metrics_to_dict(metrics),
        "limitations": "Heuristic verdicts; NEEDS REVIEW requires human inspection. Prompt-only defenses are not a security guarantee. API errors are excluded from security metrics."
    }
    save_run(run_id, payload)
    return payload


def _metrics_to_dict(metrics) -> dict:
    """Convert ComparisonMetrics dataclass to dict for JSON serialization."""
    return {
        "baseline": _version_metrics_to_dict(metrics.baseline),
        "improved": _version_metrics_to_dict(metrics.improved),
        "advanced": _version_metrics_to_dict(metrics.advanced),
        "asr_difference_pp": metrics.asr_difference_pp,
        "defense_difference_pp": metrics.defense_difference_pp,
        "advanced_asr_difference_pp": metrics.advanced_asr_difference_pp,
        "advanced_defense_difference_pp": metrics.advanced_defense_difference_pp,
        "per_attack": [
            {
                "attack_id": a.attack_id,
                "category": a.category,
                "baseline_verdict": a.baseline_verdict,
                "improved_verdict": a.improved_verdict,
                "baseline_reason": a.baseline_reason,
                "improved_reason": a.improved_reason,
                "baseline_api_error": a.baseline_api_error,
                "improved_api_error": a.improved_api_error,
                "advanced_verdict": a.advanced_verdict,
                "advanced_reason": a.advanced_reason,
                "advanced_api_error": a.advanced_api_error,
            }
            for a in metrics.per_attack
        ],
    }


def _version_metrics_to_dict(m: "VersionMetrics") -> dict:
    """Convert VersionMetrics dataclass to dict."""
    return {
        "total_evaluations": m.total_evaluations,
        "completed_evaluations": m.completed_evaluations,
        "api_error_count": m.api_error_count,
        # Adversarial metrics (known categories only)
        "adversarial_pass_count": m.adversarial_pass_count,
        "adversarial_fail_count": m.adversarial_fail_count,
        "adversarial_needs_review_count": m.adversarial_needs_review_count,
        "asr": m.asr,
        "defense_success_rate": m.defense_success_rate,
        # Benign control metrics
        "benign_total": m.benign_total,
        "benign_pass_count": m.benign_pass_count,
        "benign_fail_count": m.benign_fail_count,
        "benign_needs_review_count": m.benign_needs_review_count,
        "benign_pass_rate": m.benign_pass_rate,
        "false_positive_rate": m.false_positive_rate,
        # Unknown category metrics (tracked but excluded from rates)
        "unknown_total": m.unknown_total,
        "unknown_pass_count": m.unknown_pass_count,
        "unknown_fail_count": m.unknown_fail_count,
        "unknown_needs_review_count": m.unknown_needs_review_count,
        "unknown_categories": m.unknown_categories,
    }


def _json_default(obj):
    """JSON serializer for dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    data = load_run(run_id)
    if not data:
        try:
            uuid.UUID(run_id)
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid run ID")
        raise HTTPException(404, "Run not found")
    return data

@app.get("/api/runs/{run_id}/csv")
def download_csv(run_id: str):
    run = get_run(run_id)
    stream = io.StringIO()
    columns = ["version", "attack_id", "category", "attack", "response", "verdict", "reason", "api_error"]
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in run["results"]:
        # Serialize api_error dict to JSON string for CSV
        csv_row = dict(row)
        if "api_error" in csv_row and csv_row["api_error"] is not None:
            csv_row["api_error"] = json.dumps(csv_row["api_error"])
        else:
            csv_row["api_error"] = ""
        # Only write columns in the defined fieldnames; extrasaction="ignore" handles extra fields
        # Formula injection mitigation: prefix formula-initiating characters with single quote
        writer.writerow({
            key: ("'" + str(value) if str(value).startswith(("=", "+", "-", "@", "\t", "\r")) else value)
            for key, value in csv_row.items()
        })
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=redteam-{run_id}.csv"})
