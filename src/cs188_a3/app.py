"""App wiring: build the Flask app, register endpoints, and run it over HTTPS."""

from pathlib import Path

from flask import Flask
from flask_restful import Api
from flask_talisman import Talisman

from cs188_a3.resources import BookDetail, BookList, Register, close_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/cs188_a3/app.py -> project folder
CERTIFICATE_PATH = PROJECT_ROOT / "MyCertificate.crt"
KEYFILE_PATH = PROJECT_ROOT / "MyKey.pem"
DEFAULT_DB_PATH = PROJECT_ROOT / "books.db"
PORT = 5000


def init_api(app: Flask) -> None:
    """Register every API endpoint on the app."""
    api = Api(app)
    api.add_resource(Register, "/register")
    api.add_resource(BookList, "/books")
    api.add_resource(BookDetail, "/books/<int(signed=True):book_id>")


def create_app(db_path: str | Path = DEFAULT_DB_PATH) -> Flask:
    """Build and configure the Flask app, using the SQLite database at db_path."""
    app = Flask(__name__)
    app.config["DATABASE"] = str(db_path)
    Talisman(app)  # redirects HTTP to HTTPS and adds security headers
    app.teardown_appcontext(close_db)  # close the DB connection after every request
    init_api(app)
    return app


def run_app() -> None:
    """Start the development server over HTTPS using the project's certificate."""
    app = create_app()
    app.run(port=PORT, ssl_context=(str(CERTIFICATE_PATH), str(KEYFILE_PATH)))