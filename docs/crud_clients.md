# Step 5 — Clients API (CRUD, tenant-scoped)

This document records **what was built**, **checklists**, **HTTP endpoints**, and **how to test** the clients CRUD API.

---

## Goal

- Full **CRUD** for `clients` rows, scoped by **`tenant_id`** (every list/read/write must respect the tenant boundary).
- Align with the existing Postgres schema in `infra/supabase/migrations/0001_initial_schema.sql` and sample data in `infra/supabase/seed.sql`.

---

## Checklist — implementation steps

- [x] **Document** this file (`crud_clients.md`) before coding the feature.
- [x] **SQLAlchemy models** for `tenants` and `clients` (UUID PKs, `text[]` → PostgreSQL `ARRAY(Text)`, FK `clients.tenant_id → tenants.id`).
- [x] **Pydantic schemas** for create, update (partial), and read responses.
- [x] **Router** under `/tenants/{tenant_id}/clients` with:
  - [x] `GET` — list all clients for the tenant.
  - [x] `GET` — fetch one client by id (must belong to tenant).
  - [x] `POST` — create client for tenant.
  - [x] `PATCH` — partial update.
  - [x] `DELETE` — remove row (DB cascades to related tables per schema).
- [x] **Tenant guard** — unknown `tenant_id` → `404`.
- [x] **Cross-tenant access** — client exists but different tenant → `404` (no id leak).
- [x] **Unique slug** — DB unique on `clients.slug` → map conflict to `409`.
- [x] **Register router** in `apps/api/main.py`.
- [x] **Tests** — `pytest` integration tests (skipped automatically if `DATABASE_URL` is unset).

---

## HTTP endpoints (summary)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tenants/{tenant_id}/clients` | List clients for tenant |
| `GET` | `/tenants/{tenant_id}/clients/{client_id}` | Get one client |
| `POST` | `/tenants/{tenant_id}/clients` | Create client |
| `PATCH` | `/tenants/{tenant_id}/clients/{client_id}` | Partial update |
| `DELETE` | `/tenants/{tenant_id}/clients/{client_id}` | Delete client |

`{tenant_id}` and `{client_id}` are UUIDs.

---

## Request / response shapes (high level)

- **Create (`POST`)** — JSON body: `name`, `slug`, optional `allowed_domains`, `system_prompt`, `widget_color`, `widget_greeting`, `llm_provider`, `llm_model`, rate limits, `is_active`. Omitted fields use DB defaults where applicable.
- **Update (`PATCH`)** — any subset of the same fields (omit = leave unchanged).
- **Read (`GET`)** — full client row including `id`, `tenant_id`, timestamps.

Valid `llm_provider` values (DB check constraint): `openai`, `anthropic`, `groq`, `mistral`, `gemini`.

---

## Prerequisites for manual / integration testing

1. PostgreSQL reachable with the schema applied (e.g. Supabase local or VM + migration `0001_initial_schema.sql`).
2. Optional seed: `infra/supabase/seed.sql` provides deterministic UUIDs:
   - Tenant Acme: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1`
   - Client Acme Marketing: `cccccccc-cccc-cccc-cccc-ccccccccccc1`

3. `apps/api/.env` with:

   ```bash
   DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
   ```

4. Run API from `apps/api` so `.env` loads (see root `README.md`).

---

## Manual testing (curl)

Start server:

```bash
cd apps/api
.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**List clients** (use your real tenant UUID; seed example below):

```bash
curl -s "http://127.0.0.1:8000/tenants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/clients"
```

**Get by id**:

```bash
curl -s "http://127.0.0.1:8000/tenants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1"
```

**Create**:

```bash
curl -s -X POST "http://127.0.0.1:8000/tenants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/clients" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Test Client",
    "slug": "api-test-client-'$(date +%s)'",
    "allowed_domains": ["example.com"],
    "llm_provider": "openai",
    "llm_model": "gpt-4o"
  }'
```

**Patch** (replace UUIDs):

```bash
curl -s -X PATCH "http://127.0.0.1:8000/tenants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/clients/<CLIENT_UUID>" \
  -H "Content-Type: application/json" \
  -d '{"widget_greeting": "Updated greeting"}'
```

**Delete**:

```bash
curl -s -w "\nHTTP:%{http_code}\n" -X DELETE "http://127.0.0.1:8000/tenants/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/clients/<CLIENT_UUID>"
```

**Expected errors**:

- Unknown tenant → `404` with detail `Tenant not found`.
- Unknown client or wrong tenant → `404` with detail `Client not found`.
- Duplicate `slug` → `409` with detail `A client with this slug already exists`.

---

## Automated tests (pytest)

From `apps/api` with a real `DATABASE_URL` (tests create and delete their own rows; **requires** a working DB):

```bash
cd apps/api
export DATABASE_URL='postgresql+asyncpg://...'
.venv/bin/pytest tests/test_clients.py -v
```

`tests/conftest.py` loads `apps/api/.env` via `python-dotenv`, so if `DATABASE_URL` is only in that file, you do **not** need to export it manually. If `DATABASE_URL` is missing from both the environment and `.env`, client integration tests **skip** with a clear reason.

