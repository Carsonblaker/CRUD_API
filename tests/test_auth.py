"""Tests for registration and authentication."""

import pytest
from flask.testing import FlaskClient


def test_register_success(client: FlaskClient) -> None:
    """A new user gets 201, and the response never includes the password."""
    response = client.post("/register", json={"username": "carson", "password": "password123"})
    assert response.status_code == 201
    assert response.get_json() == {"id": 1, "username": "carson"}


def test_register_duplicate(client: FlaskClient) -> None:
    """A taken username gets 409."""
    body = {"username": "carson", "password": "password123"}
    client.post("/register", json=body)
    assert client.post("/register", json=body).status_code == 409


@pytest.mark.parametrize("body", [
    {"username": "carson"},                         # missing password
    {"username": "   ", "password": "password123"}, # blank username
    {"username": "carson", "password": "short"},    # password too short
    ["carson", "password123"],                      # a list, not an object
])
def test_register_bad_input(client: FlaskClient, body: object) -> None:
    """Bad registration input gets 400."""
    assert client.post("/register", json=body).status_code == 400


def test_login_required(client: FlaskClient, alice: tuple[str, str]) -> None:
    """No credentials or a wrong password gets 401."""
    book = {"title": "Dune", "author": "Frank Herbert"}
    assert client.post("/books", json=book).status_code == 401
    assert client.post("/books", json=book, auth=("alice", "wrongpassword")).status_code == 401