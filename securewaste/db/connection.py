"""SQLite connection handling: one connection per request, foreign keys always on.

SQLite ignores FOREIGN KEY / ON DELETE CASCADE unless `PRAGMA foreign_keys = ON` is run on every
new connection. Doing it here, once, means nobody can forget it.
"""

from __future__ import annotations

import sqlite3
from importlib import resources

import click
from flask import Flask, current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row  # rows behave like dicts: row["id"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to run twice (CREATE TABLE IF NOT EXISTS)."""
    schema = resources.files("securewaste.db").joinpath("schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)


@click.command("init-db")
def init_db_command() -> None:
    """flask --app securewaste init-db"""
    init_db()
    click.echo(f"Initialised the database at {current_app.config['DATABASE_PATH']}")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