After each test, the suite **disposes** the SQLAlchemy async engine so connection pools are not tied to a stale asyncio loop (avoids “Future attached to a different loop” errors when running many async tests).

---

## Code map

| Area | Location |
|------|----------|
| Models | `apps/api/models/` |
| Pydantic schemas | `apps/api/schemas/clients.py` |
| HTTP routes | `apps/api/routers/clients.py` |
| App wiring | `apps/api/main.py` |
| Tests | `apps/api/tests/test_clients.py` |

---

## Related API

Tenant CRUD (separate router) lives under **`/tenants`** — list/create tenants and fetch/update/delete by `tenant_id`. Clients are always nested under **`/tenants/{tenant_id}/clients`** as documented above.

Interactive docs: with the server running, open **`http://127.0.0.1:8000/docs`** for the full OpenAPI operation list and request schemas.

---

## Notes

- **DELETE** is a hard delete. The schema uses `ON DELETE CASCADE` from `clients` into `api_keys`, `chat_sessions`, etc.; use only in environments where that is acceptable.
- **Auth**: not implemented in this step; all endpoints are open. Add tenant auth / API keys in a later step.
- The SQLAlchemy **`Client`** model links to **`Tenant`** with `relationship("Tenant")`; the inverse `Tenant.clients` collection was omitted to keep imports simple (listing clients uses explicit queries).

---

# Step 7 — Auth middleware + current-client clients CRUD

## Overview

This step protects non-public requests with an API key and rewires the clients router so the authenticated current client is injected from request context and used as the scope boundary.

**Auth header:** `X-API-Key: <raw-key>`

**Protected routes:** `/clients`, `/clients/{id}`, and `/clients/{client_id}/api-keys`.

## Endpoints

| Method | Path | Description | Status |
|---|---|---|---|
| `GET` | `/clients` | List clients for the authenticated tenant | `200 / 401` |
| `GET` | `/clients/{id}` | Fetch one client by UUID | `200 / 404 / 401` |
| `POST` | `/clients` | Create a client in the authenticated tenant | `201 / 409 / 401` |
| `PATCH` | `/clients/{id}` | Partial update for one client | `200 / 404 / 409 / 401` |
| `DELETE` | `/clients/{id}` | Delete one client | `204 / 404 / 401` |
| `GET` | `/clients/{client_id}/api-keys` | List API keys for the current client only | `200 / 403 / 404 / 401` |
| `GET` | `/clients/{client_id}/api-keys/{key_id}` | Fetch one API key | `200 / 403 / 404 / 401` |
| `POST` | `/clients/{client_id}/api-keys` | Create an API key | `201 / 403 / 404 / 401` |
| `PATCH` | `/clients/{client_id}/api-keys/{key_id}` | Update an API key label | `200 / 403 / 404 / 401` |
| `DELETE` | `/clients/{client_id}/api-keys/{key_id}` | Revoke an API key | `200 / 403 / 404 / 401` |
| `POST` | `/api-keys/validate` | Validate a raw API key | `200 / 401` |

## Checklist

### 7-A — Middleware

- [x] Added `apps/api/middleware/auth.py`.
- [x] Rejects missing or invalid `X-API-Key` values with `401`.
- [x] Skips public docs and health routes.
- [x] Injects the authenticated client into `request.state.current_client`.

### 7-B — Route context

- [x] Added `apps/api/dependencies/auth.py` with `get_current_client`.
- [x] Clients CRUD uses `current_client.tenant_id` as the scope boundary.
- [x] API-key routes require the path client to match the authenticated current client.

### 7-C — Clients CRUD

- [x] `GET /clients` returns all clients for the current tenant.
- [x] `GET /clients/{id}` returns one client or `404`.
- [x] `POST /clients` inserts a new client with the current tenant ID.
- [x] `PATCH /clients/{id}` applies only the provided fields.
- [x] `DELETE /clients/{id}` removes the client and returns `204`.

### 7-D — Tests

- [x] Added auth-aware tests for list/get/create/update/delete.
- [x] Added `401` coverage for missing and invalid API keys.
- [x] Test setup uses monkeypatched service helpers, so it runs without live Postgres.

## Testing details

Run the clients auth tests:

```bash
cd apps/api
DATABASE_URL='postgresql+asyncpg://u:p@127.0.0.1:5432/db' \
  .venv/bin/pytest tests/test_clients.py -v
```

Expected result: the clients auth test suite passes.

## Smoke tests

Start the server:

```bash
cd apps/api
.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

List clients:

```bash
curl -s http://127.0.0.1:8000/clients -H 'X-API-Key: <raw-key>' | python3 -m json.tool
```

Fetch one client:

```bash
curl -s http://127.0.0.1:8000/clients/<UUID> -H 'X-API-Key: <raw-key>' | python3 -m json.tool
```

Create a client:

```bash
curl -s -X POST http://127.0.0.1:8000/clients \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <raw-key>' \
  -d '{"name":"New Client","slug":"new-client"}' | python3 -m json.tool
```

Missing key returns `401`:

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" http://127.0.0.1:8000/clients
```
