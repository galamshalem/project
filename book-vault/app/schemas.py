"""Pydantic schemas: the API's request/response contract (separate from ORM models)."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# (str, Enum) per the assignment spec; equivalent to StrEnum for our purposes.
class Genre(str, Enum):  # noqa: UP042
    FANTASY = "Fantasy"
    ROMANCE = "Romance"
    SCI_FI = "Sci-Fi"
    THRILLER = "Thriller"
    NON_FICTION = "Non-Fiction"
    MYSTERY = "Mystery"
    HISTORICAL = "Historical"


# Whitespace is stripped *before* the length check, so "   " is rejected.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Rating = Annotated[int, Field(ge=1, le=5)]


class BookBase(BaseModel):
    title: NonEmptyStr
    author: NonEmptyStr
    genre: Genre
    # Rating and review are allowed even for unread books (e.g. a DNF review).
    rating: Rating | None = None
    is_read: bool = False
    review: str | None = None


class BookCreate(BookBase):
    """Payload for POST /books."""


class BookUpdate(BaseModel):
    """Payload for PUT /books/{id}: every field optional, same constraints.

    Only fields the client actually sends are applied (see `exclude_unset`).
    """

    title: NonEmptyStr | None = None
    author: NonEmptyStr | None = None
    genre: Genre | None = None
    rating: Rating | None = None
    is_read: bool | None = None
    review: str | None = None


class BookRead(BookBase):
    """Response body: the stored book, built straight from the ORM object."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
