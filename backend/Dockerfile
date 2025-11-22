FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/. .

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Use exec form with shell to handle PORT variable
# CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]