"""SQLite access for the reading list API."""

import sqlite3
from contextlib import closing
from typing import Any

BOOK_FIELDS = (
    "id", "owner_id", "title", "author", "status", "pages",
    "rating", "notes", "first_publish_year", "ol_work_key", "created_at",
)
_SELECT_BOOKS = (
    "SELECT id, owner_id, title, author, status, pages, rating, notes, "
    "first_publish_year, ol_work_key, created_at FROM books"
)


class Database:
    """Wraps a SQLite connection and holds every SQL query the app runs."""

    def __init__(self, db_path: str) -> None:
        """Open the database at db_path and make sure the tables exist."""
        self.conn = sqlite3.connect(db_path)
        self.create_users_table()
        self.create_books_table()

    # ---------- Users ----------

    def create_users_table(self) -> None:
        """Create the users table if it doesn't exist yet."""
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )""")

    def add_user(self, username: str, hashed_pwd: str) -> int | None:
        """Insert a user and return their new id, or None if the username is taken."""
        try:
            with self.conn, closing(self.conn.cursor()) as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hashed_pwd),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user(self, username: str) -> tuple[int, str] | None:
        """Return (id, hashed password) for a username, or None if no such user."""
        with self.conn, closing(self.conn.cursor()) as cursor:
            return cursor.execute(
                "SELECT id, password FROM users WHERE username = ?",
                (username,),
            ).fetchone()

    # ---------- Books ----------

    def create_books_table(self) -> None:
        """Create the books table if it doesn't exist yet."""
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL,
                pages INTEGER,
                rating INTEGER,
                notes TEXT,
                first_publish_year INTEGER,
                ol_work_key TEXT,
                created_at TEXT NOT NULL
            )""")

    def add_book(self, owner_id: int, book: dict[str, Any], created_at: str) -> int:
        """Insert a book owned by owner_id and return its new id."""
        with self.conn, closing(self.conn.cursor()) as cursor:
            cursor.execute(
                "INSERT INTO books (owner_id, title, author, status, pages, rating, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (owner_id, book["title"], book["author"], book["status"],
                 book.get("pages"), book.get("rating"), book.get("notes"), created_at),
            )
            return cursor.lastrowid

    def get_book(self, book_id: int) -> dict[str, Any] | None:
        """Return one book as a dict, or None if it doesn't exist."""
        with self.conn, closing(self.conn.cursor()) as cursor:
            row = cursor.execute(_SELECT_BOOKS + " WHERE id = ?", (book_id,)).fetchone()
        return dict(zip(BOOK_FIELDS, row)) if row is not None else None

    def list_books(
        self, status: str | None, author: str | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        """Return books matching the optional status and author filters, by id."""
        author_pattern = "%" + author + "%" if author is not None else None  # partial match
        with self.conn, closing(self.conn.cursor()) as cursor:
            rows = cursor.execute(
                _SELECT_BOOKS
                + " WHERE (? IS NULL OR status = ?)"
                " AND (? IS NULL OR author LIKE ?)"
                " ORDER BY id LIMIT ? OFFSET ?",
                (status, status, author_pattern, author_pattern, limit, offset),
            ).fetchall()
        return [dict(zip(BOOK_FIELDS, row)) for row in rows]

    def update_book(self, book_id: int, book: dict[str, Any]) -> None:
        """Overwrite a book's editable fields with the values in book."""
        with self.conn:
            self.conn.execute(
                "UPDATE books SET title = ?, author = ?, status = ?, pages = ?, rating = ?, "
                "notes = ?, first_publish_year = ?, ol_work_key = ? WHERE id = ?",
                (book["title"], book["author"], book["status"], book["pages"], book["rating"],
                 book["notes"], book["first_publish_year"], book["ol_work_key"], book_id),
            )

    def delete_book(self, book_id: int) -> None:
        """Delete the book with the given id."""
        with self.conn:
            self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()