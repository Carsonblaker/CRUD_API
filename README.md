### POST /books  (auth required)
Creates a book owned by the caller.
Body (JSON):
- title (string, required) — 1–200 chars
- author (string, required) — 1–100 chars
- status (string, optional) — want_to_read | reading | finished; default want_to_read
...
Success: 201, returns the book; Location: /books/<id>
Errors: 400 invalid body, 401 bad/missing credentials