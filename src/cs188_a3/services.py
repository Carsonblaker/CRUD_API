from flask_bcrypt import Bcrypt

from cs188_a3.db import Database

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt can only hash the first 72 bytes of a password
MAX_USERNAME_LENGTH = 50

_bcrypt = Bcrypt()


class ValidationError(Exception):
    """Raised when request data is missing or invalid."""


class UsernameTaken(Exception):
    """Raised when registering a username that already exists."""


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