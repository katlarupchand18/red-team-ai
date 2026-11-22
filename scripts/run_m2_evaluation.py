"""Run the fixed Milestone 2 case set against all saved prompt versions."""
import asyncio
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=False)

from app.core import APIError, Attack, call_model, judge  # noqa: E402


def metrics(rows):
    output = {}
    for key, code in (("V1_Baseline", "V1"), ("V2_Improved", "V2"), ("V3_Advanced", "V3")):
        items = [r for r in rows if r["version_code"] == code]
        errors = [r for r in items if r["api_error"]]
        completed = [r for r in items if not r["api_error"]]
        adversarial = [r for r in completed if r["category"] != "benign_control"]
        benign = [r for r in completed if r["category"] == "benign_control"]
        passed = sum(r["verdict"] == "PASS" for r in adversarial)
        failed = sum(r["verdict"] == "FAIL" for r in adversarial)
        review = sum(r["verdict"] == "NEEDS REVIEW" for r in adversarial)
        benign_pass = sum(r["verdict"] == "PASS" for r in benign)
        benign_fail = sum(r["verdict"] == "FAIL" for r in benign)
        decisive = passed + failed
        output[key] = {
            "total_evaluations": len(items), "completed_evaluations": len(completed),
            "api_error_count": len(errors), "pass_count": sum(r["verdict"] == "PASS" for r in completed),
            "fail_count": sum(r["verdict"] == "FAIL" for r in completed),
            "needs_review_count": sum(r["verdict"] == "NEEDS REVIEW" for r in completed),
            "adversarial_pass": passed, "adversarial_fail": failed,
            "adversarial_needs_review": review,
            "asr_percent": round(failed * 100 / decisive, 2) if decisive else None,
            "defence_success_rate_percent": round(passed * 100 / decisive, 2) if decisive else None,
            "benign_total": len(benign), "benign_pass": benign_pass,
            "benign_fail": benign_fail,
            "benign_needs_review": sum(r["verdict"] == "NEEDS REVIEW" for r in benign),
            "benign_pass_rate_percent": round(benign_pass * 100 / len(benign), 2) if benign else None,
            "false_positive_rate_percent": round(benign_fail * 100 / len(benign), 2) if benign else None,
        }
    return output


async def main():
    prompts = json.loads((ROOT / "data/prompt_versions.json").read_text())
    cases = json.loads((ROOT / "data/m2_test_cases.json").read_text())
    rows = []
    errors = []
    for version_key, prompt in prompts.items():
        for case in cases:
            attack = Attack(case["attack_id"], case["category"], case["input"], case["expectation"])
            started = time.monotonic()
            timestamp = datetime.now(timezone.utc).isoformat()
            row = {
                "test_case_id": case["test_case_id"], "version_code": prompt["version"],
                "version_name": prompt["name"], "version_key": version_key,
                "attack_id": case["attack_id"], "category": case["category"],
                "input": case["input"], "expectation": case["expectation"],
                "response": "", "verdict": None, "reason": None,
                "api_error": None, "latency_seconds": None, "timestamp": timestamp,
                "provider": "gemini", "model": __import__("os").getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip(),
            }
            try:
                row["response"] = await call_model("gemini", prompt["prompt"], case["input"])
                row["verdict"], row["reason"] = judge(attack, row["response"], prompt["prompt"])
            except APIError as exc:
                row["api_error"] = exc.to_dict()
                errors.append({"test_case_id": case["test_case_id"], "version_code": prompt["version"], **exc.to_dict()})
            except Exception as exc:
                row["api_error"] = {"error_type": "UNKNOWN_ERROR", "message": type(exc).__name__, "provider": "gemini"}
                errors.append({"test_case_id": case["test_case_id"], "version_code": prompt["version"], **row["api_error"]})
            row["latency_seconds"] = round(time.monotonic() - started, 3)
            rows.append(row)
            print(f"{row['version_code']} {row['test_case_id']} {row['verdict'] or 'API_ERROR'}", flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "run_id": f"m2-eval-{stamp}", "executed_at": datetime.now(timezone.utc).isoformat(),
        "provider": "gemini", "model": rows[0]["model"] if rows else None,
        "total_evaluations": len(rows), "api_errors_total": len(errors), "api_errors": errors,
        "prompt_version_source": "data/prompt_versions.json", "test_case_source": "data/m2_test_cases.json",
        "prompts": prompts, "metrics": metrics(rows), "results": rows,
        "limitations": "Heuristic verdicts. NEEDS REVIEW is not counted as a successful defence; human review is required. Prompt-only controls do not guarantee security.",
    }
    json_path = ROOT / "data" / f"m2_evaluation_{stamp}.json"
    csv_path = ROOT / "data" / f"m2_evaluation_{stamp}.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    fields = list(rows[0]) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "api_error": json.dumps(row["api_error"], ensure_ascii=False) if row["api_error"] else ""})
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "count": len(rows), "errors": len(errors), "metrics": payload["metrics"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
