FROM python:3.12-slim
LABEL authors="Shashank Prasanna"

# Install system dependencies first
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first for better cache usage
COPY pyproject.toml uv.lock ./

# Install uv and Python dependencies in one layer
RUN pip install --no-cache-dir uv && \
    uv pip install --system --requirements pyproject.toml

# Copy project files
COPY src/ ./src/
COPY tests/ ./tests/
RUN mkdir media

# Default command: start API
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
