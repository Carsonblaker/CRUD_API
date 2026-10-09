
import sqlite3
from contextlib import closing


class Database:
    """Wraps a SQLite connection and holds every SQL query the app runs."""

    def __init__(self, db_path: str) -> None:
        """Open the database at db_path and make sure the tables exist."""
        self.conn = sqlite3.connect(db_path)
        self.create_users_table()

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

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()