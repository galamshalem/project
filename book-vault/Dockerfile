# syntax=docker/dockerfile:1

# ---- Builder: resolve and install dependencies with uv ----------------------
# The official uv image, on the same Python version and Debian release (trixie)
# as python:3.11-slim, so the venv's interpreter path (/usr/local/bin/python3.11)
# and system libraries match the runtime stage.
FROM ghcr.io/astral-sh/uv:0.13-python3.11-trixie-slim AS builder

# Copy files instead of hard-linking (the cache is a separate mount), pre-compile
# bytecode for faster startup, and never download a different Python.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first, from the lockfile only, so this layer is cached
# until pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Runtime: slim image with just the venv and the app code ----------------
FROM python:3.11-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Unprivileged user to run the server.
RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/

# The SQLite file lives in /app/data (DATABASE_URL defaults to ./data/books.db).
# Create it owned by the app user *before* declaring the volume, so a fresh named
# volume inherits that ownership and the non-root user can write to it.
RUN mkdir -p /app/data && chown app:app /app/data
VOLUME /app/data

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
