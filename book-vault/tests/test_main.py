"""API tests for the Book Vault: CRUD, filters, validation, 404s and persistence."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import DEFAULT_DATABASE_URL, Base, ensure_sqlite_dir, get_db
from app.main import app

VALID_BOOK: dict[str, Any] = {
    "title": "Dune",
    "author": "Frank Herbert",
    "genre": "Sci-Fi",
    "rating": 5,
    "is_read": True,
    "review": "A classic.",
}

MISSING_ID = 9999


def create_book(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """POST a valid book (with optional field overrides) and return the JSON body."""
    response = client.post("/books", json={**VALID_BOOK, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def titles(response: Any) -> list[str]:
    return [book["title"] for book in response.json()]


# --------------------------------------------------------------------------- CRUD


def test_create_book_returns_201_with_generated_fields(client: TestClient) -> None:
    book = create_book(client)
    assert book["id"] > 0
    assert {k: book[k] for k in VALID_BOOK} == VALID_BOOK
    assert book["created_at"] and book["updated_at"]


def test_create_book_applies_defaults_and_strips_whitespace(client: TestClient) -> None:
    response = client.post(
        "/books", json={"title": "  Gone Girl  ", "author": " Gillian Flynn ", "genre": "Thriller"}
    )
    assert response.status_code == 201
    book = response.json()
    assert book["title"] == "Gone Girl"
    assert book["author"] == "Gillian Flynn"
    assert book["rating"] is None
    assert book["is_read"] is False
    assert book["review"] is None


def test_rating_and_review_allowed_when_unread(client: TestClient) -> None:
    book = create_book(client, is_read=False, rating=2, review="Gave up halfway.")
    assert book["is_read"] is False
    assert book["rating"] == 2
    assert book["review"] == "Gave up halfway."


def test_list_books_empty(client: TestClient) -> None:
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []


def test_get_book_by_id(client: TestClient) -> None:
    created = create_book(client)
    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_update_book_is_partial_and_refreshes_updated_at(client: TestClient) -> None:
    created = create_book(client, is_read=False, rating=None, review=None)
    response = client.put(f"/books/{created['id']}", json={"is_read": True, "rating": 4})
    assert response.status_code == 200
    updated = response.json()
    # Sent fields change...
    assert updated["is_read"] is True
    assert updated["rating"] == 4
    # ...untouched fields keep their values.
    assert updated["title"] == created["title"]
    assert updated["author"] == created["author"]
    assert updated["genre"] == created["genre"]
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] > created["updated_at"]
    # And the change is stored, not just echoed back.
    assert client.get(f"/books/{created['id']}").json() == updated


def test_update_can_clear_rating_and_review(client: TestClient) -> None:
    created = create_book(client)
    response = client.put(f"/books/{created['id']}", json={"rating": None, "review": None})
    assert response.status_code == 200
    assert response.json()["rating"] is None
    assert response.json()["review"] is None


def test_delete_book(client: TestClient) -> None:
    created = create_book(client)
    response = client.delete(f"/books/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").json() == []


def test_full_crud_lifecycle(client: TestClient) -> None:
    book_id = create_book(client, title="The Hobbit", genre="Fantasy")["id"]
    assert titles(client.get("/books")) == ["The Hobbit"]
    response = client.put(f"/books/{book_id}", json={"title": "The Hobbit (2nd ed.)"})
    assert response.status_code == 200
    assert client.get(f"/books/{book_id}").json()["title"] == "The Hobbit (2nd ed.)"
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get("/books").json() == []


# ------------------------------------------------------------------------ Filters


@pytest.fixture
def library(client: TestClient) -> TestClient:
    """A small, varied library to filter against."""
    create_book(client, title="Dune", genre="Sci-Fi", rating=5, is_read=True)
    create_book(client, title="Foundation", genre="Sci-Fi", rating=3, is_read=True)
    create_book(client, title="Neuromancer", genre="Sci-Fi", rating=None, is_read=False)
    create_book(client, title="The Hobbit", genre="Fantasy", rating=4, is_read=True)
    create_book(client, title="Mistborn", genre="Fantasy", rating=5, is_read=False)
    create_book(client, title="Gone Girl", genre="Thriller", rating=None, is_read=False)
    return client


def test_filter_by_genre(library: TestClient) -> None:
    assert titles(library.get("/books", params={"genre": "Fantasy"})) == ["The Hobbit", "Mistborn"]
    assert library.get("/books", params={"genre": "Romance"}).json() == []


def test_filter_by_is_read(library: TestClient) -> None:
    assert titles(library.get("/books", params={"is_read": True})) == [
        "Dune",
        "Foundation",
        "The Hobbit",
    ]
    assert titles(library.get("/books", params={"is_read": False})) == [
        "Neuromancer",
        "Mistborn",
        "Gone Girl",
    ]


def test_filter_by_min_rating_excludes_unrated(library: TestClient) -> None:
    assert titles(library.get("/books", params={"min_rating": 4})) == [
        "Dune",
        "The Hobbit",
        "Mistborn",
    ]
    # min_rating=1 matches every *rated* book but still excludes unrated ones.
    rated = titles(library.get("/books", params={"min_rating": 1}))
    assert "Neuromancer" not in rated
    assert "Gone Girl" not in rated
    assert len(rated) == 4


def test_filters_combined(library: TestClient) -> None:
    response = library.get("/books", params={"genre": "Sci-Fi", "is_read": True, "min_rating": 4})
    assert titles(response) == ["Dune"]
    response = library.get("/books", params={"genre": "Fantasy", "min_rating": 5})
    assert titles(response) == ["Mistborn"]
    response = library.get("/books", params={"genre": "Fantasy", "is_read": False})
    assert titles(response) == ["Mistborn"]
    response = library.get("/books", params={"genre": "Thriller", "min_rating": 1})
    assert response.json() == []


# --------------------------------------------------------------------- Validation


@pytest.mark.parametrize("rating", [1, 5])
def test_rating_boundaries_accepted(client: TestClient, rating: int) -> None:
    assert create_book(client, rating=rating)["rating"] == rating


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_out_of_range_rejected(client: TestClient, rating: int) -> None:
    response = client.post("/books", json={**VALID_BOOK, "rating": rating})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "rating"]


@pytest.mark.parametrize("field", ["title", "author"])
@pytest.mark.parametrize("value", ["", "   "], ids=["empty", "whitespace"])
def test_empty_or_whitespace_title_author_rejected(
    client: TestClient, field: str, value: str
) -> None:
    response = client.post("/books", json={**VALID_BOOK, field: value})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_invalid_genre_rejected(client: TestClient) -> None:
    response = client.post("/books", json={**VALID_BOOK, "genre": "Horror"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "genre"]


@pytest.mark.parametrize("field", ["title", "author", "genre"])
def test_missing_required_field_rejected(client: TestClient, field: str) -> None:
    payload = {k: v for k, v in VALID_BOOK.items() if k != field}
    response = client.post("/books", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"


def test_empty_body_rejected(client: TestClient) -> None:
    assert client.post("/books", json={}).status_code == 422


@pytest.mark.parametrize("rating", [0, 6])
def test_invalid_rating_via_put_rejected(client: TestClient, rating: int) -> None:
    created = create_book(client, rating=3)
    response = client.put(f"/books/{created['id']}", json={"rating": rating})
    assert response.status_code == 422
    # The stored book is unchanged.
    assert client.get(f"/books/{created['id']}").json()["rating"] == 3


@pytest.mark.parametrize(
    "payload",
    [{"title": "  "}, {"author": ""}, {"genre": "Horror"}, {"title": None}, {"is_read": None}],
    ids=["blank-title", "empty-author", "bad-genre", "null-title", "null-is_read"],
)
def test_invalid_fields_via_put_rejected(client: TestClient, payload: dict[str, Any]) -> None:
    created = create_book(client)
    response = client.put(f"/books/{created['id']}", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("min_rating", [0, 6])
def test_min_rating_filter_out_of_range_rejected(client: TestClient, min_rating: int) -> None:
    response = client.get("/books", params={"min_rating": min_rating})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "min_rating"]


def test_invalid_genre_filter_rejected(client: TestClient) -> None:
    assert client.get("/books", params={"genre": "Horror"}).status_code == 422


# ---------------------------------------------------------------------------- 404


def test_get_missing_book_returns_404(client: TestClient) -> None:
    response = client.get(f"/books/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


def test_update_missing_book_returns_404(client: TestClient) -> None:
    response = client.put(f"/books/{MISSING_ID}", json={"rating": 3})
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


def test_delete_missing_book_returns_404(client: TestClient) -> None:
    response = client.delete(f"/books/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


def test_404_documented_in_openapi(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    operations = spec["paths"]["/books/{book_id}"]
    for method in ("get", "put", "delete"):
        not_found = operations[method]["responses"].get("404")
        assert not_found is not None, f"404 not documented on {method.upper()}"
        assert not_found["description"] == "Book not found"
        schema_ref = not_found["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/ErrorResponse"
    error_schema = spec["components"]["schemas"]["ErrorResponse"]
    assert error_schema["properties"]["detail"]["type"] == "string"


# ----------------------------------------------------------------------- Database


def test_get_db_yields_session_and_closes_it() -> None:
    """The real get_db dependency (not the test override) opens and closes a session."""
    dependency = get_db()
    db = next(dependency)
    assert isinstance(db, Session)
    assert db.execute(text("SELECT 1")).scalar_one() == 1
    assert db.in_transaction()
    # Finishing the generator (what FastAPI does after the response) runs `finally`.
    with pytest.raises(StopIteration):
        next(dependency)
    assert not db.in_transaction()


def test_get_db_closes_session_on_error() -> None:
    """If the request handler raises, the session is still closed."""
    dependency = get_db()
    db = next(dependency)
    db.execute(text("SELECT 1"))
    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError("handler failed"))
    assert not db.in_transaction()


def test_default_database_dir_is_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Run from an empty temp dir so the relative ./data path never hits the real one.
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "data").exists()
    ensure_sqlite_dir(DEFAULT_DATABASE_URL)
    assert (tmp_path / "data").is_dir()
    ensure_sqlite_dir(DEFAULT_DATABASE_URL)  # idempotent: no error if it already exists


def test_custom_database_url_dir_is_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "nested" / "dir" / "books.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    ensure_sqlite_dir(os.environ["DATABASE_URL"])
    assert db_file.parent.is_dir()
    assert not db_file.exists()  # only the directory; SQLite creates the file itself


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:"])
def test_in_memory_database_creates_no_dirs(
    url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    ensure_sqlite_dir(url)
    assert list(tmp_path.iterdir()) == []


# -------------------------------------------------------------------- Persistence


def test_data_persists_across_engine_rebuild(tmp_path: Path) -> None:
    """Simulate an app restart: write with one engine, read back with a fresh one."""
    db_url = f"sqlite:///{tmp_path / 'books.db'}"

    def build_session_factory() -> tuple[Any, sessionmaker[Session]]:
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)  # no-op on the second run
        return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_with(factory: sessionmaker[Session]) -> None:
        def override_get_db() -> Generator[Session, None, None]:
            db = factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

    try:
        # "First run": create a book, then fully dispose of the engine.
        engine, factory = build_session_factory()
        override_with(factory)
        with TestClient(app) as client:
            created = create_book(client, title="Persistent Book")
        engine.dispose()

        # "Second run": a brand-new engine on the same file must see the book.
        engine, factory = build_session_factory()
        override_with(factory)
        with TestClient(app) as client:
            response = client.get(f"/books/{created['id']}")
            assert response.status_code == 200
            assert response.json() == created
            assert titles(client.get("/books")) == ["Persistent Book"]
        engine.dispose()
    finally:
        app.dependency_overrides.clear()
