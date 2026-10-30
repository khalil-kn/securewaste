from flask import Flask
from flask_wtf.csrf import CSRFProtect

from web.routes_documents import documents_bp

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "web" / "templates")
)

# Security configuration
app.config["SECRET_KEY"] = "change-this-secret-key-before-production"

# Allow multipart overhead; upload.py enforces the exact 10 MB file limit.
app.config["MAX_CONTENT_LENGTH"] = 11 * 1024 * 1024

# Enable CSRF protection
csrf = CSRFProtect(app)

# Register document routes
app.register_blueprint(documents_bp)


@app.route("/")
def home():
    return "Secure Waste is running!"


if __name__ == "__main__":
    app.run(debug=True)