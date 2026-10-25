# EX1 — Backend: Personal Book Vault & Reading Tracker

A REST API for tracking the books you own, what you've read, and how you rated them.
Built with FastAPI, SQLAlchemy 2.0 and SQLite, managed with uv, tested with pytest,
and packaged with Docker.

The project lives in [`book-vault/`](book-vault/). See its
[README](book-vault/README.md) for the full documentation: endpoints with curl
examples, setup, running the server and tests, and Docker.

## Quick start

```bash
git clone https://github.com/galamshalem/project.git
cd project/book-vault
uv sync
uv run uvicorn app.main:app --reload    # API docs at http://localhost:8000/docs
uv run pytest -v                        # run the tests
```

Or with Docker:

```bash
cd project/book-vault
docker build -t book-vault .
docker run -d --name book-vault -p 8000:8000 -v book-vault-data:/app/data book-vault
```
