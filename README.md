# Legal AI Analyzer

Legal AI Analyzer is a full-stack application for uploading legal documents, extracting text, and generating AI-assisted analysis (clauses, risks, sections, summaries, and Q&A).

## Tech Stack

- Frontend: React + Vite + React Router + Tailwind CSS
- Backend API: FastAPI
- Storage/DB/Auth: Supabase
- Document processing: PyMuPDF, python-docx
- AI pipeline: Sentence Transformers, Transformers, spaCy, NLTK, Sumy, Pinecone, Gemini
- Background processing: SQLite-backed local job queue + Python worker

## Project Structure

```text
legal-ai-analyzer/
  frontend/                 # React app (Vite)
  backend/                  # FastAPI app + services + worker
    app/
      routes/               # API routes
      services/             # text extraction, storage, queue, AI pipeline, data access
      models/               # Pydantic request/response models
  supabase/migrations/      # SQL migrations
```

## Features

- Upload legal documents (`pdf`, `docx`)
- Text extraction for PDF and DOCX
- Asynchronous document processing queue
- Document-level analysis endpoints:
  - Full analysis
  - Clauses
  - Risks
  - Sections
  - Summarization
  - Ask-a-question over document content
- Dashboard risk summary
- Basic profile/settings endpoints
- Frontend Supabase-auth integration

## Prerequisites

- Node.js 18+
- Python 3.10+
- Supabase project (URL, anon key, service role key, storage bucket)
- (Optional but recommended) spaCy model: `en_core_web_sm`
- (Optional) Pinecone account for vector index
- (Optional) Gemini API key for advanced summarization

## Environment Setup

### 1) Backend env (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and fill values:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=
FRONTEND_ORIGIN=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=legal-doc-embeddings
PINECONE_HOST=
PINECONE_EXPECTED_DIMENSION=384
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemini-2.5-pro
GEMINI_MAP_MODEL_NAME=gemini-2.5-flash
GEMINI_REDUCE_MODEL_NAME=gemini-2.5-pro
```

Notes:
- Use **service role key only on backend**, never in frontend.

### 2) Frontend env (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
# Optional in production:
# VITE_API_URL=https://your-api.example.com
```

In local development, keep `VITE_API_URL` empty to use Vite proxy to `http://127.0.0.1:8000`.

## Install Dependencies

### Frontend

```bash
cd frontend
npm install
```

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run Locally

Use 3 terminals.

### Terminal 1: Backend API

```bash
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Worker

```bash
cd backend
.venv\Scripts\Activate.ps1
python -m app.worker
```

### Terminal 3: Frontend

```bash
cd frontend
npm run dev
```

Frontend typically runs at `http://localhost:5173`.

## API Overview

### Health
- `GET /health`

### Upload
- `POST /upload`

### Documents
- `GET /documents`
- `GET /documents/{document_id}`
- `DELETE /documents/{document_id}`
- `GET /documents/{document_id}/text`
- `GET /documents/{document_id}/analysis`
- `GET /documents/{document_id}/clauses`
- `GET /documents/{document_id}/risks`
- `GET /documents/{document_id}/sections`
- `POST /documents/{document_id}/summarize`
- `POST /documents/{document_id}/ask`

### Dashboard / Admin
- `GET /dashboard/risk-summary`
- `GET /admin/queue-status`

### Settings
- `GET /settings/profile`
- `PUT /settings/profile`
- `POST /settings/delete-all-documents`
- `POST /settings/delete-account`

## Processing Flow

1. Frontend uploads file to `POST /upload`.
2. Backend stores file in Supabase storage and inserts document metadata.
3. A queue job (`process_document`) is inserted into local SQLite queue (`backend/tmp/job_queue.sqlite3`).
4. Worker claims the job and:
   - downloads file content,
   - runs text extraction (PDF/DOCX),
   - stores extracted text,
   - triggers AI analysis pipeline.
5. Document status progresses through states like `uploaded -> processing -> extracted -> analyzed` (or `failed`).

## Database / Supabase

- SQL migrations are under `supabase/migrations/`.
- Ensure your Supabase storage bucket matches `SUPABASE_STORAGE_BUCKET`.
- Frontend uses anon key; backend uses service role key.

## Security Notes (Important)

- Do not commit `.env` files or secret keys.
- Keep service role key restricted to backend runtime only.
- Prefer private bucket + signed URLs for sensitive legal documents.
- Enforce strict auth + ownership checks on all document-related endpoints before production deployment.

## Troubleshooting

- **Auth not working in frontend:** verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- **Uploads succeed but analysis does not start:** ensure worker process is running.
- **CORS errors:** set `FRONTEND_ORIGIN` in backend env to your frontend origin.
- **Queue seems stuck:** check `GET /admin/queue-status`.

## Build

Frontend production build:

```bash
cd frontend
npm run build
npm run preview
```

## Current Gaps / Recommendations

- Add automated tests (backend route tests, frontend smoke tests).
- Add CI workflow for lint + tests.
- Harden auth boundaries and document access patterns for production.
- Add structured logging and redaction for sensitive legal text.

---

If you want, I can also generate:
- a `README-dev.md` focused only on local development/debugging, and
- a deployment runbook for Render/Railway/AWS with environment templates.
