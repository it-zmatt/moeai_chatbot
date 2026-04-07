# MoeAI Chatbot

## API app (FastAPI)

The HTTP API lives in `apps/api`. You run a **Uvicorn** process there; that is the server clients talk to. PostgreSQL must already be running and reachable (for example on your VM); this repo does not start Postgres for you.

### Prerequisites

- Python 3.11+ (3.13 is fine)
- A PostgreSQL instance the API can reach, with `DATABASE_URL` pointing at it (async driver: `postgresql+asyncpg://...`)

### One-time setup

From the **repository root**:

```bash
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install --upgrade pip
apps/api/.venv/bin/pip install -r apps/api/requirements.txt
```

### Environment variables

Create `apps/api/.env` (this path is gitignored). You can start from the root `.env.example` and adjust values.

Required:

- `DATABASE_URL` — must use the **asyncpg** dialect, e.g. `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE`

`pydantic-settings` loads `.env` from the **current working directory**, so keep `apps/api/.env` and run commands from `apps/api` as shown below.

### Using the virtual environment

**Option A — activate (fish/bash/zsh):**

```bash
cd apps/api
source .venv/bin/activate
```

**Option B — no activate (call binaries directly):**

```bash
apps/api/.venv/bin/python ...
apps/api/.venv/bin/uvicorn ...
```

Deactivate after Option A: `deactivate`.

### Start the server

Always from **`apps/api`** so `.env` is found:

```bash
cd apps/api
source .venv/bin/activate   # optional
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Without activating, use the venv’s Uvicorn explicitly:

```bash
cd apps/api
.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **`--reload`** — auto-reload on code changes (development only).
- **`main:app`** — module `main.py`, FastAPI instance `app`.

### Test the API and database health

With the server running, **`GET /health`** runs `SELECT 1` against Postgres. If the database is reachable and credentials are correct:

```bash
curl -s http://127.0.0.1:8000/health
```

Expected JSON:

```json
{"status":"ok","database":"connected"}
```

If Postgres is down, the URL is wrong, or auth fails, you will usually see a **500** response and errors in the Uvicorn logs.

Optional quick check that the app imports (still requires `DATABASE_URL` in `apps/api/.env` or in the environment):

```bash
cd apps/api
.venv/bin/python -c "from main import app; print(app.title)"
```

### Summary

| What | Do you start it? |
|------|-------------------|
| **PostgreSQL** | Yes — on your VM or host; must match `DATABASE_URL`. |
| **FastAPI / Uvicorn** | Yes — that is “starting the app” (`uvicorn` as above). |
| **Virtualenv** | Not a server — activate it or use `.venv/bin/...` so dependencies are available. |
