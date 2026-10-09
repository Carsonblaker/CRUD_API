# Reading List API

A multi-user REST API for keeping a reading list. Registered users add books they want to read, are reading, or have finished, and only the user who added a book can change or delete it. Each book can be matched against [Open Library](https://openlibrary.org/developers/api) to fill in its first publication year and page count.

## Getting started

**Requirements:** Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Carsonblaker/CRUD_API.git
cd CRUD_API
uv sync
```

**HTTPS certificate:** the server runs over HTTPS and expects `MyCertificate.crt` and `MyKey.pem` in the project folder. They are not in the repository. To generate a self-signed pair:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout MyKey.pem -out MyCertificate.crt -days 365 -subj "/CN=localhost"
```

**Run the server:**

```bash
uv run cs188-a3
```

The API is served at `https://127.0.0.1:5000`. Data is stored in `books.db`, which is created automatically. Because the certificate is self-signed, pass `-k` to curl.

**Run the tests:**

```bash
uv run pytest
```

Tests use a temporary database, never `books.db`. A few tests call the real Open Library API, so they need an internet connection.

**Environment variables:** none. Open Library does not require an API key.

## Authentication

Endpoints that create, change, or delete data require **HTTP Basic Auth** (`curl -u username:password`). Missing or invalid credentials return `401`. The message is the same for an unknown username and a wrong password.

All errors are JSON: `{"message": "..."}`.

## Endpoint reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/register` | No | Create a user |
| POST | `/books` | Yes | Add a book |
| GET | `/books` | No | List books, with filters |
| GET | `/books/{id}` | No | Get one book |
| PATCH | `/books/{id}` | Owner | Update some fields of a book |
| DELETE | `/books/{id}` | Owner | Delete a book |
| GET | `/books/{id}/openlibrary` | No | Preview the Open Library match for a book |
| PUT | `/books/{id}/openlibrary` | Owner | Save Open Library data onto a book |

### POST /register

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | Yes | 1–50 characters, not blank |
| `password` | string | Yes | At least 8 characters, at most 72 bytes |

- **201**: `{"id": 1, "username": "alice"}` (the password is never returned)
- **400**: missing, blank, or invalid fields, or a body that isn't a JSON object
- **409**: username already taken

### The book object

| Field | Type | Set by | Description |
|---|---|---|---|
| `id` | integer | Server | Book id |
| `owner_id` | integer | Server | Id of the user who added it |
| `created_at` | string | Server | UTC timestamp, ISO 8601 |
| `title` | string | Client | 1–200 characters |
| `author` | string | Client | 1–100 characters |
| `status` | string | Client | `want_to_read`, `reading`, or `finished` |
| `pages` | integer or null | Client / Open Library | 1–10000 |
| `rating` | integer or null | Client | 1–5 |
| `notes` | string or null | Client | Up to 1000 characters |
| `first_publish_year` | integer or null | Open Library | Filled by `PUT /books/{id}/openlibrary` |
| `ol_work_key` | string or null | Open Library | e.g. `/works/OL893415W` |

### POST /books (auth required)

Body: `title` and `author` (required), plus optional `status` (default `want_to_read`), `pages`, `rating`, and `notes`. Sending any server-set field, or any unknown field, returns 400.

- **201**: the new book, with a `Location: /books/{id}` header
- **400**: missing, invalid, unknown, or read-only fields
- **401**: missing or invalid credentials

### GET /books

| Query parameter | Type | Default | Description |
|---|---|---|---|
| `status` | string | (none) | Only books with this status |
| `author` | string | (none) | Case-insensitive partial match on author |
| `limit` | integer | 20 | How many books to return (1–100) |
| `offset` | integer | 0 | How many books to skip |

- **200**: a list of books, ordered by id
- **400**: invalid `status`, `limit`, or `offset`

### GET /books/{id}

- **200**: the book
- **404**: no book with that id

### PATCH /books/{id} (owner only)

Body: any subset of `title`, `author`, `status`, `pages`, `rating`, and `notes`. Only the fields sent are changed. `pages`, `rating`, and `notes` can be cleared with `null`.

- **200**: the updated book
- **400**: empty body, or invalid, unknown, or read-only fields
- **401**: missing or invalid credentials
- **403**: you don't own this book
- **404**: no book with that id

### DELETE /books/{id} (owner only)

- **204**: deleted, with no body
- **401**, **403**, **404**: as above

### GET /books/{id}/openlibrary

Searches Open Library for the book's title and author and returns the best match without saving anything: `ol_work_key`, `title`, `authors`, `first_publish_year`, `pages`, `description`, and `subjects`.

- **200**: the match
- **404**: no book with that id, or no match on Open Library
- **502**: Open Library is unreachable or returned an error

### PUT /books/{id}/openlibrary (owner only)

Saves `ol_work_key` and `first_publish_year` onto the book, and fills in `pages` if it was empty. No request body.

- **200**: the updated book
- **401**, **403**, **404**, **502**: as above

## Example session

```bash
# Register two users
$ curl -k -X POST https://127.0.0.1:5000/register -H "Content-Type: application/json" -d '{"username":"alice","password":"password123"}'
{"id": 1, "username": "alice"}

$ curl -k -X POST https://127.0.0.1:5000/register -H "Content-Type: application/json" -d '{"username":"bob","password":"password123"}'
{"id": 2, "username": "bob"}

# Alice adds a book
$ curl -k -u alice:password123 -X POST https://127.0.0.1:5000/books -H "Content-Type: application/json" -d '{"title":"Dune","author":"Frank Herbert"}'
{"id": 1, "owner_id": 1, "title": "Dune", "author": "Frank Herbert", "status": "want_to_read", "pages": null, "rating": null, "notes": null, "first_publish_year": null, "ol_work_key": null, "created_at": "2026-10-09T23:28:16+00:00"}

# Anyone can list books
$ curl -k "https://127.0.0.1:5000/books?author=herbert"
[{"id": 1, "owner_id": 1, "title": "Dune", ...}]

# Alice fills in details from Open Library
$ curl -k -u alice:password123 -X PUT https://127.0.0.1:5000/books/1/openlibrary
{"id": 1, ..., "pages": 604, "first_publish_year": 1965, "ol_work_key": "/works/OL893415W", ...}

# Bob tries to delete Alice's book
$ curl -k -i -u bob:password123 -X DELETE https://127.0.0.1:5000/books/1
HTTP/1.1 403 FORBIDDEN
Content-Type: application/json

{"message": "You do not own this book"}
```

## Resources and AI use

- [Flask](https://flask.palletsprojects.com/), [Flask-RESTful](https://flask-restful.readthedocs.io/), [Flask-Talisman](https://github.com/wntrblm/flask-talisman), and [Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/) documentation
- [Open Library Search API](https://openlibrary.org/dev/docs/api/search) and [Works API](https://openlibrary.org/dev/docs/api/books)
- [MDN HTTP status codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status)
- My API Activity code was the starting point for `Database`, `Register`, and `auth_required`.
- **AI use:** I used Claude (Anthropic's AI assistant) throughout this assignment. It helped me adapt my API Activity code and wrote most of the service layer, the books and Open Library endpoints, the test suite, the CI workflow, and a draft of this README. I reviewed, ran, and debugged the code myself. It also helped me fix git setup problems (an accidental repository in my home folder and a committed `.venv`).