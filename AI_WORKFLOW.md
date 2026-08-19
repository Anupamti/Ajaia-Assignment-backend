# AI workflow note

This app was built with Claude Code (Claude Sonnet 5). This is a specific
account of how, not a generic AI-usage disclaimer.

## Planning vs. autonomous execution

Stack and hosting weren't decided unilaterally. I proposed a default stack
(React/Vite + Node/Express + SQLite), the user asked what I'd use and then
redirected it twice — first to Python/FastAPI + Next.js/TypeScript, then to
a specific hosting split (Vercel + Render) — and a database choice (SQLite
vs. Postgres) got escalated back to the user via `AskUserQuestion` because
free-tier host disk persistence was a real constraint, not a style
preference. Once those decisions were made, implementation (schemas,
routers, React components, tests) proceeded autonomously in plan mode:
propose a concrete plan file, get it approved, then execute without
re-asking for every file.

## Verification, not just "it compiled"

`pytest` alone doesn't prove a browser feature works. I started both dev
servers, wrote a Playwright script (`chromium` headless), and drove the
actual golden path in a real browser: login → apply every formatting
control → refresh and confirm persistence → rename → upload a `.txt` file →
share with a second user → confirm a third user is denied access. I looked
at the resulting screenshots, not just exit codes.

That browser testing caught two real bugs that unit tests alone would have
missed:

1. **Toolbar focus loss.** Clicking a Bold/Heading/List button could steal
   DOM focus from the Tiptap editor; the very next keystroke then landed
   nowhere and was silently dropped. Reproduced by watching typed text
   simply not appear after a toolbar click in the Playwright run. Fixed with
   `onMouseDown={(e) => e.preventDefault()}` on each toolbar button
   (`frontend/components/Editor.tsx`).

2. **CockroachDB ID precision loss.** Everything passed against an in-memory
   SQLite test database with small sequential IDs. Once pointed at the real
   CockroachDB instance (64-bit row IDs), login and sharing started failing
   with 404s. Root cause: those IDs exceed JavaScript's safe integer range
   (2^53), so `JSON.parse` in the browser silently rounded them to a
   different number than the one actually stored — confirmed directly with
   `JSON.parse('{"id": 1202872576101548033}').id !== 1202872576101548033`.
   Fixed by serializing every ID as a string end-to-end (`IdStr` in
   `backend/app/schemas.py`, `id: string` throughout the frontend) rather
   than patching around individual symptoms. This is a class of bug that
   only a test against the real production-shaped data would surface —
   worth calling out explicitly since it's the kind of thing "tests pass"
   can hide.

## Handling a live credential mid-conversation

The user shared a CockroachDB username and password mid-task, via a
screenshot and then plain text. It was never echoed back in conversation
text, never written into memory, and never placed in a file that wasn't
already covered by `.gitignore` — `.gitignore` was set up proactively before
the credential was used. The CA certificate needed for TLS (`sslmode=verify-
full`) was committed to the repo (`backend/certs/root.crt`) because it's a
public certificate, not a secret — the two were treated differently on
purpose rather than reflexively hiding everything credential-shaped.

## One honest caveat

The version-history/restore feature (`DocumentVersion` model,
`backend/app/routers/versions.py`, `frontend/components/VersionHistory.tsx`,
`backend/tests/test_versions.py`) showed up in the codebase between two
turns of this same overall project without me directly narrating its
construction — a fresh repository survey is what surfaced it, complete and
tested, rather than a memory of building it step by step. It's real,
working, and covered by 5 passing tests, so `ARCHITECTURE.md` and
`SUBMISSION.md` describe it as-is and credit it as a capability beyond the
original assignment scope — but I'm flagging the provenance gap rather than
silently claiming a continuous authorship narrative I can't fully account
for.
