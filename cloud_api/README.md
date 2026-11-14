# SecureWaste cloud API

The cloud side of SecureWaste receives **scan metadata only**: an event id, a timestamp, a
classification, a risk level and three counts. Document text, filenames, paths and matched
values never leave the local scanner (ADR-0006).

## Layout

| File | Purpose |
| --- | --- |
| `schema.sql` | The `scan_events` table and its indexes. The only place the DDL is written. |
| `db.py` | Connection handling, schema application, insert and read of one scan event. |
| `config.py` | Settings read from environment variables. |

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

The schema is applied automatically when the API starts (`db.apply_schema`) and by the test
fixture, so no manual migration step is needed. To apply it by hand instead:

```bash
podman exec -i sw-pg psql -U postgres -d securewaste_cloud < cloud_api/schema.sql
```

## Tests

The database tests need a reachable database; without `CLOUD_DATABASE_URL` they are skipped.

```bash
export CLOUD_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/securewaste_cloud
pytest cloud_api/tests
```
