# Docs — a small collaborative document editor

A minimal Google-Docs-style app: create and edit rich-text documents in the
browser, upload a `.txt`/`.md` file to turn it into a document, and share a
document with another user.

- **Backend:** Python, FastAPI, SQLAlchemy
- **Frontend:** Next.js (App Router) + TypeScript, [Tiptap](https://tiptap.dev) for rich text
- **Database:** CockroachDB Cloud (Postgres wire-compatible), used both locally and in production
- **Auth:** seeded demo users (Alice / Bob / Carol), pick-a-user login, no passwords

## Repositories

This project is split across two repos:

- Frontend: https://github.com/Anupamti/Ajaia-Assignment-frontend
- Backend: https://github.com/Anupamti/Ajaia-Assignment-backend

Both repos carry an identical copy of this documentation set. To run the
project locally (including `docker compose`, which expects this exact
layout), clone both into a common parent directory using these folder names:

```bash
git clone https://github.com/Anupamti/Ajaia-Assignment-backend.git backend
git clone https://github.com/Anupamti/Ajaia-Assignment-frontend.git frontend
```

Everything below assumes you're standing in that parent directory, with
`backend/` and `frontend/` as siblings.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) (design rationale),
[AI_WORKFLOW.md](AI_WORKFLOW.md) (how this was built), and
[SUBMISSION.md](SUBMISSION.md) (requirements checklist + current status).

## Live deployment

- Frontend: _TODO — Vercel URL_
- Backend API: _TODO — Render URL_

## Supported file types

File upload only accepts **`.txt` and `.md`** files (max 1MB). Any other
extension is rejected with a clear error message, both in the UI and the API
(`400 Bad Request`). Markdown is converted to formatted HTML; plain text is
wrapped into paragraphs.

## Running locally

You need a CockroachDB Cloud connection string — see `backend/.env.example`
for the format (note the `cockroachdb://` scheme, not `postgresql://` — see
[ARCHITECTURE.md](ARCHITECTURE.md) for why). The CA cert needed for
`sslmode=verify-full` is already committed at `backend/certs/root.crt`.

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env   # fill in DATABASE_URL
export DATABASE_URL=$(grep DATABASE_URL backend/.env | cut -d= -f2-)
export JWT_SECRET=some-long-random-string
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Option B — run each side manually

Backend (requires Python 3.10+):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

Frontend (requires Node 18+):

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

On first startup the backend creates its tables and seeds three demo users
(Alice, Bob, Carol) automatically — nothing else to set up.

## Running the tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -v
```

Tests run against an isolated in-memory SQLite database (via a FastAPI
dependency override), not the real CockroachDB instance, so they're fast and
don't need any credentials. 15 tests across three suites: `test_sharing.py`
(access control — an owner can access their document, a stranger gets a 404,
and after sharing the recipient gets access while a third user still
doesn't), `test_documents.py` (CRUD, validation, sanitization, upload), and
`test_versions.py` (version-history snapshot gating and restore).

## Deploying

- **Frontend → Vercel:** import the repo, set the root directory to
  `frontend/`, and set `NEXT_PUBLIC_API_URL` to the deployed backend URL.
- **Backend → Render:** `backend/render.yaml` defines the web service
  (Docker runtime). After connecting the repo, set `DATABASE_URL` (the
  CockroachDB connection string) and `CORS_ORIGINS` (the Vercel frontend URL)
  in the Render dashboard — both are intentionally left unset in
  `render.yaml` since they're environment-specific.

## Architecture notes — what I prioritized and why

Full rationale lives in [ARCHITECTURE.md](ARCHITECTURE.md) (design
decisions, the feature-to-file mapping, and what's deliberately out of
scope). Highlights:

- CockroachDB Cloud for both dev and prod, not SQLite — free-tier PaaS hosts
  wipe local disk on redeploy, which would break "documents persist after
  refresh."
- Documents are stored as sanitized HTML, not a custom format — Tiptap
  round-trips it losslessly, and it's also what file upload converts into.
- Access control (`get_accessible_document`) is enforced server-side and
  returns an indistinguishable 404 for "doesn't exist" vs. "not shared with
  you," so the API can't leak document existence.
