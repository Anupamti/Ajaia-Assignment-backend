# Submission

## What's included

- [README.md](README.md) — setup, local run instructions (Docker Compose or
  manual), supported upload file types, how to run tests, deploy steps.
- [ARCHITECTURE.md](ARCHITECTURE.md) — system overview and the reasoning
  behind each significant decision.
- [AI_WORKFLOW.md](AI_WORKFLOW.md) — how Claude Code was used to build this,
  including two real bugs found and fixed through actual browser testing.
- `backend/` — FastAPI + SQLAlchemy API, CockroachDB Cloud, `pytest` suite.
- `frontend/` — Next.js (App Router) + TypeScript, Tiptap rich-text editor.
- `docker-compose.yml`, `backend/render.yaml` — local and hosted run configs.

## Requirements checklist

| Requirement | Status | Where |
|---|---|---|
| Create / rename / edit / persist a document | Done | `backend/app/routers/documents.py`, `frontend/app/documents/[id]/page.tsx` |
| Rich text: bold, italic, underline, headings, lists | Done | `frontend/components/Editor.tsx` (Tiptap) |
| File upload (`.txt`, `.md` → new document) | Done, types stated in UI + README | `backend/app/routers/upload.py`, `backend/app/converters.py` |
| Sharing (owner, grant access, owned-vs-shared distinction) | Done | `backend/app/models.py` (`DocumentShare`), `frontend/components/ShareDialog.tsx` |
| Persistence across refresh, formatting preserved | Done — verified against the real CockroachDB instance, not just SQLite tests | CockroachDB via SQLAlchemy |
| Setup/run instructions | Done | [README.md](README.md) |
| Validation and error handling | Done | Pydantic schemas; explicit 400/401/403/404 responses; sanitized HTML via `bleach` |
| At least one meaningful automated test | Done — 15 tests total | `backend/tests/` (`test_sharing.py`, `test_documents.py`, `test_versions.py`) |
| Architecture note | Done | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Bonus, beyond the original scope:** version history + restore | Done | `backend/app/routers/versions.py`, `frontend/components/VersionHistory.tsx` — see [AI_WORKFLOW.md](AI_WORKFLOW.md) for a note on how this feature's provenance is being reported |

## Current status — stated plainly

- **Local run: fully working**, verified end-to-end in a real browser
  (login, formatting, refresh-persistence, rename, upload, sharing,
  cross-user access control) against the actual CockroachDB Cloud instance,
  not just an in-memory test database.
- **Not yet pushed to a git remote.** This has been developed as a local
  working directory; a GitHub repo was intentionally deferred by the user
  and can be pushed on request.
- **Not yet deployed.** `README.md`'s "Live deployment" section still has
  placeholder URLs — the hosting plan (Vercel for the frontend, Render for
  the backend) and the config for it (`backend/render.yaml`) are in place,
  but the actual deploy step is pending the git push above.

## How to verify

```bash
cd backend
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt
PYTHONPATH=. pytest -v
```
15 tests, all passing: 6 document CRUD/validation tests, 4 sharing/access-
control tests, 5 version-history/restore tests.

For running the app itself (Docker Compose or manual, both backend and
frontend), see [README.md](README.md) — instructions aren't duplicated here
to avoid the two drifting out of sync.
