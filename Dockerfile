FROM python:3.12-slim

# Create a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency file
COPY pyproject.toml .

# Install dependencies system-wide via uv
RUN uv pip install --system .

# Copy application code
COPY app ./app

# Expose the API port
EXPOSE 8000

# Switch to non-root user for security
USER appuser

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
