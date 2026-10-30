"""SecureWaste application factory.

`flask --app securewaste run` calls create_app(). Tests call create_app(test_config) to get a fresh
app with a temporary database — that is why we use a factory instead of a global `app = Flask(...)`.
"""

from __future__ import annotations

from flask import Flask

from securewaste.config import load_config


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True, template_folder="web/templates", static_folder="web/static")
    app.config.update(load_config(app.instance_path))
    if test_config:
        app.config.update(test_config)

    # Runtime folders live under instance/ (git-ignored), never inside the static web folder (FR-05).
    for sub in ("originals", "sanitized", "tmp"):
        (app.config["STORAGE_DIR"] / sub).mkdir(parents=True, exist_ok=True)

    # Build upload limits from config
    app.config["UPLOAD_LIMITS"] = {
        "max_bytes": app.config["MAX_CONTENT_LENGTH"],
        "max_pdf_pages": app.config["MAX_PDF_PAGES"],
        "max_extracted_chars": app.config["MAX_EXTRACTED_CHARS"],
    }

    # Detection rules will be populated by Milestone 1 issue #5; empty list for now
    app.config["DETECTION_RULES"] = []

    from securewaste.db import connection
    from securewaste.web import routes_api, routes_dashboard, routes_documents, security

    security.init_app(app)
    connection.init_app(app)
    # One blueprint per file: teammates add routes in their own file without touching this one.
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_documents.bp)
    app.register_blueprint(routes_api.bp)
    return app
