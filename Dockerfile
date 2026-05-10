# Stage 1: Builder stage
FROM python:3.11-slim AS builder

# Install system dependencies required for building Python packages
# Removed gcc and curl as they are not needed for installing wheels
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --no-install-project --frozen --no-cache

# Stage 2: Final runtime stage
FROM python:3.11-slim

# Install runtime system dependencies
# Changed libpq-dev to libpq5 for a smaller runtime image
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

# Copy project source code
COPY apps/ apps/
COPY core/ core/
COPY templates/ templates/
COPY static/ static/
COPY manage.py mock_data.py ./
COPY .env* ./

# Create necessary directories for mounts
RUN mkdir -p media ai_models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings

# Expose port
EXPOSE 8000

# Default command using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "core.wsgi:application"]
