"""Unit tests of credential parsing, rotation and the issue_credential script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from cloud_api.auth import AuthConfigError, Role, hash_token, new_credential, parse_credentials

NOW = 1_800_000_000
EMP = "11111111-1111-4111-8111-111111111111"
GOOD_HASH = "a" * 64
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "entry",
    [
        "plaintoken:employee",  # the old, insecure format
        f"{GOOD_HASH}:employee:{EMP}",  # missing expiry
        f"{GOOD_HASH}:employee:{EMP}:abc",  # bad expiry
        f"{'A' * 64}:employee:{EMP}:{NOW + 60}",  # hash must be lowercase hex
        f"{GOOD_HASH}:root:{EMP}:{NOW + 60}",  # unknown role
        f"{GOOD_HASH}:auditor:{EMP}:{NOW + 60}",  # removed role
        f"{GOOD_HASH}:employee:not-a-uuid:{NOW + 60}",  # bad uuid
        f"{GOOD_HASH}:employee::{NOW + 60}",  # missing uuid
    ],
)
def test_malformed_entries_fail_fast_without_echoing_them(entry):
    with pytest.raises(AuthConfigError) as error:
        parse_credentials(entry, now=NOW)
    assert GOOD_HASH not in str(error.value)


def test_duplicate_token_is_rejected():
    entry = f"{GOOD_HASH}:employee:{EMP}:{NOW + 60}"
    with pytest.raises(AuthConfigError):
        parse_credentials(f"{entry},{entry}", now=NOW)


def test_lifetime_above_the_cap_is_rejected():
    with pytest.raises(AuthConfigError):
        parse_credentials(f"{GOOD_HASH}:employee:{EMP}:{NOW + 10**9}", now=NOW, max_ttl_seconds=86400)


def test_an_already_expired_entry_is_skipped():
    assert parse_credentials(f"{GOOD_HASH}:employee:{EMP}:{NOW - 1}", now=NOW) == {}


def test_empty_configuration_means_no_credentials():
    assert parse_credentials("", now=NOW) == {}
    assert parse_credentials(None, now=NOW) == {}


def test_a_generated_entry_round_trips_and_never_contains_the_token():
    token, entry = new_credential("employee", EMP, 600, now=NOW)
    credential = parse_credentials(entry, now=NOW)[hash_token(token)]
    assert credential.employee_id == EMP and credential.role is Role.EMPLOYEE
    assert token.startswith("swt_") and token not in entry


def test_rotation_both_tokens_work_then_the_old_one_stops():
    old_token, old_entry = new_credential("employee", EMP, 3600, now=NOW)
    new_token, new_entry = new_credential("employee", EMP, 3600, now=NOW)
    overlap = parse_credentials(f"{old_entry},{new_entry}", now=NOW)
    assert hash_token(old_token) in overlap and hash_token(new_token) in overlap
    after_removal = parse_credentials(new_entry, now=NOW)
    assert hash_token(old_token) not in after_removal


def _run_script(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.run(  # noqa: S603
        [sys.executable, "scripts/issue_credential.py", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_script_issues_an_employee_credential():
    result = _run_script(EMP, "employee", "--ttl-days", "7")
    assert result.returncode == 0
    assert "TOKEN" in result.stdout and "ENTRY" in result.stdout


def test_script_refuses_admin_without_the_flag():
    assert _run_script(EMP, "admin").returncode != 0
    assert _run_script(EMP, "admin", "--allow-admin").returncode == 0


def test_script_refuses_a_lifetime_above_the_cap():
    assert _run_script(EMP, "employee", "--ttl-days", "365").returncode != 0
