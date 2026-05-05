# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy ONLY dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# We use --no-install-project because we haven't copied the source code yet
RUN uv sync --no-install-project --frozen --no-cache --no-dev

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

# Copy project source code (Surgical COPY to avoid heavy files)
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

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
