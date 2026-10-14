FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Install Tesseract OCR and required system runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-tel \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to /app
WORKDIR /app

# Install dependencies with caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Alembic migration config and application source code
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Create and switch to a non-root application user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose default port
EXPOSE 10000

# Start FastAPI server using uvicorn from the backend directory with dynamic PORT support
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
