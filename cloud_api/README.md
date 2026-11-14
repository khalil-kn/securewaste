# SecureWaste cloud API

The cloud side of SecureWaste receives **scan metadata only**: an event id, a timestamp, a
classification, a risk level and three counts. Document text, filenames, paths and matched
values never leave the local scanner (ADR-0006).

## Layout

| File | Purpose |
| --- | --- |
| `schema.sql` | The `scan_events` table and its indexes. The only place the DDL is written. |
| `db.py` | Connection handling, insert and read of one scan event. |
| `config.py` | Settings read from environment variables. |
| `validation.py` | The request contract: allowed keys, values and counts. Pure functions. |
| `auth.py` | The bearer token guard and the roles that may store a scan. |
| `routes.py` | The HTTP endpoints. |
| `app.py` | The application factory. |
| `__main__.py` | `python -m cloud_api`, the local entry point. |

## Local database

The API needs PostgreSQL 16 or newer. The quickest way is a container:

```bash
podman run -d --name sw-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=securewaste_cloud \
  -p 5432:5432 docker.io/library/postgres:16-alpine

export CLOUD_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/securewaste_cloud
```

A local PostgreSQL installation works the same way; only the URL changes.

The schema is a migration script: apply it before starting the API or running the tests.

```bash
podman exec -i sw-pg psql -U postgres -d securewaste_cloud < cloud_api/schema.sql
```

## Configuration

| Variable | Meaning |
| --- | --- |
| `CLOUD_DATABASE_URL` | PostgreSQL URL of the cloud database. |
| `CLOUD_API_HOST` | Address the API listens on. Default `127.0.0.1`. |
| `CLOUD_API_PORT` | Port the API listens on. Default `5001`. |
| `CLOUD_API_TOKENS` | Bearer tokens and their roles: `token:role,token:role`. |

A role that may store scan events: `employee`, `admin`, `security_officer`. Any other role gets
`403`. When `CLOUD_API_TOKENS` is unset, every write is refused with `401`. Copy
`.env.example` and replace the placeholder tokens before running the service.

## Endpoints

### `GET /health`

Public liveness check. It says nothing about the database and holds no secret.

```bash
curl http://127.0.0.1:5001/health
```

```json
{ "status": "ok", "service": "securewaste-cloud" }
```

### `POST /api/v1/scans`

Stores the metadata of one scan event.

```bash
curl -X POST http://127.0.0.1:5001/api/v1/scans \
  -H "Authorization: Bearer $CLOUD_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "3f0c1d2e-4b5a-4c6d-8e9f-0a1b2c3d4e5f",
    "timestamp": "2026-11-20T10:30:00Z",
    "classification": "Confidential",
    "risk": "High",
    "counts": { "email": 2, "phone": 1, "keyword": 3 }
  }'
```

```json
{ "event_id": "3f0c1d2e-4b5a-4c6d-8e9f-0a1b2c3d4e5f", "status": "stored" }
```

The contract:

- `event_id`: a UUID, unique in the table.
- `timestamp`: an ISO 8601 date and time with a timezone offset.
- `classification`: one of `Public`, `Internal`, `Confidential`, `Highly Confidential`.
- `risk`: one of `Low`, `Medium`, `High`.
- `counts`: an object with the keys `email`, `phone` and `keyword`, each a non-negative integer.

Any other key is refused, so document text, file names, paths and matched values cannot reach
the database even by accident.

| Status | When |
| --- | --- |
| `201` | The scan event is stored. |
| `400` | The body is not valid JSON or does not match the contract. The response lists the fields to fix. |
| `401` | The bearer token is missing or unknown. |
| `403` | The role of the token may not store scan events. |
| `409` | This `event_id` is already stored. |
| `413` | The body is larger than 8 KiB. |
| `415` | The `Content-Type` is not `application/json`. |
| `503` | The database cannot be reached. |

## Running the API

```bash
export CLOUD_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/securewaste_cloud
export CLOUD_API_TOKENS="employee-token:employee"
python -m cloud_api
```

## Tests

The database tests need a reachable database; without `CLOUD_DATABASE_URL` they are skipped.

```bash
export CLOUD_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/securewaste_cloud
pytest cloud_api/tests
```
