# ---- Build Stage ----
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system build dependencies for C-extensions (psycopg2, pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python3-dev libpq-dev zlib1g-dev libjpeg-dev && \
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

# Install runtime dependencies for PostgreSQL and healthchecks
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source code
COPY . .

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to run with gunicorn
CMD ["gunicorn", "disaster.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

