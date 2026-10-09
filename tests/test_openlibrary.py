"""Tests for the Open Library lookup."""

import pytest
import requests
from flask.testing import FlaskClient

from cs188_a3 import openlibrary

FAKE_MATCH = {"key": "/works/OL1W", "first_publish_year": 1965, "number_of_pages_median": 412}


def test_search_real_api() -> None:
    """Our search code works against the real Open Library API."""
    match = openlibrary.search_work("Dune", "Frank Herbert")
    assert match is not None
    assert match["key"].startswith("/works/")


def test_put_saves_match(
    client: FlaskClient, alice: tuple[str, str], book_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET previews the match, and PUT saves it onto the book (network calls are faked)."""
    monkeypatch.setattr(openlibrary, "search_work", lambda title, author: FAKE_MATCH)
    monkeypatch.setattr(openlibrary, "get_work", lambda key: {})
    assert client.get(f"/books/{book_id}/openlibrary").status_code == 200
    book = client.put(f"/books/{book_id}/openlibrary", auth=alice).get_json()
    assert book["first_publish_year"] == 1965


def test_outage_returns_502(client: FlaskClient, book_id: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """If Open Library is unreachable, the API returns 502 instead of crashing."""
    def broken_get(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(openlibrary.requests, "get", broken_get)
    assert client.get(f"/books/{book_id}/openlibrary").status_code == 502