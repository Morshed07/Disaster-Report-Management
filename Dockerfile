# ---- Build Stage ----
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for psycopg (PostgreSQL adapter)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependency for PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source code
COPY . .

# Collect static files (uses production settings via wsgi.py default)
RUN DJANGO_SETTINGS_MODULE=disaster.settings.production \
    SECRET_KEY=build-placeholder \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user for security
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "disaster.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
