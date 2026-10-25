# CLAUDE.md

Personal Book Vault & Reading Tracker: a FastAPI + SQLAlchemy 2.0 + SQLite REST API,
managed with uv. All commands below run from the `book-vault/` directory.

## Commands

```bash
uv sync                                   # install runtime + dev deps from uv.lock
uv add <pkg>                              # add a runtime dependency
uv add --dev <pkg>                        # add a dev dependency
uv run uvicorn app.main:app --reload      # run the dev server (docs at /docs)
uv run pytest -v                          # run the tests
uv run pytest tests/test_main.py::test_name -v   # run a single test
uv run ruff check .                       # lint
uv run ruff format .                      # format
docker build -t book-vault .              # build the image
docker run -d --name book-vault -p 8000:8000 -v book-vault-data:/app/data book-vault
```

Never edit `uv.lock` by hand. Change dependencies with `uv add` / `uv remove`.

## Layout

```
app/
  main.py       FastAPI app, lifespan (creates tables), all endpoints
  database.py   DATABASE_URL (default sqlite:///./data/books.db), engine, SessionLocal, Base, get_db
  models.py     SQLAlchemy ORM models (typed Mapped[...] style)
  schemas.py    Pydantic v2 schemas: Genre enum, BookCreate, BookUpdate, BookRead
tests/
  conftest.py   `client` fixture: fresh in-memory SQLite (StaticPool) per test via dependency_overrides
  test_main.py  API tests, grouped by CRUD / filters / validation / 404 / persistence
data/           runtime SQLite file (gitignored, also the Docker volume at /app/data)
```

## Conventions

- **Schemas vs models.** `models.py` describes how data is stored. `schemas.py`
  describes the API contract. Endpoints take schemas as input and return ORM objects
  with `response_model=` set to a schema, never raw dicts. Put validation in the
  schemas, not in the endpoints.
- **Database access goes through `get_db`.** Endpoints take `db: Session = Depends(get_db)`.
  Never create a `SessionLocal()` directly in app code. This is what lets the tests
  swap in an in-memory database.
- **Type hints everywhere.** Annotate all function parameters and return types. Use
  SQLAlchemy 2.0 `Mapped[...]` / `mapped_column` and modern syntax (`X | None`, `list[X]`).
- **Updates are partial.** `PUT` applies `payload.model_dump(exclude_unset=True)` so
  that omitted fields are left alone. New optional fields on `BookUpdate` must
  follow the same pattern. If a new column is NOT NULL, add it to the explicit-null
  check in `BookUpdate`.
- **Errors.** Use `get_book_or_404()` for id lookups, so the 404 message is always
  `BOOK_NOT_FOUND`. Every `/books/{book_id}` route declares
  `responses=NOT_FOUND_RESPONSE` so the 404 is documented in OpenAPI, and
  `test_404_documented_in_openapi` checks this. Leave validation errors to FastAPI's
  default `422` response.
- **Tests are required.** Every new endpoint needs tests for success, validation
  (`422`) and not-found (`404`) cases. Use the `client` fixture and never point tests
  at `./data/books.db`.
- **Before finishing any change**, run these and make sure both pass:
  ```bash
  uv run pytest -v
  uv run ruff check .
  ```
