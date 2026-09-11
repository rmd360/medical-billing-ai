# Medical Billing AI

An AI-assisted medical billing compliance auditor for the COMP7039 dissertation.
The application combines external CPT/ICD lookups, retrieval-augmented policy context,
and compliance agents behind a FastAPI service with an optional Streamlit dashboard.

## Setup

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add an `OPENAI_API_KEY` to `.env` for the full RAG path. The application still starts
without it by using the local fallback vector store. `CPT_API_URL` is optional.

## Run

Start the API from the repository root:

```powershell
uvicorn api.app:app --reload --port 8001
```

In a second terminal, start the dashboard:

```powershell
streamlit run dashboard/dashboard.py
```

The API documentation is available at `http://127.0.0.1:8001/docs`.

## Baseline and evaluation

The deterministic baseline in `baseline/` validates CPT and ICD-10 formats and
reports a conservative compliance decision without network access or an LLM.
The benchmark runner consumes JSONL records with `bill` and `expected_status`
fields:

```powershell
python -m eval.benchmark eval/benchmark_cases.jsonl
```

This provides a reproducible reference point for dissertation experiments; it is
not a substitute for clinical or coding advice.

## Project layout

- `agents/`: billing and compliance agents
- `api/`: FastAPI application
- `baseline/`: deterministic comparison engine
- `dashboard/`: Streamlit interface
- `eval/`: benchmark runner and smoke cases
- `rag/`: embedding, retrieval, and vector-store components
- `services/`: CPT and ICD API clients