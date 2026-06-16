# CV Customizer - Resume Parsing & Tailoring System

## Project Overview
This is the **Feature 1: Project Structure & Setup** of the CV Customizer system.

A comprehensive multi-agent system for:
1. **Parsing** resumes/portfolios → Master CV format
2. **Job searching** → Extract metadata & filter by ATS score
3. **CV tailoring** → Generate LaTeX CVs, Overleaf sync, ATS optimization

## Architecture

```
FastAPI Backend
├── Parser Agent (LLM: Gemini)
├── Job Search Agent (LLM: Claude)
└── CV Tailor Agent (LLM: ChatGPT)

With LLM Provider Abstraction Layer supporting:
- Claude, Gemini, ChatGPT, Groq, Ollama, Kimi
```

## Setup

### Prerequisites
- Python 3.10+
- pip

### Installation

1. **Clone the repository and switch to feature branch**
   ```bash
   git checkout feature/cv_customiser
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   source venv/bin/activate      # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements_cv.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Run the application**
   ```bash
   python run_cv_customizer.py
   ```

   Or with uvicorn:
   ```bash
   uvicorn cv_customizer.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Project Structure

```
cv_customizer/
├── __init__.py
├── main.py              # FastAPI app initialization
├── config.py            # Configuration management
├── schemas.py           # Pydantic models
├── routers/
│   ├── health.py        # Health check
│   ├── parser.py        # Parser Agent routes
│   ├── job_search.py    # Job Search Agent routes
│   └── cv_tailor.py     # CV Tailor Agent routes
├── agents/
│   ├── llm_provider.py  # LLM abstraction layer
│   ├── parser_agent.py  # Parser Agent implementation (Agent 1)
│   ├── job_search_agent.py  # Job Search Agent (Agent 2)
│   └── cv_tailor_agent.py   # CV Tailor Agent (Agent 3)
├── utils/               # Utility functions (TBD)
├── models/              # Database models (TBD)
└── templates/           # LaTeX templates (TBD)

tests/                   # Test suite (TBD)
```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Parser Agent
- `POST /api/parser/upload` - Upload and parse PDF resume
- `POST /api/parser/parse-portfolio` - Parse portfolio website
- `GET /api/parser/master-cv/{user_id}` - Get Master CV
- `PUT /api/parser/master-cv/{user_id}` - Update Master CV

### Job Search Agent
- `POST /api/jobs/search` - Search and extract job metadata
- `POST /api/jobs/filter-by-ats` - Filter jobs by ATS score
- `GET /api/jobs/job/{job_id}` - Get job details

### CV Tailor Agent
- `POST /api/tailor/generate` - Generate tailored CV
- `POST /api/tailor/check-ats-score` - Check ATS score
- `POST /api/tailor/overleaf-sync` - Sync to Overleaf
- `GET /api/tailor/download/{cv_id}` - Download CV

## Configuration

### LLM Provider Selection
Set in `.env`:
```
PARSER_LLM_PROVIDER=gemini      # Agent 1: Data extraction
JOB_SEARCH_LLM_PROVIDER=claude  # Agent 2: Job analysis
CV_TAILOR_LLM_PROVIDER=chatgpt  # Agent 3: CV wording
```

Supported providers: `claude`, `gemini`, `chatgpt`, `groq`, `ollama`, `kimi`

## Next Steps

**Feature 2: Master CV JSON Schema** - Define complete CV data structure
**Feature 3: LLM Provider Abstraction** - Full LangChain integration
**Feature 4: Parser Agent** - PDF parsing + portfolio scraping

---

Created: 2026-06-16
Status: ✅ Project Structure Complete
