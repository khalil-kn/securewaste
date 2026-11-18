# Cloud API migrations (SCRUM-45)

Numbered SQL files for the SecureWaste cloud metadata API. Apply in order with `psql`.

## Files

- `000_schema_migrations.sql` — creates the `schema_migrations` tracking table.
- `001_scrum45_employee_and_nullable_risk.sql` — makes `risk` nullable and adds `employee_id`.

## Apply (fresh or existing database)

```bash
psql "$CLOUD_DATABASE_URL" -f cloud_api/migrations/000_schema_migrations.sql
psql "$CLOUD_DATABASE_URL" -f cloud_api/migrations/001_scrum45_employee_and_nullable_risk.sql
```

For a brand-new database, `cloud_api/schema.sql` already reflects the post-migration state;
running the migrations on top of it is a no-op.

## Rollback

These migrations are not automatically reversible. Take a backup first:

```bash
pg_dump "$CLOUD_DATABASE_URL" > securewaste_cloud_backup.sql
```

Restore from the backup to roll back. Historic rows keep their `risk` value and receive
`employee_id = NULL` (unattributed) — never fabricate ownership.