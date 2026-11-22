# RED TEAM AI — Prompt Safety Tester (C23)

**Bennett University | School of Computer Science Engineering (SCSE)**  
**Course:** SCSE4041 Mini-Project  
**Team:** RED TEAM AI  
**Project Category:** Artificial Intelligence Security | Cybersecurity

> Authorized prompt safety testing only.

---

## 1. Project Overview

RED TEAM AI — Prompt Safety Tester (C23) is an educational cybersecurity project developed as part of the SCSE4041 Mini-Project at Bennett University.

The project provides a web-based environment for evaluating the prompt safety behavior of Large Language Models (LLMs).

It allows users to test system prompts against predefined adversarial prompt scenarios, compare baseline and improved system prompt configurations, and collect structured evidence from model responses.

The platform integrates supported AI providers through their APIs and uses a conservative heuristic evaluation methodology to classify observed outcomes.

The project focuses on understanding prompt injection, instruction conflicts, model response behavior, and AI application security.

**Important:** This project is a research and educational prototype. It is not a validated automated vulnerability detector.

## 2. Project Objectives

- Explore prompt injection and instruction-conflict vulnerabilities.
- Develop a structured prompt safety testing platform.
- Evaluate LLM responses against predefined attack scenarios.
- Compare baseline and improved system prompts.
- Integrate OpenAI and Google Gemini APIs.
- Implement conservative heuristic response evaluation.
- Store test results and supporting evidence locally.
- Export evaluation evidence in JSON and CSV formats.
- Encourage human-reviewed security assessment.

## 3. System Architecture

### Architecture Overview

The application follows this architecture:

```text
Next.js UI
    |
    v
FastAPI Backend
    |
    v
Attack Library
    |
    v
OpenAI / Gemini API
    |
    v
Conservative Heuristic Evaluation
    |
    v
Baseline / Improved Comparison
    |
    v
JSON / CSV Evidence
```

### Architecture Components

| Component | Description |
|---|---|
| Next.js UI | User interface for configuring and executing tests |
| FastAPI Backend | Backend API and application logic |
| Attack Library | Collection of predefined prompt safety test cases |
| OpenAI/Gemini API | External model provider integration |
| Heuristic Evaluation | Conservative response classification |
| Comparison Engine | Baseline and improved prompt comparison |
| Evidence Storage | Local persistence of test results |
| JSON/CSV Export | Structured evidence for further analysis |

## 4. Technology Stack

### Frontend
- Next.js
- React
- TypeScript
- CSS

### Backend
- Python
- FastAPI
- Uvicorn
- Pydantic
- HTTPX
- Python Dotenv
- Pytest

### AI Providers
- OpenAI API
- Google Gemini API

### Development Tools
- Git
- GitHub
- Node.js
- npm
- Python virtual environment

## 5. System Requirements

| Requirement | Minimum version |
|---|---|
| Python | 3.10+ |
| Node.js | 20+ |
| npm | Compatible with Node.js |
| Git | Installed |
| AI Provider | At least one supported API key |

**Provider requirement:** One provider API key is sufficient to configure an actual model integration. Supported providers are OpenAI and Google Gemini.

## 6. Features

### 6.1 Prompt Safety Testing

Provides a controlled environment for testing model behavior against predefined prompt safety scenarios.

### 6.2 Attack Library

Maintains a collection of test cases designed to evaluate model responses to adversarial and instruction-conflicting prompts.

### 6.3 Baseline System Prompt

Provides the original system prompt configuration used as the reference during testing.

### 6.4 Improved System Prompt

Provides a refined system prompt configuration intended to improve instruction handling and prompt safety behavior.

### 6.5 AI Provider Integration

Supports API-based model integration with:

- OpenAI
- Google Gemini

Actual provider evaluations require valid API credentials and successful API requests.

### 6.6 Conservative Heuristic Evaluation

Evaluates model responses using predefined criteria and assigns one of three verdicts:

