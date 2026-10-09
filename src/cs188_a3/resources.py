"""HTTP layer: Flask-RESTful resources, request parsing, and authentication."""

from functools import wraps
from typing import Any, Callable

from flask import current_app, g, request
from flask_restful import Resource

from cs188_a3 import services
from cs188_a3.db import Database

ApiResponse = tuple[Any, ...]  # (body, status) or (body, status, headers)


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

    def post(self) -> ApiResponse:
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


class BookList(Resource):
    """/books: list books (anyone) or create one (authenticated)."""

    def get(self) -> ApiResponse:
        """List books, filtered by optional status/author and paged by limit/offset."""
        try:
            books = services.list_books(
                get_db(),
                request.args.get("status"),
                request.args.get("author"),
                request.args.get("limit"),
                request.args.get("offset"),
            )
        except services.ValidationError as err:
            return {"message": str(err)}, 400
        return books, 200

    @auth_required
    def post(self) -> ApiResponse:
        """Create a book owned by the caller, with a Location header pointing at it."""
        body = get_json_object()
        if body is None:
            return {"message": "Request body must be a JSON object"}, 400
        try:
            book = services.create_book(get_db(), g.user_id, body)
        except services.ValidationError as err:
            return {"message": str(err)}, 400
        return book, 201, {"Location": f"/books/{book['id']}"}


class BookDetail(Resource):
    """/books/<id>: read, update, or delete one book."""

    def get(self, book_id: int) -> ApiResponse:
        """Return one book."""
        try:
            return services.get_book(get_db(), book_id), 200
        except services.NotFound:
            return {"message": "Book not found"}, 404

    @auth_required
    def patch(self, book_id: int) -> ApiResponse:
        """Update only the fields present in the body, if the caller owns the book."""
        changes = get_json_object()
        if changes is None:
            return {"message": "Request body must be a JSON object"}, 400
        try:
            book = services.update_book(get_db(), g.user_id, book_id, changes)
        except services.NotFound:
            return {"message": "Book not found"}, 404
        except services.Forbidden:
            return {"message": "You do not own this book"}, 403
        except services.ValidationError as err:
            return {"message": str(err)}, 400
        return book, 200

    @auth_required
    def delete(self, book_id: int) -> ApiResponse:
        """Delete the book, if the caller owns it."""
        try:
            services.delete_book(get_db(), g.user_id, book_id)
        except services.NotFound:
            return {"message": "Book not found"}, 404
        except services.Forbidden:
            return {"message": "You do not own this book"}, 403
        return "", 204

class BookOpenLibrary(Resource):
    """/books/<id>/openlibrary: preview (GET) or save (PUT) Open Library data for a book."""

    def get(self, book_id: int) -> ApiResponse:
        """Return the best Open Library match for this book without changing it."""
        try:
            return services.find_open_library_match(get_db(), book_id), 200
        except services.NotFound:
            return {"message": "Book not found"}, 404
        except services.NoOpenLibraryMatch:
            return {"message": "No match found on Open Library"}, 404
        except services.ExternalServiceError:
            return {"message": "Open Library is unavailable; try again later"}, 502

    @auth_required
    def put(self, book_id: int) -> ApiResponse:
        """Save the Open Library match onto the book, if the caller owns it."""
        try:
            return services.apply_open_library_match(get_db(), g.user_id, book_id), 200
        except services.NotFound:
            return {"message": "Book not found"}, 404
        except services.Forbidden:
            return {"message": "You do not own this book"}, 403
        except services.NoOpenLibraryMatch:
            return {"message": "No match found on Open Library"}, 404
        except services.ExternalServiceError:
            return {"message": "Open Library is unavailable; try again later"}, 502