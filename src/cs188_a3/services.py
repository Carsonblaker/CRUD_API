"""Service layer: the actual work of the reading list API, kept separate from HTTP."""

from datetime import datetime, timezone
from typing import Any

from flask_bcrypt import Bcrypt

from cs188_a3.db import Database

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt can only hash the first 72 bytes of a password
MAX_USERNAME_LENGTH = 50

BOOK_STATUSES = ("want_to_read", "reading", "finished")
EDITABLE_FIELDS = {"title", "author", "status", "pages", "rating", "notes"}
MAX_TITLE_LENGTH = 200
MAX_AUTHOR_LENGTH = 100
MAX_NOTES_LENGTH = 1000
MAX_PAGES = 10000
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_SQLITE_ID = 2**63 - 1  # SQLite integers can't be bigger than this

_bcrypt = Bcrypt()


class ValidationError(Exception):
    """Raised when request data is missing or invalid."""


class UsernameTaken(Exception):
    """Raised when registering a username that already exists."""


class NotFound(Exception):
    """Raised when a requested record does not exist."""


class Forbidden(Exception):
    """Raised when a user tries to change a record they don't own."""


# ---------- Users ----------

def register_user(db: Database, username: object, password: object) -> dict[str, int | str]:
    """Validate input, store a new user with a hashed password, and return their public info.

    Raises ValidationError for bad input and UsernameTaken if the username exists.
    """
    if not isinstance(username, str) or not username.strip():
        raise ValidationError("username is required and must be a non-blank string")
    username = username.strip()
    if len(username) > MAX_USERNAME_LENGTH:
        raise ValidationError(f"username must be at most {MAX_USERNAME_LENGTH} characters")
    if not isinstance(password, str) or not password.strip():
        raise ValidationError("password is required and must be a non-blank string")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValidationError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")

    hashed = _bcrypt.generate_password_hash(password).decode("utf-8")
    user_id = db.add_user(username, hashed)
    if user_id is None:
        raise UsernameTaken()
    return {"id": user_id, "username": username}  # never include the hash


def authenticate(db: Database, username: str, password: str) -> int | None:
    """Return the user's id if the username and password match, otherwise None."""
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return None
    user = db.get_user(username)
    if user is None:
        return None
    user_id, hashed = user
    if not _bcrypt.check_password_hash(hashed, password):
        return None
    return user_id


# ---------- Books ----------

def _check_text(name: str, value: object, max_length: int) -> str:
    """Return value stripped if it is a non-blank string within max_length."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-blank string")
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(f"{name} must be at most {max_length} characters")
    return value


def _check_int(name: str, value: object, low: int, high: int) -> int:
    """Return value if it is an integer between low and high (inclusive)."""
    # bool is a subclass of int in Python, so reject True/False explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValidationError(f"{name} must be between {low} and {high}")
    return value


def _validate_book_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Validate every field present in data and return the cleaned values."""
    unknown = set(data) - EDITABLE_FIELDS
    if unknown:
        raise ValidationError("unknown or read-only field(s): " + ", ".join(sorted(unknown)))
    cleaned: dict[str, Any] = {}
    for field, value in data.items():
        if field == "title":
            cleaned[field] = _check_text("title", value, MAX_TITLE_LENGTH)
        elif field == "author":
            cleaned[field] = _check_text("author", value, MAX_AUTHOR_LENGTH)
        elif field == "status":
            if value not in BOOK_STATUSES:
                raise ValidationError("status must be one of: " + ", ".join(BOOK_STATUSES))
            cleaned[field] = value
        elif value is None:
            cleaned[field] = None  # optional fields can be cleared with null
        elif field == "pages":
            cleaned[field] = _check_int("pages", value, 1, MAX_PAGES)
        elif field == "rating":
            cleaned[field] = _check_int("rating", value, 1, 5)
        elif field == "notes":
            cleaned[field] = _check_text("notes", value, MAX_NOTES_LENGTH)
    return cleaned


def _parse_query_int(name: str, raw: str | None, default: int, low: int, high: int) -> int:
    """Convert a query-string value to an int in range, or use default if absent."""
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValidationError(f"{name} must be between {low} and {high}")
    return value


def get_book(db: Database, book_id: int) -> dict[str, Any]:
    """Return one book, or raise NotFound if it doesn't exist."""
    if not 1 <= book_id <= MAX_SQLITE_ID:
        raise NotFound()
    book = db.get_book(book_id)
    if book is None:
        raise NotFound()
    return book


def list_books(
    db: Database, status: str | None, author: str | None, limit: str | None, offset: str | None
) -> list[dict[str, Any]]:
    """Return books filtered by optional status and author, with limit/offset paging."""
    if status is not None and status not in BOOK_STATUSES:
        raise ValidationError("status must be one of: " + ", ".join(BOOK_STATUSES))
    limit_value = _parse_query_int("limit", limit, DEFAULT_LIMIT, 1, MAX_LIMIT)
    offset_value = _parse_query_int("offset", offset, 0, 0, MAX_SQLITE_ID)
    return db.list_books(status, author, limit_value, offset_value)


def create_book(db: Database, owner_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Validate data, store a new book owned by owner_id, and return it."""
    cleaned = _validate_book_fields(data)
    missing = [field for field in ("title", "author") if field not in cleaned]
    if missing:
        raise ValidationError("missing required field(s): " + ", ".join(missing))
    cleaned.setdefault("status", "want_to_read")
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    book_id = db.add_book(owner_id, cleaned, created_at)
    return get_book(db, book_id)


def update_book(db: Database, user_id: int, book_id: int, changes: dict[str, Any]) -> dict[str, Any]:
    """Apply only the given changes to a book the user owns, and return the updated book."""
    book = get_book(db, book_id)
    if book["owner_id"] != user_id:
        raise Forbidden()
    cleaned = _validate_book_fields(changes)
    if not cleaned:
        raise ValidationError("request body must include at least one field to change")
    book.update(cleaned)  # merge the changes into the existing book
    db.update_book(book_id, book)
    return book


def delete_book(db: Database, user_id: int, book_id: int) -> None:
    """Delete a book the user owns."""
    book = get_book(db, book_id)
    if book["owner_id"] != user_id:
        raise Forbidden()
    db.delete_book(book_id)