# Authenticating the sync client against the cloud API

Applies to the cloud API (`cloud_api`), SCRUM-29. Audience: the sync client (SCRUM-30).

## Credentials
- Every employee has a **personal** bearer token that starts with `swt_`. There is no shared token.
- An admin issues it with `python scripts/issue_credential.py <employee_uuid> <role> --ttl-days N`.
  The token is shown once. The server stores only its SHA-256 hash, so a lost token cannot be
  recovered and a new one must be issued.
- Tokens expire. The default lifetime is 30 days, and the server rejects anything over 90 days.

## Every request
```
Authorization: Bearer swt_xxxxxxxx
```
- Send the header on every call to `/api/v1/...`.
- `GET /health` needs no token.

## Endpoints
| Method and path | Who may call it |
|---|---|
| `POST /api/v1/scans` | employee, admin |
| `GET /api/v1/scans/<event_id>` | the owner of the event, or security_officer / admin |

## Rules for the client
1. **Do not send `employee_id`.** The server takes the owner from the token. A body that contains
   `employee_id` is rejected with 400.
2. Send only the contract keys: `event_id`, `timestamp`, `classification`, `risk`, `counts`.
3. Read the token from config or an environment variable (for example `SECUREWASTE_API_TOKEN`).
   Never put it in source code, the repository, a URL or a log. Redact the `Authorization`
   header in client logs.
4. Do not cache API responses.

## Handling responses
| Status | Meaning | Client action |
|---|---|---|
| 201 | Event stored | Mark as synced |
| 409 | `event_id` already stored | Treat as already synced |
| 400 | Payload does not match the contract (details are in the response) | Do not retry unchanged. Fix the payload. |
| 401 | Token missing, unknown or expired (same message for all three) | Stop and ask for a new token. There is no refresh endpoint. |
| 403 | Authenticated, but this role or employee is not allowed | Do not retry. Report it. |
| 503 | Database not reachable | Retry later with backoff |

## Rotation
1. The admin issues a second token for the same employee.
2. Deploy the new token to the client.
3. The admin removes the old entry from `CLOUD_API_CREDENTIALS` and redeploys the server.

Both tokens work during the overlap.

## Roles
- **employee:** create scans and read their own.
- **security_officer:** read all scans and the audit log. Cannot create scans.
- **admin:** create scans, read all, manage users. Cannot read the audit log.

## Server configuration (for operators)
`CLOUD_API_CREDENTIALS` is a comma-separated list of
`<sha256_hex>:<role>:<employee_uuid>:<expires_at_epoch_seconds>`.
The server refuses to start if any entry is malformed.