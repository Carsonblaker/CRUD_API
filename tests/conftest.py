"""Shared pytest fixtures: a fresh app per test, plus ready-made users and a book."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from cs188_a3.app import create_app

TEST_PASSWORD = "hunter2hunter2"


def register(client: FlaskClient, username: str) -> tuple[str, str]:
    """Register a user and return the (username, password) pair to pass as auth=."""
    client.post("/register", json={"username": username, "password": TEST_PASSWORD})
    return (username, TEST_PASSWORD)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[FlaskClient]:
    """A test client backed by an empty temporary database (never the real books.db)."""
    app = create_app(db_path=tmp_path / "test.db", force_https=False)
    app.testing = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def alice(client: FlaskClient) -> tuple[str, str]:
    """A registered user who owns the book fixture."""
    return register(client, "alice")


@pytest.fixture
def bob(client: FlaskClient) -> tuple[str, str]:
    """A second registered user who does not own alice's book."""
    return register(client, "bob")


@pytest.fixture
def book_id(client: FlaskClient, alice: tuple[str, str]) -> int:
    """Create a book owned by alice and return its id."""
    response = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}, auth=alice)
    return response.get_json()["id"]