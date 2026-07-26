# Backend image for Render.
# Matches the tested runtime (.python-version = 3.12.7). Render injects $PORT
# at runtime; uvicorn binds to it (see CMD).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libgomp1 is required by onnxruntime (a chromadb dependency) at import time;
# the slim base image doesn't include it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install deps first so this layer caches unless requirements change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Apply DB migrations, then start. Render sets $PORT (defaults to 10000 there);
# shell form so the variable expands, with an 8000 fallback for local runs.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
