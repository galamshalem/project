"""SQLAlchemy ORM models: how data is stored (separate from API schemas)."""

from datetime import UTC, datetime

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.schemas import Genre


def utcnow() -> datetime:
    return datetime.now(UTC)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    # values_callable stores the enum *values* ("Sci-Fi") rather than names ("SCI_FI").
    genre: Mapped[Genre] = mapped_column(
        Enum(Genre, values_callable=lambda e: [m.value for m in e], validate_strings=True)
    )
    rating: Mapped[int | None] = mapped_column(default=None)
    is_read: Mapped[bool] = mapped_column(default=False)
    review: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    # onupdate fires on ORM UPDATEs; the PUT endpoint also sets it explicitly.
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
