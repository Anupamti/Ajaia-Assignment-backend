# Architecture

## System overview

A conventional two-tier web app: a Next.js/TypeScript frontend talks to a
FastAPI backend over a JSON REST API, and the backend talks to a single
CockroachDB Cloud database (used identically for local dev and production —
no separate dev/prod storage). Auth is a stateless JWT in an httpOnly cookie;
there is no session store, message queue, or cache layer — the app is small
enough that none of those earn their complexity yet.

```
frontend/ (Next.js App Router)        backend/ (FastAPI)
  app/login, app/, app/documents/[id]   routers/ auth, documents, upload, versions
  components/ Editor, ShareDialog,      models.py: User, Document,
    VersionHistory, Header                DocumentShare, DocumentVersion
  lib/api.ts (typed fetch client)       auth.py: JWT issue/verify
        |  JSON over HTTPS, cookie auth        |
        `-------------------------------------->  CockroachDB Cloud
```

## Decisions and why

**CockroachDB Cloud everywhere, not SQLite.** Most free-tier PaaS hosts wipe
local disk on redeploy/restart, so a SQLite file would silently lose data —
directly violating "documents remain available after refresh." Using the
same CockroachDB instance for local dev and production also means there's
only one code path to reason about, no dev/prod schema drift. One wrinkle:
SQLAlchemy's generic Postgres dialect can't parse CockroachDB's
`SELECT version()` output, so the app depends on `sqlalchemy-cockroachdb`
and connection strings use the `cockroachdb://` scheme.

**HTML as the single content representation.** Tiptap's `getHTML()` /
`setContent()` round-trip bold/italic/underline/headings/lists losslessly,
so documents are stored as sanitized HTML (via `bleach`) rather than a custom
JSON format. This also makes file upload trivial — `.md` is rendered to HTML
with `python-markdown`, `.txt` is wrapped into paragraphs, and both land in
the exact same `content_html` column an edited document uses. One
representation, one code path, for both the editor and the importer.

**Stateless JWT-in-a-cookie auth over a session store.** With three seeded,
password-less users, a database-backed session table would be pure overhead.
A signed JWT in an httpOnly cookie gets the same "who is this request from"
answer with no extra state to manage — appropriate for this scope, not
something I'd reach for with real passwords or refresh-token rotation needs.

**IDs are serialized as strings, not JSON numbers.** CockroachDB's default
row IDs are 64-bit and exceed JavaScript's safe integer range (2^53), so
sending them as JSON numbers silently corrupts them once `JSON.parse` rounds
them in the browser. Every ID crosses the API as a string (`IdStr` in
`backend/app/schemas.py`, `id: string` throughout the frontend) — the same
approach Stripe/Twitter/Discord use for large IDs.

**Access control is enforced server-side, not just hidden in the UI.**
`get_accessible_document` (`backend/app/routers/documents.py`) is the single
place that decides owner-or-shared-or-404 for every document (and version)
route, and a non-shared user gets an indistinguishable 404 (not a 403) so the
API doesn't leak whether a document exists. This is exercised directly by
`backend/tests/test_sharing.py`.

**Version history checkpoints on a time gate, not every keystroke.** Autosave
fires ~every 600ms while typing, so snapshotting on every save would flood
the table. Instead, `update_document` checkpoints the pre-edit state only if
the last checkpoint is more than 5 minutes old (`VERSION_SNAPSHOT_INTERVAL`
in `backend/app/routers/documents.py`), giving Google-Docs-style "restore an
earlier point in time" without per-keystroke rows. Restoring a version always
force-checkpoints the current state first (bypassing the gate), so a restore
is itself undoable. Covered by `backend/tests/test_versions.py`.

**Deliberately out of scope:** no granular permission levels (view vs. edit
— anyone a document is shared with can currently edit it), no real
password/OAuth authentication, no live multi-user collaborative cursors, no
document deletion. These are the natural next additions but weren't needed
to demonstrate the required capabilities at this scope.

## What each feature maps to

| Requirement | Where |
|---|---|
| Create / rename / edit / persist | `backend/app/routers/documents.py`, `frontend/app/documents/[id]/page.tsx` |
| Rich text (bold/italic/underline/headings/lists) | `frontend/components/Editor.tsx` (Tiptap) |
| File upload | `backend/app/routers/upload.py`, `backend/app/converters.py` |
| Sharing | `backend/app/models.py` (`DocumentShare`), `frontend/components/ShareDialog.tsx` |
| Version history (bonus, beyond original scope) | `backend/app/models.py` (`DocumentVersion`), `backend/app/routers/versions.py`, `frontend/components/VersionHistory.tsx` |
| Owned vs. shared distinction | `DocumentListItem.is_owner`, dashboard sections in `frontend/app/page.tsx` |
| Persistence | CockroachDB via SQLAlchemy |
| Validation / error handling | Pydantic schemas, explicit 400/401/403/404 responses, `ApiError` surfaced as inline UI errors |
| Automated tests | `backend/tests/test_sharing.py`, `test_documents.py`, `test_versions.py` (15 tests total) |
