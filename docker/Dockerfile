# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS builder
RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

EXPOSE 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
