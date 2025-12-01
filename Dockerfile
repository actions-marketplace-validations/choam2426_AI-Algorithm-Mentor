# syntax=docker/dockerfile:1

# 🚀 Lightweight Python image with uv for fast dependency installation
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Install dependencies only (cached layer)
COPY app/pyproject.toml app/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY app/src ./src
COPY app/main.py ./

# ─────────────────────────────────────────────────────────────
# Production stage - minimal runtime image
# ─────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src
COPY --from=builder /app/main.py ./

# Use virtualenv Python
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python", "/app/main.py"]
