FROM python:3.12-slim

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

# Copy application code
COPY app ./app

# Ensure non-root user owns the application files
RUN chown -R appuser:appuser /app

# Expose the API port
EXPOSE 8000

# Switch to non-root user for security
USER appuser

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
