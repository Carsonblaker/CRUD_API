"""Tests for the /books endpoints."""

import pytest
from flask.testing import FlaskClient

DUNE = {"title": "Dune", "author": "Frank Herbert"}


def test_create_book(client: FlaskClient, alice: tuple[str, str]) -> None:
    """Creating a book returns 201, a Location header, and a default status."""
    response = client.post("/books", json=DUNE, auth=alice)
    assert response.status_code == 201
    assert response.headers["Location"].endswith("/books/1")
    assert response.get_json()["status"] == "want_to_read"


@pytest.mark.parametrize("body", [
    {"title": "Dune"},           # missing author
    {**DUNE, "title": 123},      # number where text expected
    {**DUNE, "rating": 6},       # out of range
    {**DUNE, "id": 99},          # server-controlled field
])
def test_create_book_bad_input(client: FlaskClient, alice: tuple[str, str], body: object) -> None:
    """Invalid book data gets 400."""
    assert client.post("/books", json=body, auth=alice).status_code == 400


def test_list_and_filter(client: FlaskClient, alice: tuple[str, str]) -> None:
    """Listing returns every book, and ?status= filters them."""
    client.post("/books", json=DUNE, auth=alice)
    client.post("/books", json={"title": "Emma", "author": "Jane Austen", "status": "finished"}, auth=alice)
    assert len(client.get("/books").get_json()) == 2
    assert [b["title"] for b in client.get("/books?status=finished").get_json()] == ["Emma"]


def test_get_book(client: FlaskClient, book_id: int) -> None:
    """Anyone can read one book."""
    assert client.get(f"/books/{book_id}").status_code == 200


@pytest.mark.parametrize("bad_id", [999, -1, 2**63])
def test_get_missing_book(client: FlaskClient, bad_id: int) -> None:
    """Missing, negative, and huge ids all get 404."""
    assert client.get(f"/books/{bad_id}").status_code == 404


def test_patch_book(client: FlaskClient, alice: tuple[str, str], book_id: int) -> None:
    """PATCH changes only the fields sent."""
    book = client.patch(f"/books/{book_id}", json={"rating": 4}, auth=alice).get_json()
    assert book["rating"] == 4
    assert book["title"] == "Dune"


def test_only_owner_can_change(client: FlaskClient, bob: tuple[str, str], book_id: int) -> None:
    """Another user gets 403 when changing or deleting someone else's book."""
    assert client.patch(f"/books/{book_id}", json={"rating": 1}, auth=bob).status_code == 403
    assert client.delete(f"/books/{book_id}", auth=bob).status_code == 403


def test_delete_book(client: FlaskClient, alice: tuple[str, str], book_id: int) -> None:
    """The owner can delete a book, and then it's gone."""
    assert client.delete(f"/books/{book_id}", auth=alice).status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404