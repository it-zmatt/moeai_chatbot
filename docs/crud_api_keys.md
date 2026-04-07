# API Keys CRUD — Step 6

Complete reference for building the API Keys feature: endpoints, implementation checklist, and testing guide.

---

## Table of Contents

1. [Schema Reference](#schema-reference)
2. [Endpoints](#endpoints)
3. [Implementation Checklist](#implementation-checklist)
4. [Security Design](#security-design)
5. [Testing Guide](#testing-guide)

---

## Schema Reference

Table: `api_keys` (from `infra/supabase/migrations/0001_initial_schema.sql`)

| Column         | Type        | Notes                                      |
|----------------|-------------|--------------------------------------------|
| `id`           | uuid        | PK, auto-generated                         |
| `client_id`    | uuid        | FK → `clients.id` ON DELETE CASCADE        |
| `key_hash`     | text        | bcrypt hash — raw key is NEVER stored      |
| `label`        | text        | nullable, human-readable name              |
| `is_active`    | boolean     | default `true`; set to `false` to revoke   |
| `last_used_at` | timestamptz | nullable; updated on successful validation |
| `created_at`   | timestamptz | auto                                       |
| `updated_at`   | timestamptz | auto via trigger                           |

---

## Endpoints

Base path: `/api/v1`

### GET — List all keys for a client

```
GET /clients/{client_id}/api-keys
```

- Returns all `api_keys` rows for the given `client_id`.
- `key_hash` is **never** returned in any response.
- Optional query param `?active_only=true` filters out revoked keys.

**Response `200`**
```json
[
  {
    "id": "dddddddd-dddd-dddd-dddd-ddddddddddd1",
    "client_id": "cccccccc-cccc-cccc-cccc-ccccccccccc1",
    "label": "Staging embed key",
    "is_active": true,
    "last_used_at": "2026-04-06T10:00:00Z",
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-04-01T09:00:00Z"
  }
]
```

**Response `404`** — client not found

---

### GET — Fetch single key by ID

```
GET /clients/{client_id}/api-keys/{key_id}
```

- Returns a single `api_key` row.
- Validates `key_id` belongs to `client_id`.
- `key_hash` is **never** returned.

**Response `200`**
```json
{
  "id": "dddddddd-dddd-dddd-dddd-ddddddddddd1",
  "client_id": "cccccccc-cccc-cccc-cccc-ccccccccccc1",
  "label": "Staging embed key",
  "is_active": true,
  "last_used_at": "2026-04-06T10:00:00Z",
  "created_at": "2026-04-01T09:00:00Z",
  "updated_at": "2026-04-01T09:00:00Z"
}
```

**Response `404`** — key not found or does not belong to client

---

### POST — Generate new API key

```
POST /clients/{client_id}/api-keys
```

- Generates a cryptographically secure key: `moe_<secrets.token_urlsafe(32)>`
- Hashes it with **bcrypt** (via passlib) before storing.
- Returns the **raw key exactly once** — it cannot be retrieved again.

**Request body**
```json
{
  "label": "Production widget"
}
```

**Response `201`**
```json
{
  "id": "dddddddd-dddd-dddd-dddd-ddddddddddd5",
  "client_id": "cccccccc-cccc-cccc-cccc-ccccccccccc1",
  "label": "Production widget",
  "is_active": true,
  "last_used_at": null,
  "created_at": "2026-04-06T12:00:00Z",
  "updated_at": "2026-04-06T12:00:00Z",
  "raw_key": "moe_abc123...xyz"
}
```

> `raw_key` only appears in this 201 response. Store it immediately — it cannot be recovered.

**Response `404`** — client not found

---

### PATCH — Update key label

```
PATCH /clients/{client_id}/api-keys/{key_id}
```

- Only `label` is updatable via this endpoint.

**Request body**
```json
{
  "label": "New label"
}
```

**Response `200`** — returns updated `ApiKeyResponse` (no `raw_key`)

**Response `404`** — key not found or does not belong to client

---

### DELETE — Revoke key (soft delete)

```
DELETE /clients/{client_id}/api-keys/{key_id}
```

- Sets `is_active = false` — **does not hard-delete** the row (preserves audit trail).
- Idempotent: revoking an already-revoked key returns `200`.

**Response `200`**
```json
{
  "id": "dddddddd-dddd-dddd-dddd-ddddddddddd1",
  "client_id": "cccccccc-cccc-cccc-cccc-ccccccccccc1",
  "label": "Staging embed key",
  "is_active": false,
  "last_used_at": "2026-04-06T10:00:00Z",
  "created_at": "2026-04-01T09:00:00Z",
  "updated_at": "2026-04-06T13:00:00Z"
}
```

**Response `404`** — key not found or does not belong to client

---

### POST — Validate a raw key

```
POST /api-keys/validate
```

- Used internally by the chat/widget endpoint to authenticate incoming requests.
- Scans active keys for the client, verifies with bcrypt.
- On success: updates `last_used_at` and returns `client_id`.

**Request body**
```json
{
  "raw_key": "moe_abc123...xyz"
}
```

**Response `200`**
```json
{
  "valid": true,
  "client_id": "cccccccc-cccc-cccc-cccc-ccccccccccc1",
  "key_id": "dddddddd-dddd-dddd-dddd-ddddddddddd1"
}
```

**Response `401`**
```json
{
  "valid": false,
  "detail": "Invalid or revoked API key"
}
```

---

## Implementation Checklist

### Step 6A — Models

- [x] `apps/api/models/__init__.py` — updated to export `ApiKey`
- [x] `apps/api/models/base.py` — SQLAlchemy `DeclarativeBase` (pre-existing)
- [x] `apps/api/models/api_key.py` — `ApiKey` ORM model matching schema

### Step 6B — Schemas (Pydantic)

- [x] `apps/api/schemas/api_key.py` with:
  - `ApiKeyCreate` — `label: str | None`
  - `ApiKeyUpdate` — `label: str | None`
  - `ApiKeyResponse` — all fields except `key_hash`
  - `ApiKeyCreatedResponse` — extends `ApiKeyResponse` + `raw_key: str`
  - `ApiKeyValidateRequest` — `raw_key: str`
  - `ApiKeyValidateResponse` — `valid`, `client_id`, `key_id`

### Step 6C — Database session

- [x] `apps/api/core/database.py` — pre-existing, used as-is (`get_session`)

### Step 6D — Service layer

- [x] `apps/api/services/api_key_service.py`:
  - `generate_raw_key()` — `moe_` + `secrets.token_urlsafe(32)`
  - `hash_key(raw)` — bcrypt via passlib
  - `verify_key(raw, hashed)` — bcrypt verify
  - `list_api_keys(db, client_id, active_only)` — SELECT with optional filter
  - `get_api_key(db, client_id, key_id)` — SELECT single
  - `create_api_key(db, client_id, label)` — generate + hash + INSERT
  - `update_api_key(db, client_id, key_id, label)` — UPDATE label
  - `revoke_api_key(db, client_id, key_id)` — set `is_active=False`
  - `validate_api_key(db, raw_key)` — scan active keys, bcrypt verify, update `last_used_at`

### Step 6E — Router

- [x] `apps/api/routers/api_keys.py`:
  - `GET  /clients/{client_id}/api-keys`
  - `GET  /clients/{client_id}/api-keys/{key_id}`
  - `POST /clients/{client_id}/api-keys`
  - `PATCH /clients/{client_id}/api-keys/{key_id}`
  - `DELETE /clients/{client_id}/api-keys/{key_id}`
  - `POST /api-keys/validate`
- [x] `apps/api/main.py` — `keys_router` and `validate_router` registered

### Step 6F — Tests

- [x] `apps/api/tests/test_api_keys.py` — 19 pytest-asyncio integration tests

---

## Security Design

| Concern | Approach |
|---|---|
| Key storage | Only bcrypt hash stored in DB — raw key never persisted |
| Key format | `moe_` prefix + `secrets.token_urlsafe(32)` (~256 bits entropy) |
| Hash algorithm | bcrypt via `passlib[bcrypt]` (already in `requirements.txt`) |
| `key_hash` exposure | Never returned in any API response |
| Revocation | Soft delete (`is_active=False`) — preserves audit trail |
| `last_used_at` | Updated on every successful validation |

---

## Testing Guide

### Setup

```bash
cd apps/api
source .venv/bin/activate
pip install pytest pytest-asyncio httpx

# Apply migrations + seed data
supabase db reset
```

### Run tests

```bash
pytest apps/api/tests/test_api_keys.py -v
```

### Manual cURL examples

**List all keys for a client**
```bash
curl http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys
```

**List active keys only**
```bash
curl "http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys?active_only=true"
```

**Get key by ID**
```bash
curl http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys/dddddddd-dddd-dddd-dddd-ddddddddddd1
```

**Generate a new key**
```bash
curl -X POST http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys \
  -H "Content-Type: application/json" \
  -d '{"label": "My new key"}'
```

**Update label**
```bash
curl -X PATCH http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys/dddddddd-dddd-dddd-dddd-ddddddddddd1 \
  -H "Content-Type: application/json" \
  -d '{"label": "Updated label"}'
```

**Revoke key**
```bash
curl -X DELETE http://localhost:8000/api/v1/clients/cccccccc-cccc-cccc-cccc-ccccccccccc1/api-keys/dddddddd-dddd-dddd-dddd-ddddddddddd1
```

**Validate a raw key**
```bash
curl -X POST http://localhost:8000/api/v1/api-keys/validate \
  -H "Content-Type: application/json" \
  -d '{"raw_key": "moe_abc123..."}'
```

### Test Case Matrix

| # | Endpoint | Scenario | Expected |
|---|----------|----------|----------|
| 1 | GET list | valid client with keys | 200, list of keys, no `key_hash` field |
| 2 | GET list | `?active_only=true` | 200, only `is_active=true` keys |
| 3 | GET list | unknown `client_id` | 404 |
| 4 | GET one | valid client + key | 200, single key object, no `key_hash` |
| 5 | GET one | key belongs to different client | 404 |
| 6 | GET one | unknown `key_id` | 404 |
| 7 | POST | valid client, with label | 201, response contains `raw_key` |
| 8 | POST | valid client, no label | 201, `label=null` |
| 9 | POST | unknown `client_id` | 404 |
| 10 | POST | security check | `key_hash` in DB != `raw_key` in response |
| 11 | PATCH | update label | 200, updated label, no `raw_key` |
| 12 | PATCH | key belongs to different client | 404 |
| 13 | DELETE | active key | 200, `is_active=false` |
| 14 | DELETE | already-revoked key (idempotent) | 200, `is_active=false` |
| 15 | DELETE | unknown key | 404 |
| 16 | POST validate | valid active key | 200, `valid=true`, `client_id` returned |
| 17 | POST validate | wrong key value | 401, `valid=false` |
| 18 | POST validate | revoked key | 401, `valid=false` |
| 19 | POST validate | successful call | `last_used_at` updated in DB |
