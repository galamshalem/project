# Verification evidence: Personal Book Vault & Reading Tracker

All evidence below was produced on 2026-10-25. Text files contain the exact commands
that were run together with their full, unedited output. Screenshots were taken with
Playwright driving Google Chrome against the running server, at a 1400×900 viewport.

| # | Evidence | What it shows |
|---|----------|---------------|
| 01 | [01-ruff.txt](01-ruff.txt) | `uv sync` + `ruff check` on a fresh clone |
| 02 | [02-pytest.txt](02-pytest.txt), [02-pytest.png](02-pytest.png) | Full test run on a fresh clone: 40 passed |
| 03 | [03-coverage.txt](03-coverage.txt), [03-coverage.png](03-coverage.png) | Test coverage: 96% |
| 04 | [04-api-demo.txt](04-api-demo.txt) | Live curl session against the server, including a restart |
| 05–09 | Swagger UI screenshots | Interactive docs, with real requests executed |
| 10 | [10-docker.txt](10-docker.txt) | Docker build, run, restart and persistence |

## FastAPI

The API is a FastAPI app exposing five REST endpoints, with interactive OpenAPI docs
generated automatically at `/docs`.

![Swagger UI overview](05-swagger-overview.png)

## Pydantic validation

Pydantic v2 schemas reject bad input with FastAPI's standard `422` response. The
checks cover ratings outside 1–5, empty or whitespace-only titles and authors, unknown
genres, and missing fields. The demo shows rating 6 and an empty title both returning
`422` (steps 10–11 in [04-api-demo.txt](04-api-demo.txt)). The 404 screenshot shows a
missing id returning `{"detail": "Book not found"}`.

![422 for rating 6 in Swagger UI](08-swagger-422.png)

![404 for a missing book in Swagger UI](09-swagger-404.png)

## CRUD

Books can be created (`201`), listed, fetched by id, partially updated with `PUT`
(only the fields sent are changed), and deleted (`204`, after which `GET` returns
`404`). See steps 1–3, 8–9 and 13–14 in [04-api-demo.txt](04-api-demo.txt).

![POST /books returning 201 in Swagger UI](06-swagger-post.png)

## Filters

`GET /books` accepts `genre`, `is_read` and `min_rating` filters, which can be combined.
Unrated books are excluded when `min_rating` is set. See steps 5–7 in
[04-api-demo.txt](04-api-demo.txt); the combined filters are covered by the tests.

![GET /books?genre=Sci-Fi in Swagger UI](07-swagger-get-filter.png)

## SQLite persistence

Data is stored in a SQLite file. In the demo, the server was stopped and started
again on the same file, and the books were still there, including the `PUT` changes
and with the deleted book still gone (step 15 in [04-api-demo.txt](04-api-demo.txt)).
The test suite also checks persistence by rebuilding the database engine on a
temporary file.

## Tests

The suite has 40 pytest tests, each with an isolated in-memory database. They cover
CRUD, every filter and filter combinations, validation `422`s, `404`s, and
persistence. On a fresh clone of the repository, all 40 pass, and ruff reports no
issues ([01-ruff.txt](01-ruff.txt), [02-pytest.txt](02-pytest.txt)).

![pytest output: 40 passed](02-pytest.png)

## Coverage

Coverage is 96% overall, and 100% for `main.py`, `models.py` and `schemas.py`
([03-coverage.txt](03-coverage.txt)). The only lines not covered are in
`database.py`: the code that creates `./data` and the production `get_db`. The tests
deliberately replace both with an isolated test database.

![HTML coverage report](03-coverage.png)

## Docker

The multi-stage image builds with uv and runs as a non-root user (`uid=999(app)`).
Books created in the container were still there after `docker restart`, and also
after the container was deleted and a new one started on the same named volume
([10-docker.txt](10-docker.txt)).

## Documentation

The [README](../../README.md) documents every endpoint with curl examples, along
with setup, running the server and tests, and Docker. [CLAUDE.md](../../CLAUDE.md)
lists the development commands and the project's conventions.
