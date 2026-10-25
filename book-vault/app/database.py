"""Database engine, session factory and the FastAPI session dependency."""

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./data/books.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLite won't create missing parent directories, so make sure ./data exists.
if DATABASE_URL == DEFAULT_DATABASE_URL:
    Path("./data").mkdir(parents=True, exist_ok=True)

# SQLite connections refuse cross-thread use by default; FastAPI may serve a
# request on a different thread than the one that opened the connection.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
