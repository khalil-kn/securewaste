"""Usage: python scripts/issue_credential.py <employee_uuid> <role> [--ttl-days 30] [--allow-admin]

Prints the plaintext token ONCE (give it to the employee) and the entry to append
to CLOUD_API_CREDENTIALS. Never commit either.
"""

import argparse

from cloud_api.auth import DEFAULT_MAX_TTL_SECONDS, Role, new_credential


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("employee_uuid")
    ap.add_argument("role", choices=[r.value for r in Role])
    ap.add_argument("--ttl-days", type=int, default=30)
    ap.add_argument("--allow-admin", action="store_true", help="required for the admin role")
    args = ap.parse_args()

    if args.role == Role.ADMIN.value and not args.allow_admin:
        raise SystemExit("refusing to issue an admin credential without --allow-admin")
    ttl = args.ttl_days * 86400
    if ttl <= 0 or ttl > DEFAULT_MAX_TTL_SECONDS:
        raise SystemExit("ttl must be positive and not exceed the maximum token lifetime")

    token, entry = new_credential(args.role, args.employee_uuid, ttl)
    print(f"TOKEN (give to the employee, shown once): {token}")
    print(f"ENTRY (append to CLOUD_API_CREDENTIALS):  {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
