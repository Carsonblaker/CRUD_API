
from functools import wraps
from typing import Any, Callable

from flask import current_app, g, request
from flask_restful import Resource

from cs188_a3 import services
from cs188_a3.db import Database


def get_db() -> Database:
    """Return this request's database connection, opening it on first use."""
    if "db" not in g:
        g.db = Database(current_app.config["DATABASE"])
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    """Close the database connection at the end of a request, if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_json_object() -> dict[str, Any] | None:
    """Return the request body if it is a JSON object, otherwise None."""
    body = request.get_json(silent=True)  # silent=True: return None instead of erroring on bad JSON
    return body if isinstance(body, dict) else None


def auth_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Require HTTP Basic Auth and store the caller's id in g.user_id."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        auth = request.authorization
        if auth is None or not auth.username or not auth.password:
            return {"message": "Authentication required"}, 401
        user_id = services.authenticate(get_db(), auth.username, auth.password)
        if user_id is None:
            return {"message": "Invalid credentials"}, 401
        g.user_id = user_id
        return func(*args, **kwargs)

    return wrapper


class Register(Resource):
    """POST /register: create a new user account."""

    def post(self) -> tuple[dict[str, Any], int]:
        """Register a user from a JSON body containing username and password."""
        body = get_json_object()
        if body is None:
            return {"message": "Request body must be a JSON object"}, 400
        try:
            user = services.register_user(get_db(), body.get("username"), body.get("password"))
        except services.ValidationError as err:
            return {"message": str(err)}, 400
        except services.UsernameTaken:
            return {"message": "Username is already taken"}, 409
        return user, 201