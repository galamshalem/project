"""FastAPI application: Personal Book Vault & Reading Tracker endpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Book, utcnow
from app.schemas import BookCreate, BookRead, BookUpdate, Genre


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Create tables on startup (no-op if they already exist).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Personal Book Vault & Reading Tracker",
    description="Track the books you own, what you've read, and how you rated them.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_book_or_404(db: Session, book_id: int) -> Book:
    """Fetch a book by id, raising 404 if it doesn't exist."""
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.post("/books", response_model=BookRead, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, db: Session = Depends(get_db)) -> Book:
    book = Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=list[BookRead])
def list_books(
    genre: Genre | None = None,
    is_read: bool | None = None,
    min_rating: int | None = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
) -> list[Book]:
    """List books, optionally filtered. Filters combine with AND."""
    query = select(Book).order_by(Book.id)
    if genre is not None:
        query = query.where(Book.genre == genre)
    if is_read is not None:
        query = query.where(Book.is_read == is_read)
    if min_rating is not None:
        # In SQL, NULL >= n is never true, so unrated books are excluded here.
        query = query.where(Book.rating >= min_rating)
    return list(db.scalars(query))


@app.get("/books/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> Book:
    return get_book_or_404(db, book_id)


@app.put("/books/{book_id}", response_model=BookRead)
def update_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)) -> Book:
    """Partially update a book: only fields present in the request body change."""
    book = get_book_or_404(db, book_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    # Set explicitly so an empty body `{}` still counts as an update.
    book.updated_at = utcnow()
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = get_book_or_404(db, book_id)
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
