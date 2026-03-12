# Iteration 01 — 2026-03-12

## Context

Set up the project scaffold for the vendor portal using the full tech stack with latest versions. Python 3.13 backend (FastAPI, uvicorn, aiosqlite, hatchling, uv), SvelteKit 2 + Svelte 5 frontend (adapter-static, @vite-pwa/sveltekit, marked), and shared tooling (Makefile, gitignore, directory structure).

## Jobs to Be Done

1. **When** I clone the repo and run the setup, **I want to** have a working Python backend scaffold with FastAPI, uvicorn, and SQLite (WAL mode), **so that** I can start building domain features without plumbing work.

2. **When** I open the frontend, **I want to** have a working SvelteKit 2 + Svelte 5 app with static adapter, **so that** I can build web UIs targetting latest browsers.

3. **When** I work on the project, **I want to** have consistent tooling (Makefile, gitignore, directory conventions), **so that** common tasks like running tests, starting dev servers, and building are one command away.


## Tasks

### JTBD 1 — Backend scaffold
- [x] Init `pyproject.toml` with hatchling build, uv package manager, Python 3.13
- [x] Add runtime deps: fastapi, uvicorn, aiosqlite, itsdangerous, sse-starlette
- [x] Add dev deps: pytest, pytest-asyncio, httpx
- [x] Create `backend/src/` package with `__init__.py`
- [x] Create `backend/src/main.py` with FastAPI app and a health endpoint
- [x] Create `backend/src/db.py` with async SQLite connection (WAL mode)
- [x] Run `uv sync` and verify the app starts

### JTBD 2 — Frontend scaffold
- [x] `npm create svelte@latest frontend` with SvelteKit 2 + Svelte 5, TypeScript
- [x] Add deps: `@sveltejs/adapter-static`, `marked`
- [x] Configure `svelte.config.js` with adapter-static
- [x] Verify `npm run dev` starts

### JTBD 3 — Tooling
- [x] Create `.gitignore` (Python, Node, SQLite, logs/, frontend/tests/scratch, backend/tests/scratch, tools, data/)
- [x] Create `Makefile` with targets: `up`, `down`, `test-backend`, `test-browser`
- [x] Create `docs/` directory with `ddd-vocab.md` and `workspace/` placeholder
- [x] Create directories
- [x] `git init`

## Notes

Project scaffolded with latest versions: FastAPI 0.135, uvicorn 0.41, aiosqlite 0.22, SvelteKit 2 + Svelte 5 + Vite 7.3. Backend source lives at `backend/src/`, frontend at `frontend/`. Static adapter in SPA fallback mode. Both dev servers verified working.
