FROM python:3.12-slim AS base

# Create a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install uv (tool for running/installing project)
RUN pip install --no-cache-dir uv

# Copy dependency files to ensure reproducible installs
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide via uv
RUN uv pip install --system .

# Copy application code and tests
COPY app ./app
COPY tests ./tests

# Ensure non-root user owns the application files
RUN chown -R appuser:appuser /app

# Expose the API port
EXPOSE 8000

# Switch to non-root user for security
USER appuser

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

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
