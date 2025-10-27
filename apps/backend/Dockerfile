FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for layer caching)
COPY requirements.txt pyproject.toml* ./

# Install dependencies directly in system Python (no venv needed in Docker!)
RUN uv pip install --system -r requirements.txt

# Install Spacy models
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download en_core_web_lg

# Copy application code
COPY . .

# Create .env from example if not exists (will be overridden by docker-compose env_file)
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run server (using system Python directly)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
