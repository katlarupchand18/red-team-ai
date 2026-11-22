import json
import os
import uuid
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "runs"
RUNS_DIR = os.getenv("RUNS_DIR")

if RUNS_DIR:
    DATA_DIR = Path(RUNS_DIR)
else:
    DATA_DIR = DEFAULT_DATA_DIR

# Ensure directory is writable; fallback to /tmp/runs in serverless/read-only environments
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    DATA_DIR = Path("/tmp/runs")
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_error_message(msg: str) -> str:
    """Strip any known API keys or secrets from error messages."""
    for env_key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "VERCEL_TOKEN", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "BLOB_READ_WRITE_TOKEN"):
        val = os.getenv(env_key)
        if val and len(val) > 4:
            msg = msg.replace(val, "[REDACTED]")
    return msg


def _json_default(obj: Any) -> Any:
    """JSON serializer for dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def save_run(run_id: str, payload: dict) -> None:
    """
    Save a run payload to persistent storage.
    Attempts Vercel Blob and Supabase external persistent storage, and saves to local/tmp disk.
    """
    serialized = json.dumps(payload, indent=2, default=_json_default)

    # 1. Attempt Vercel Blob persistent storage if configured
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if blob_token:
        try:
            import httpx
            headers = {
                "authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
                "content-type": "application/json",
            }
            with httpx.Client(timeout=8.0) as client:
                client.put(
                    f"https://blob.vercel-storage.com/runs/{run_id}.json",
                    headers=headers,
                    content=serialized,
                )
        except Exception:
            pass

    # 2. Attempt Supabase external persistent storage if configured
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        try:
            import httpx
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            }
            body = {
                "run_id": run_id,
                "created_at": payload.get("created_at"),
                "provider": payload.get("provider"),
                "data": payload,
            }
            with httpx.Client(timeout=5.0) as client:
                client.post(f"{supabase_url.rstrip('/')}/rest/v1/runs", headers=headers, json=body)
        except Exception:
            pass

    # 3. Save to local filesystem (or /tmp/runs fallback)
    try:
        (DATA_DIR / f"{run_id}.json").write_text(serialized, encoding="utf-8")
    except (PermissionError, OSError):
        tmp_dir = Path("/tmp/runs")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        (tmp_dir / f"{run_id}.json").write_text(serialized, encoding="utf-8")


def load_run(run_id: str) -> dict | None:
    """
    Load a run payload by run_id (UUID string).
    Checks local disk first (for committed historical runs), then Vercel Blob, Supabase, and /tmp/runs.
    """
    try:
        normalized_id = str(uuid.UUID(run_id))
    except (ValueError, TypeError):
        return None

    # 1. Check local DATA_DIR
    target_file = DATA_DIR / f"{normalized_id}.json"
    if target_file.exists():
        try:
            return json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2. Check DEFAULT_DATA_DIR (preserves all committed historical JSON runs)
    if DATA_DIR != DEFAULT_DATA_DIR:
        default_file = DEFAULT_DATA_DIR / f"{normalized_id}.json"
        if default_file.exists():
            try:
                return json.loads(default_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    # 3. Check Vercel Blob persistent storage if configured
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if blob_token:
        try:
            import httpx
            headers = {
                "authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
            }
            with httpx.Client(timeout=8.0) as client:
                r = client.get(
                    f"https://blob.vercel-storage.com?prefix=runs/{normalized_id}",
                    headers=headers,
                )
                if r.status_code == 200:
                    blobs = r.json().get("blobs", [])
                    if blobs and len(blobs) > 0 and "url" in blobs[0]:
                        download_resp = client.get(blobs[0]["url"])
                        if download_resp.status_code == 200:
                            return download_resp.json()
        except Exception:
            pass

    # 4. Check Supabase external storage if configured
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if supabase_url and supabase_key:
        try:
            import httpx
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Accept": "application/json",
            }
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{supabase_url.rstrip('/')}/rest/v1/runs?run_id=eq.{normalized_id}&select=data",
                    headers=headers,
                )
                if resp.status_code == 200:
                    records = resp.json()
                    if records and len(records) > 0 and "data" in records[0]:
                        return records[0]["data"]
        except Exception:
            pass

    # 5. Check /tmp/runs
    tmp_file = Path("/tmp/runs") / f"{normalized_id}.json"
    if tmp_file.exists():
        try:
            return json.loads(tmp_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return None
