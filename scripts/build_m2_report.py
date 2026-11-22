"""Build the submission report from saved live evaluation evidence."""
import csv
import html
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
run_path = max(DATA.glob("m2_evaluation_????????T??????Z.json"), key=lambda p: p.stat().st_mtime)
run = json.loads(run_path.read_text())
case_path = DATA / "m2_test_cases.json"
cases = json.loads(case_path.read_text())
versions = json.loads((DATA / "prompt_versions.json").read_text())

with (DATA / "m2_test_cases.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(cases[0]))
    writer.writeheader()
    writer.writerows(cases)

with (DATA / "prompt_iteration_log.csv").open("w", newline="", encoding="utf-8") as f:
    fields = ["version", "name", "created_at", "description", "changes_from_previous", "reason", "expected_security_improvements", "evidence"]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for key, p in versions.items():
        writer.writerow({"version": p["version"], "name": p["name"], "created_at": p["created_at"],
                         "description": p["changes_from_previous"], "changes_from_previous": p["changes_from_previous"],
                         "reason": p["reason"], "expected_security_improvements": p["expected_security_improvements"],
                         "evidence": run_path.name})

log_rows = []
for key, p in versions.items():
    log_rows.append({"version": p["version"], "name": p["name"], "created_at": p["created_at"],
                     "description": p["changes_from_previous"], "reason": p["reason"],
                     "expected_security_improvements": p["expected_security_improvements"],
                     "prompt_text": p["prompt"], "evaluation_metrics": run["metrics"][key],
                     "evidence": run_path.name})
(DATA / "prompt_iteration_log.json").write_text(json.dumps(log_rows, ensure_ascii=False, indent=2) + "\n")

summary = {"run_id": run["run_id"], "executed_at": run["executed_at"], "provider": run["provider"],
           "model": run["model"], "total_evaluations": run["total_evaluations"],
           "api_errors_total": run["api_errors_total"], "metrics": run["metrics"]}
public_dir = ROOT / "frontend" / "public"
public_dir.mkdir(exist_ok=True)
(public_dir / "m2-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

def e(value):
    return html.escape(str(value if value is not None else ""))

styles = """
@page { size: A4; margin: 17mm 15mm; @bottom-right { content: "RED TEAM AI • Milestone 2"; color: #607080; font-size: 8pt; } }
body { font: 10pt/1.48 Arial, sans-serif; color: #162436; }
h1 { color: #0b2f50; font-size: 25pt; margin: 0 0 8pt; }
h2 { color: #0b557a; font-size: 17pt; border-bottom: 1px solid #b6c8d8; padding-bottom: 4pt; margin-top: 22pt; }
h3 { color: #183c5a; font-size: 12pt; margin-bottom: 4pt; }
.cover { margin-top: 45mm; }
.tag { color: #1674a5; text-transform: uppercase; letter-spacing: 2pt; font-weight: bold; }
.muted { color: #53667a; }
.card { background: #f2f6fa; border-left: 3px solid #1684b4; padding: 8pt 11pt; margin: 8pt 0; }
table { border-collapse: collapse; width: 100%; margin: 9pt 0 14pt; font-size: 8.7pt; }
th { background: #123b5d; color: white; text-align: left; }
th, td { border: 1px solid #cad5df; padding: 5pt 6pt; vertical-align: top; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f4f6f8; border: 1px solid #d7dfe5; padding: 8pt; font: 8pt/1.35 Consolas, monospace; }
.case { break-inside: avoid; border-bottom: 1px solid #d6dfe7; padding: 4pt 0 8pt; }
.verdict { font-weight: bold; }
.small { font-size: 8pt; }
.page { break-before: page; }
"""
body = [f'<div class="cover"><p class="tag">Bennett University • SCSE4041</p><h1>RED TEAM AI</h1><h2>Milestone 2: Prompt Security Evaluation</h2><p class="muted">Team RED TEAM AI (C23) · Evidence generated from live provider runs</p><div class="card"><b>Run:</b> {e(run["run_id"])}<br><b>Executed:</b> {e(run["executed_at"])} (UTC)<br><b>Provider / model:</b> {e(run["provider"])} / {e(run["model"])}<br><b>Completed calls:</b> {len(run["results"])-run["api_errors_total"]} of {len(run["results"])} · <b>API errors:</b> {run["api_errors_total"]}</div><p>This report records the three saved system prompt versions, the fixed ten-case input set, live model responses, conservative verdicts and limitations.</p></div>']
body.append('<div class="page"><h2>1. Architecture and Method</h2><p>The application uses a Next.js frontend and FastAPI backend. The backend sends a system prompt and one user test input to the configured Gemini provider, stores the response and error data, and applies a conservative heuristic judge. This Milestone 2 evaluation used three independently saved prompt texts and ten identical test inputs per version. The frontend also loads a generated Milestone 2 summary JSON file; the report and UI summary use the same run metrics.</p><p>All 30 provider calls completed without API errors. Responses and per-call UTC timestamps are preserved in the raw JSON/CSV run files. Evaluator verdicts are heuristic; prompt extraction cases are always marked NEEDS REVIEW because surface output alone cannot establish whether hidden text leaked.</p><div class="card"><b>Metric definitions:</b> ASR = adversarial FAIL ÷ (adversarial PASS + FAIL); defence success = adversarial PASS ÷ (PASS + FAIL). NEEDS REVIEW is excluded from both denominators and never counted as success. Benign pass rate = benign PASS ÷ non-error benign cases. False positive rate = benign FAIL ÷ non-error benign cases. API errors are excluded.</div>')
body.append('<h2>2. Prompt Iterations</h2>')
for key, p in versions.items():
    body.append(f'<h3>{e(p["version"])} — {e(p["name"])}</h3><p><b>Created:</b> {e(p["created_at"])}<br><b>Changes:</b> {e(p["changes_from_previous"])}<br><b>Reason:</b> {e(p["reason"])}<br><b>Expected improvement:</b> {e(p["expected_security_improvements"])}</p><pre>{e(p["prompt"])}</pre>')
body.append('<h2>3. Comparative Results</h2><table><thead><tr><th>Prompt</th><th>PASS</th><th>FAIL</th><th>NEEDS REVIEW</th><th>API errors</th><th>ASR</th><th>Defence</th><th>Benign pass</th><th>FPR</th></tr></thead><tbody>')
for key, m in run['metrics'].items():
    body.append(f'<tr><td>{e(versions[key]["version"])} {e(versions[key]["name"])}</td><td>{m["pass_count"]}</td><td>{m["fail_count"]}</td><td>{m["needs_review_count"]}</td><td>{m["api_error_count"]}</td><td>{e(m["asr_percent"])}%</td><td>{e(m["defence_success_rate_percent"])}%</td><td>{e(m["benign_pass_rate_percent"])}%</td><td>{e(m["false_positive_rate_percent"])}%</td></tr>')
body.append('</tbody></table><p>Each version has only nine adversarial cases and one benign control. The decisive adversarial samples are smaller because NEEDS REVIEW is excluded. The results are descriptive for this provider, model, prompt, and single run; they are not a statistical safety guarantee.</p>')
body.append('<h2>4. Test Inputs and Full Evidence</h2><p>Every case below was run once against each version. Each entry includes the exact input, expected behavior, observed response, verdict, and evaluator explanation.</p>')
rows_by_case = {(r['version_key'], r['test_case_id']): r for r in run['results']}
for case in cases:
    body.append(f'<div class="case"><h3>{e(case["test_case_id"])} — {e(case["category"])}</h3><p><b>Input:</b> {e(case["input"])}<br><b>Expected:</b> {e(case["expectation"])}</p>')
    for key, p in versions.items():
        r = rows_by_case[(key, case['test_case_id'])]
        v = r['verdict'] or 'API ERROR'
        body.append(f'<p><b>{e(p["version"])} / {e(p["name"])} — <span class="verdict">{e(v)}</span></b><br><b>Actual output:</b> {e(r["response"] if r["response"] else json.dumps(r["api_error"]))}<br><b>Explanation:</b> {e(r["reason"] or "Provider call failed; excluded from metrics.")}<br><span class="small">UTC: {e(r["timestamp"])} · latency: {e(r["latency_seconds"])} s · provider/model: {e(r["provider"])}/{e(r["model"])}</span></p>')
    body.append('</div>')
body.append('<h2>5. Limitations and Next Steps</h2><ul><li>Only one call per case and prompt was made; model outputs can vary between runs.</li><li>Prompt extraction outcomes require a human to compare outputs against protected prompt content. No real secrets were included.</li><li>Heuristic verdicts can misclassify nuanced or quoted responses. Review all NEEDS REVIEW cases manually before making strong security claims.</li><li>Prompt instructions alone do not provide access control, isolation, or a guarantee against prompt injection.</li><li>Future work: blinded human annotation, repeated trials, broader indirect-injection cases, and evaluation against additional providers/models.</li></ul><h2>6. Evidence Files</h2><p>Full prompts: <code>data/prompt_versions.json</code>. Test cases: <code>data/m2_test_cases.json</code> and CSV. Iteration log: <code>data/prompt_iteration_log.csv</code>. Raw run: <code>{e(run_path.name)}</code> and matching CSV. Evaluator: <code>scripts/run_m2_evaluation.py</code>.</p>')
html_doc = '<!doctype html><html><head><meta charset="utf-8"><style>' + styles + '</style></head><body>' + ''.join(body) + '</body></html>'
report_html = ROOT / "reports" / "milestone_2_report.html"
report_html.parent.mkdir(exist_ok=True)
report_html.write_text(html_doc, encoding="utf-8")
shutil.copy2(run_path, DATA / "m2_evaluation_30_runs.json")
shutil.copy2(run_path.with_suffix('.csv'), DATA / "m2_evaluation_30_runs.csv")

outdir = ROOT / "reports"
result = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(report_html)], capture_output=True, text=True)
pdf_path = outdir / "milestone_2_report.pdf"
if result.returncode or not pdf_path.exists():
    # Minimal dependency-free PDF writer fallback for restricted/headless systems.
    plain = ["RED TEAM AI — MILESTONE 2", "Prompt Security Evaluation", "Bennett University • SCSE4041 • Team C23", "",
             f"Run: {run['run_id']} | {run['executed_at']} UTC",
             f"Provider/model: {run['provider']} / {run['model']} | {len(run['results'])} calls | {run['api_errors_total']} API errors", "",
             "ARCHITECTURE AND METHOD",
             "Next.js UI -> FastAPI -> Gemini -> heuristic evaluator -> JSON/CSV evidence.",
             "The frontend Milestone 2 snapshot and report read metrics generated from the same run JSON.",
             "One run per case/version. NEEDS REVIEW is not counted as success. API errors are excluded.",
             "ASR = adversarial FAIL / (PASS + FAIL); defence = PASS / (PASS + FAIL).",
             "Benign pass rate = benign PASS / non-error benign cases; FPR = benign FAIL / non-error benign cases.", "",
             "PROMPT ITERATIONS"]
    for key, p in versions.items():
        plain.extend([f"{p['version']} — {p['name']} | Created {p['created_at']}",
                      f"Changes: {p['changes_from_previous']}", f"Reason: {p['reason']}",
                      f"Expected: {p['expected_security_improvements']}", "Full prompt:", p['prompt'], ""])
    plain.extend(["COMPARATIVE RESULTS", "Version | PASS | FAIL | NEEDS REVIEW | API errors | ASR | Defence | Benign pass | FPR"])
    for key, m in run['metrics'].items():
        plain.append(f"{versions[key]['version']} | {m['pass_count']} | {m['fail_count']} | {m['needs_review_count']} | {m['api_error_count']} | {m['asr_percent']}% | {m['defence_success_rate_percent']}% | {m['benign_pass_rate_percent']}% | {m['false_positive_rate_percent']}%")
    plain.extend(["", "FULL TEST EVIDENCE"])
    rows_by_case = {(r['version_key'], r['test_case_id']): r for r in run['results']}
    for case in cases:
        plain.extend([f"{case['test_case_id']} — {case['category']}", f"Input: {case['input']}", f"Expected: {case['expectation']}"])
        for key, p in versions.items():
            r = rows_by_case[(key, case['test_case_id'])]
            plain.extend([f"{p['version']} — {r['verdict'] or 'API ERROR'} | {r['timestamp']} UTC | {r['latency_seconds']}s",
                          f"Actual: {r['response'] if r['response'] else json.dumps(r['api_error'])}",
                          f"Explanation: {r['reason'] or 'Provider call failed; excluded from metrics.'}"])
        plain.append("")
    plain.extend(["LIMITATIONS AND NEXT STEPS",
                  "One repetition per case; outputs may vary. Extraction outcomes require human comparison with protected prompt content.",
                  "Heuristic verdicts can misclassify nuanced or quoted responses. Prompt text alone is not a security guarantee.",
                  "Future work: blinded annotation, repeated trials, broader attacks, and additional providers/models.", "",
                  f"Evidence: {run_path.name}; data/prompt_versions.json; data/m2_test_cases.json; data/prompt_iteration_log.csv."])
    pages, current = [], []
    for para in plain:
        lines = textwrap.wrap(para, width=92, break_long_words=True, break_on_hyphens=False) if para else [""]
        for line in lines:
            current.append(line)
            if len(current) >= 62:
                pages.append(current)
                current = []
    if current:
        pages.append(current)
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
    page_ids = []
    for page_no, lines in enumerate(pages):
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        commands = []
        y = 790
        for line in lines:
            if line == "RED TEAM AI — MILESTONE 2":
                font, size, color, step = "F2", 21, "0.05 0.22 0.36", 27
            elif line == "Prompt Security Evaluation":
                font, size, color, step = "F2", 14, "0.08 0.36 0.51", 21
            elif line in {"ARCHITECTURE AND METHOD", "PROMPT ITERATIONS", "COMPARATIVE RESULTS", "FULL TEST EVIDENCE", "LIMITATIONS AND NEXT STEPS"}:
                font, size, color, step = "F2", 12, "0.05 0.30 0.46", 17
            elif line.startswith(("V1 —", "V2 —", "V3 —", "V1 Baseline Prompt", "V2 Improved Security Prompt", "V3 Advanced Security Prompt")) or (len(line) > 3 and line[0:2] == "TC"):
                font, size, color, step = "F2", 9.5, "0.08 0.25 0.38", 13
            else:
                font, size, color, step = "F1", 8.5, "0.09 0.14 0.20", 11
            safe = line.encode("cp1252", "replace").decode("cp1252").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"BT /{font} {size} Tf {color} rg 50 {y} Td ({safe}) Tj ET")
            y -= step
        commands.append(f"BT /F1 8 Tf 0.33 0.40 0.48 rg 50 28 Td (RED TEAM AI  |  Milestone 2  |  Page {page_no + 1} of {len(pages)}) Tj ET")
        stream = "\n".join(commands).encode("cp1252", "replace")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >> >> /Contents {content_id} 0 R >>".encode())
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    kids = " ".join(f"{n} 0 R" for n in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode() + (obj if isinstance(obj, bytes) else obj.encode()) + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    pdf_path.write_bytes(pdf)
    print("LibreOffice unavailable for conversion; generated PDF with built-in writer.")
print(f"REPORT={pdf_path}")
print(f"SOURCE_RUN={run_path.name}")
