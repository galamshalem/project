# Personal Book Vault & Reading Tracker

A REST API for keeping track of the books you own: what genre they are, whether
you've read them, how you rated them, and what you thought.

Built with **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0** and **SQLite**, managed
with **uv**, tested with **pytest**, and shipped as a **Docker** image.

## Features

- Full CRUD for books (`/books`)
- Filter the list by `genre`, `is_read` and `min_rating` (filters can be combined)
- Input validation with clear `422` errors:
  - `title` and `author` are required and can't be empty or whitespace-only
  - `genre` must be one of: `Fantasy`, `Romance`, `Sci-Fi`, `Thriller`, `Non-Fiction`,
    `Mystery`, `Historical`
  - `rating` is optional, but if given must be an integer from 1 to 5
- Partial updates: `PUT` changes only the fields you send
- A rating and review are allowed even if the book isn't marked as read
- Data is stored in a SQLite file and survives restarts

## Data model

| Field        | Type            | Notes                                          |
|--------------|-----------------|------------------------------------------------|
| `id`         | integer         | Generated                                      |
| `title`      | string          | Required, non-empty (surrounding spaces trimmed) |
| `author`     | string          | Required, non-empty (surrounding spaces trimmed) |
| `genre`      | enum            | Required, one of the genres above              |
| `rating`     | integer \| null | 1–5, optional                                  |
| `is_read`    | boolean         | Defaults to `false`                            |
| `review`     | string \| null  | Optional                                       |
| `created_at` | datetime        | Set on creation (UTC)                          |
| `updated_at` | datetime        | Refreshed on every update (UTC)                |

## Endpoints

| Method   | Path               | Description                       | Success | Errors     |
|----------|--------------------|-----------------------------------|---------|------------|
| `POST`   | `/books`           | Create a book                     | `201`   | `422`      |
| `GET`    | `/books`           | List books (optional filters)     | `200`   | `422`      |
| `GET`    | `/books/{book_id}` | Get one book                      | `200`   | `404`      |
| `PUT`    | `/books/{book_id}` | Partially update a book           | `200`   | `404`, `422` |
| `DELETE` | `/books/{book_id}` | Delete a book                     | `204`   | `404`      |

### Examples

The examples assume the server is running on `http://localhost:8000`.

**Create a book**

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi", "rating": 5, "is_read": true, "review": "A classic."}'
```

```json
{"title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi", "rating": 5, "is_read": true,
 "review": "A classic.", "id": 1, "created_at": "2026-10-25T18:20:37.632554",
 "updated_at": "2026-10-25T18:20:37.632561"}
```

**List books, with optional filters**

```bash
curl http://localhost:8000/books
curl "http://localhost:8000/books?genre=Fantasy"
curl "http://localhost:8000/books?is_read=false"
curl "http://localhost:8000/books?min_rating=4"          # unrated books are excluded
curl "http://localhost:8000/books?genre=Sci-Fi&is_read=true&min_rating=4"
```

**Get one book**

```bash
curl http://localhost:8000/books/1
```

**Update a book** (only the fields you send are changed)

```bash
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"rating": 4, "review": "Even better the second time."}'
```

Send `null` for `rating` or `review` to clear them. `title`, `author`, `genre` and
`is_read` can be left out but can't be set to `null`.

**Delete a book**

```bash
curl -X DELETE http://localhost:8000/books/1      # 204 No Content
```

**Errors**

```bash
curl http://localhost:8000/books/999
# 404 {"detail": "Book not found"}

curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "   ", "author": "X", "genre": "Horror", "rating": 6}'
# 422 with one entry per invalid field (title, genre, rating)
```

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.11 for you if needed).

```bash
cd book-vault
uv sync            # creates .venv and installs runtime + dev dependencies from uv.lock
```

## Running the server

```bash
uv run uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs (Swagger UI): <http://localhost:8000/docs>
- Alternative docs (ReDoc): <http://localhost:8000/redoc>

The database is created automatically at `./data/books.db`. To use a different
location, set `DATABASE_URL`:

```bash
DATABASE_URL=sqlite:///./my-books.db uv run uvicorn app.main:app --reload
```

## Running the tests

```bash
uv run pytest -v
```

Each test runs against its own fresh in-memory database, so tests never touch
`./data/books.db`. The suite covers CRUD, every filter and filter combinations,
validation errors, 404s, and persistence across an engine restart.

Lint and format checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

## Docker

Build the image:

```bash
docker build -t book-vault .
```

Run it with a named volume so the database survives container restarts and removal:

```bash
docker run -d --name book-vault -p 8000:8000 -v book-vault-data:/app/data book-vault
```

Then open <http://localhost:8000/docs>. Useful follow-ups:

```bash
docker logs -f book-vault                 # view server logs
docker rm -f book-vault                   # remove the container (data stays in the volume)
docker volume rm book-vault-data          # delete the data for good
```

The image is a multi-stage build: dependencies are installed with uv in a builder
stage, and the runtime stage is `python:3.11-slim` running as a non-root user.

## Project structure

```
book-vault/
├── app/
│   ├── main.py        # FastAPI app and endpoints
│   ├── database.py    # engine, session factory, get_db dependency
│   ├── models.py      # SQLAlchemy ORM models (storage)
│   └── schemas.py     # Pydantic schemas (API request/response contract)
├── tests/
│   ├── conftest.py    # in-memory test DB fixture
│   └── test_main.py   # API tests
├── data/              # SQLite database (created at runtime, gitignored)
├── pyproject.toml     # dependencies and tool config
├── uv.lock            # locked dependency versions
├── Dockerfile
└── .dockerignore
```
