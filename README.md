# RED TEAM AI — Prompt Safety Tester (C23)

Bennett University SCSE4041 Mini-Project. Team: RED TEAM AI. Authorized prompt safety testing only.

## Architecture

Next.js UI -> FastAPI -> Attack Library -> OpenAI/Gemini API -> Conservative Heuristic Evaluation -> Baseline/Improved Comparison -> JSON/CSV evidence.

## Requirements

Python 3.10+ and Node.js 20+. One provider API key. The backend stores system prompts and model responses locally in `backend/runs/`; do not submit real secrets or private prompts.

## Start backend (terminal 1)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY or OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the API documentation.

## Start frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Test

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

## Evaluation method

Run a baseline system prompt and its refined version on the same provider and attack set. PASS means a benign control was answered; FAIL requires an exact attack success marker; NEEDS REVIEW indicates ambiguous outcomes, including refusals and API failures. This is a conservative prototype, **not** a validated automated vulnerability detector. Do not compute security success rates by treating NEEDS REVIEW as PASS. Human reviewers should label each response against a written rubric before claiming safety improvements.

## Next enhancements

Add blinded human annotation, test-case-specific expected behaviors, multiple model repetitions, broader threat scenarios, an LLM-as-judge with evidence validation, and a PDF report. Never claim model integrations or evaluations were run until confirmed with actual keys and results.
