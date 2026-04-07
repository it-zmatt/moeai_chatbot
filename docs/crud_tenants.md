# Step 4 — Tenants API (CRUD)

This document records **what was built**, **checklists**, **HTTP endpoints**, and **how to test** the tenants CRUD API.

---

## Goal

Full **CRUD** for the `tenants` table — the root entity every client, API key, and session belongs to.

---

## Checklist — implementation steps

- [x] **Document** this file (`crud_tenants.md`) before coding the feature.
- [x] **SQLAlchemy model** — `apps/api/models/tenant.py` mirrors the DB schema (`id` UUID PK, `name`, `slug` UNIQUE, `contact_email`, `plan` string, `is_active`, `created_at`, `updated_at`).
- [x] **Shared `Base`** — `apps/api/models/base.py` (`DeclarativeBase`), imported by all ORM models.
- [x] **Pydantic schemas** — `apps/api/schemas/tenant.py`:
  - `TenantCreate` — required fields for `POST` body.
  - `TenantUpdate` — all fields optional for `PATCH` body.
  - `TenantResponse` — output shape with `from_attributes=True`.
- [x] **Router** — `apps/api/routers/tenants.py` with five endpoints (see table below).
  - Duplicate `slug` → `409 Conflict`.
  - Unknown `id` → `404 Not Found`.
- [x] **Register router** in `apps/api/main.py` at prefix `/tenants`.
- [x] **Tests** — `apps/api/tests/test_tenants.py` (10 tests); fixtures in `apps/api/tests/conftest.py`.

---

## HTTP endpoints

| Method   | Path                  | Description              | Success code     | Error codes      |
|----------|-----------------------|--------------------------|------------------|------------------|
| `GET`    | `/tenants`            | List all tenants         | `200 OK`         |                  |
| `GET`    | `/tenants/{id}`       | Get one tenant by UUID   | `200 OK`         | `404`            |
| `POST`   | `/tenants`            | Create a new tenant      | `201 Created`    | `409` (dup slug) |
| `PATCH`  | `/tenants/{id}`       | Partial update a tenant  | `200 OK`         | `404`, `409`     |
| `DELETE` | `/tenants/{id}`       | Hard delete a tenant     | `204 No Content` | `404`            |

---

## Request / response shapes

### POST / PATCH body fields

| Field           | Type    | Required (POST) | Notes                                       |
|-----------------|---------|-----------------|---------------------------------------------|
| `name`          | string  | yes             |                                             |
| `slug`          | string  | yes             | Must be unique across all tenants           |
| `contact_email` | string  | yes             |                                             |
| `plan`          | string  | no              | `free` (default) / `starter` / `pro` / `enterprise` |
| `is_active`     | boolean | no              | Defaults to `true`                          |

### Response (`TenantResponse`)

```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme",
  "contact_email": "admin@acme.com",
  "plan": "starter",
  "is_active": true,
  "created_at": "2026-04-06T10:00:00Z",
  "updated_at": "2026-04-06T10:00:00Z"
}
```

---

## Code map

| Area            | Location                              |
|-----------------|---------------------------------------|
| ORM model       | `apps/api/models/tenant.py`           |
| Pydantic schemas| `apps/api/schemas/tenant.py`          |
| HTTP routes     | `apps/api/routers/tenants.py`         |
| App wiring      | `apps/api/main.py`                    |
| Tests           | `apps/api/tests/test_tenants.py`      |
| Test fixtures   | `apps/api/tests/conftest.py`          |

---

## Prerequisites for manual / integration testing

1. PostgreSQL reachable with the schema applied (`infra/supabase/migrations/0001_initial_schema.sql`).
2. `apps/api/.env`:

   ```bash
   DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
   ```

3. Run API from `apps/api` so `.env` loads:

   ```bash
   cd apps/api
   .venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## Manual smoke tests (curl)

### GET /tenants — list all

```bash
curl -s http://127.0.0.1:8000/tenants | python3 -m json.tool
```

Expected: `[]` on a fresh DB, or an array of tenant objects.

### POST /tenants — create

```bash
curl -s -X POST http://127.0.0.1:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Acme Corp",
        "slug": "acme",
        "contact_email": "admin@acme.com",
        "plan": "starter"
      }' | python3 -m json.tool
```

Expected: `201 Created` with the full tenant object including `id`, `created_at`, `updated_at`.

### GET /tenants/{id} — fetch by ID

```bash
curl -s http://127.0.0.1:8000/tenants/<UUID> | python3 -m json.tool
```

Expected: the same tenant object.

### GET /tenants/{id} — not found

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  http://127.0.0.1:8000/tenants/00000000-0000-0000-0000-000000000000
```

Expected: `HTTP_CODE:404` with `{"detail":"Tenant not found"}`.

### PATCH /tenants/{id} — partial update

```bash
curl -s -X PATCH http://127.0.0.1:8000/tenants/<UUID> \
  -H "Content-Type: application/json" \
  -d '{"plan": "pro", "is_active": false}' | python3 -m json.tool
```

Expected: `200 OK` with `plan` changed to `"pro"` and `is_active` changed to `false`; other fields unchanged.

### DELETE /tenants/{id} — delete

```bash
curl -s -o /dev/null -w "HTTP_CODE:%{http_code}\n" \
  -X DELETE http://127.0.0.1:8000/tenants/<UUID>
```

Expected: `HTTP_CODE:204`.

Verify it's gone:

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" http://127.0.0.1:8000/tenants/<UUID>
```

Expected: `HTTP_CODE:404`.

### POST /tenants — duplicate slug → 409

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -X POST http://127.0.0.1:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Copy", "slug": "acme", "contact_email": "x@x.com"}'
```

Expected: `HTTP_CODE:409` with `{"detail":"A tenant with this slug already exists"}`.

---

## Automated tests (pytest)

Tests require a live `DATABASE_URL` (set in environment or `apps/api/.env`). Each test uses a unique slug so runs never conflict with each other or existing data.

```bash
cd apps/api
.venv/bin/pytest tests/test_tenants.py -v
```

Expected: **10 tests pass**.

| Test | What it checks |
|------|---------------|
| `test_list_tenants_returns_json_list` | `GET /tenants` → 200, array |
| `test_list_tenants_returns_created` | Created tenant appears in list |
| `test_get_tenant_by_id` | `GET /tenants/{id}` → 200, correct fields |
| `test_get_tenant_not_found` | Zero UUID → 404 |
| `test_create_tenant_returns_201` | All response fields present |
| `test_create_tenant_duplicate_slug_returns_409` | Dup slug → 409 |
| `test_patch_tenant` | `PATCH` changes only supplied fields |
| `test_patch_tenant_not_found` | Zero UUID → 404 |
| `test_delete_tenant` | 204, then 404 on re-fetch |
| `test_delete_tenant_not_found` | Zero UUID → 404 |

---

## Interactive docs

With the server running:

- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

All five `/tenants` endpoints will appear under the `tenants` tag.

---

## Notes

- **DELETE** is a hard delete. The DB schema cascades deletes from `tenants` into `clients`, `api_keys`, `chat_sessions`, etc.
- **Auth**: not yet implemented — all endpoints are open. Auth will be added in a later step.
