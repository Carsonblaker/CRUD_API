"""Client for the Open Library API: https://openlibrary.org/developers/api"""

from typing import Any

import requests

OPEN_LIBRARY_BASE_URL = "https://openlibrary.org"
SEARCH_FIELDS = "key,title,author_name,first_publish_year,number_of_pages_median"
REQUEST_TIMEOUT_SECONDS = 10
# Open Library asks apps to identify themselves with a User-Agent header
USER_AGENT = "cs188-a3-reading-list/0.1 (carson.blaker@drake.edu)"


class OpenLibraryError(Exception):
    """Raised when Open Library can't be reached or returns an unexpected response."""


def _get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET a JSON document from Open Library, raising OpenLibraryError on any failure."""
    try:
        response = requests.get(
            OPEN_LIBRARY_BASE_URL + path,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as err:  # network errors, bad status, bad JSON
        raise OpenLibraryError(str(err)) from err


def search_work(title: str, author: str) -> dict[str, Any] | None:
    """Return the best Open Library match for a title and author, or None if nothing matches."""
    data = _get_json(
        "/search.json",
        {"title": title, "author": author, "limit": 1, "fields": SEARCH_FIELDS},
    )
    docs = data.get("docs", [])
    return docs[0] if docs else None  # "no results" is a 200 with an empty docs list, not a 404


def get_work(work_key: str) -> dict[str, Any]:
    """Return details for one work, given a key like '/works/OL45804W'."""
    return _get_json(work_key + ".json")