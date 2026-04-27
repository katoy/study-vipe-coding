FROM python:3.12-slim AS base

# Create a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install build tooling and install dependencies
RUN pip install --no-cache-dir pip setuptools wheel

# Copy dependency files to ensure reproducible installs
COPY pyproject.toml uv.lock ./

# Install project and dependencies
RUN pip install --no-cache-dir .

# Copy application code and tests
COPY app ./app
COPY tests ./tests

# Ensure non-root user owns the application files
RUN chown -R appuser:appuser /app

# Expose the API port
EXPOSE 8080

# Switch to non-root user for security
USER appuser

# Run the FastAPI application.
# Cloud Run injects PORT; local docker run falls back to 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# CI stage with dev tools
FROM base AS ci
USER root
# Install CI/dev tools including Playwright for E2E tests
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir pytest pytest-cov ruff mypy playwright pytest-playwright
# Create global Playwright browsers directory and install browsers with OS deps
RUN mkdir -p /ms-playwright \
 && playwright install --with-deps \
 && chown -R appuser:appuser /ms-playwright
USER appuser
CMD ["pytest", "-q"]

# Final production image (default build target)
FROM base AS final
USER appuser
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