- PASS
- FAIL
- NEEDS REVIEW

### 6.7 Baseline / Improved Comparison

Compares the behavior of the baseline and improved system prompts using the same provider and attack set.

### 6.8 Evidence Collection

Stores test results and supporting information locally and supports structured JSON and CSV evidence.

## 7. Installation and Setup

### Prerequisites

Install Python 3.10+, Node.js 20+, npm, and Git.

Clone the repository:

```bash
git clone https://github.com/katlarupchand18/red-team-ai.git
cd red-team-ai
```

### 7.1 Start Backend (Terminal 1)

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on Linux:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment configuration file:

```bash
cp .env.example .env
```

Edit `.env` and configure at least one provider:

```env
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

Replace the placeholder with your actual API key. Only configure credentials for providers you intend to use.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend address:

http://localhost:8000

API documentation:

http://localhost:8000/docs

### 7.2 Start Frontend (Terminal 2)

Open a second terminal.

Navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Frontend address:

http://localhost:3000

### 7.3 Running the Application

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:3000`.
4. Configure the desired provider and system prompts.
5. Execute the available prompt safety tests.
6. Review the resulting verdicts.
7. Compare baseline and improved configurations.
8. Inspect the available evidence.

Actual model execution depends on valid provider credentials and successful API requests.

## 8. Test Execution

The backend uses Pytest for automated testing.

Navigate to the backend:

```bash
cd backend
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run the tests:

```bash
python -m pytest -q
```

### Development Test Result

The backend test suite completed successfully during development:

```text
78 passed, 1 warning in 20.49s
```

The warning concerned a Starlette TestClient deprecation notice involving HTTPX.

This is a recorded development result and does not guarantee identical results across future environments.

## 9. Evaluation Methodology

Run a baseline system prompt and its refined version on the same provider and attack set.

The evaluation engine uses three verdict categories.

| Verdict | Definition |
|---|---|
| PASS | A benign control was answered |
| FAIL | An exact attack success marker was observed |
| NEEDS REVIEW | Ambiguous outcomes, including refusals and API failures |

### PASS

A benign control prompt receives an appropriate answer.

### FAIL

An exact attack success marker is detected according to the defined evaluation criteria.

### NEEDS REVIEW

The response cannot be confidently classified.

Examples include:

- Model refusals.
- API failures.
- Ambiguous responses.
- Incomplete responses.
- Outcomes requiring manual interpretation.

### Evaluation Rules

1. Use the same provider for baseline and improved comparisons.
2. Use the same attack set for both configurations.
3. Preserve the original model responses.
4. Treat ambiguous outcomes separately.
5. Review NEEDS REVIEW results manually.
6. Do not count NEEDS REVIEW as PASS.
7. Do not compute security success rates by treating NEEDS REVIEW as PASS.
8. Record actual API execution results.
9. Do not claim security improvements without sufficient evidence.

**Important evaluation limitation:**

This is a conservative prototype, not a validated automated vulnerability detector.

Human reviewers should label each response against a written rubric before claiming safety improvements.

## 10. Evidence Storage and Data Management

The backend stores system prompts and model responses locally in:

```text
backend/runs/
```

Evidence can be represented in:

- JSON
- CSV

### Evidence Handling

The stored information may include:

- System prompt configurations.
- Model responses.
- Test results.
- Evaluation verdicts.
- Supporting evidence.

Treat these files as potentially sensitive.

Do not submit real secrets or private prompts to the public repository.

Do not commit API credentials, private model responses, or confidential testing data.

## 11. Repository Structure

```text
red-team-ai/
│
├── backend/
│   ├── api/
│   │   └── index.py
│   │
│   ├── app/
│   │   ├── core.py
│   │   ├── main.py
│   │   └── storage.py
│   │
│   ├── tests/
│   │   └── test_core.py
│   │
│   ├── runs/
│   ├── .env.example
│   ├── .gitignore
│   ├── requirements.txt
│   └── vercel.json
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── style.css
│   │
│   ├── AGENTS.md
│   ├── .gitignore
│   ├── next.config.mjs
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── vercel.json
│
├── docs/
│
└── README.md
```

This is the documented project structure. Additional files may exist in the development environment.

## 12. Security Considerations

The project is designed for authorized prompt safety testing only.

Follow these security practices:

- Use only systems you are authorized to test.
- Never hardcode API keys in source code.
- Keep API credentials in environment variables.
- Never commit `.env` files.
- Do not expose private system prompts.
- Avoid submitting sensitive personal or organizational information.
- Restrict access to locally stored test evidence.
- Review stored responses before sharing them.
- Follow provider terms and institutional policies.
- Do not treat heuristic verdicts as definitive security guarantees.

## 13. Limitations

The current evaluation methodology has several limitations:

1. Heuristic evaluation may not correctly interpret every model response.
2. Model refusals and API failures can produce ambiguous results.
3. Model behavior may vary between repeated requests.
4. Results may depend on the provider, model version, and configuration.
5. Passing automated tests does not prove that the application is secure.
6. A limited attack set cannot represent every possible prompt injection scenario.
7. Human-reviewed annotations are necessary for stronger experimental conclusions.
8. The current system is not a certified or validated AI security benchmark.

## 14. Next Enhancements

The following improvements are planned for future development.

### 14.1 Blinded Human Annotation

Introduce blinded human annotation so reviewers can evaluate responses without knowing whether they belong to the baseline or improved configuration.

### 14.2 Test-Case-Specific Expected Behaviors

Define expected behaviors for individual test cases rather than depending exclusively on generic success markers.

### 14.3 Multiple Model Repetitions

Run multiple model repetitions to understand response variability and improve evaluation reliability.

### 14.4 Broader Threat Scenarios

Expand the attack library with broader prompt injection and instruction-conflict scenarios.

### 14.5 LLM-as-Judge with Evidence Validation

Introduce an optional LLM-as-judge evaluation component with evidence validation and human oversight.

### 14.6 PDF Report Generation

Develop a PDF report generation feature containing:

- Evaluation configuration.
- Provider and model information.
- Test case results.
- Baseline and improved comparisons.
- Human-reviewed annotations.
- Limitations and recommendations.

These are proposed enhancements, not claims that the functionality is already implemented.

## 15. Responsible Use

RED TEAM AI is intended for:

- Academic learning.
- Authorized cybersecurity research.
- Controlled prompt safety testing.
- AI application security experimentation.
- Educational evaluation of LLM behavior.

Users must ensure that all testing complies with applicable laws, institutional policies, provider terms, and authorization requirements.

The project must not be represented as a certified AI security assessment platform or a guarantee of model safety.

## 16. Academic Project Information

| Field | Information |
|---|---|
| Project | RED TEAM AI — Prompt Safety Tester (C23) |
| University | Bennett University |
| School | School of Computer Science Engineering |
| Course | SCSE4041 Mini-Project |
| Team | RED TEAM AI |
| Domain | Cybersecurity and AI Security |
| Focus | Prompt Injection and LLM Safety Evaluation |

## 17. Conclusion

RED TEAM AI — Prompt Safety Tester provides an educational platform for exploring prompt injection and evaluating LLM instruction-following behavior.

By combining a Next.js frontend, FastAPI backend, attack library, OpenAI/Gemini API integrations, conservative heuristic evaluation, baseline/improved comparison, and structured evidence collection, the project demonstrates a practical approach to AI security experimentation.

The project emphasizes repeatable testing, transparent evaluation, secure evidence handling, and human-reviewed conclusions.

Automated verdicts alone are not sufficient to establish AI safety. Human review, documented methodology, and clearly stated limitations remain essential.

---

**RED TEAM AI — Test Responsibly. Evaluate Carefully. Build Safer AI.**
