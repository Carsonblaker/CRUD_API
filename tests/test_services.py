"""Service-layer tests that don't use Flask at all."""

from pathlib import Path

import pytest

from cs188_a3 import services
from cs188_a3.db import Database


def test_password_is_hashed(tmp_path: Path) -> None:
    """The database stores a hash, not the real password."""
    db = Database(str(tmp_path / "test.db"))
    services.register_user(db, "carson", "password123")
    _, stored = db.get_user("carson")
    assert stored != "password123"


def test_non_owner_cannot_update(tmp_path: Path) -> None:
    """update_book raises Forbidden for someone who isn't the owner."""
    db = Database(str(tmp_path / "test.db"))
    owner = db.add_user("a", "hash")
    other = db.add_user("b", "hash")
    book = services.create_book(db, owner, {"title": "Dune", "author": "Frank Herbert"})
    with pytest.raises(services.Forbidden):
        services.update_book(db, other, book["id"], {"rating": 3})