FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        postgresql-client \
        libpq-dev \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy basify framework
COPY basify ./basify

# Copy docker-compose.yml for service discovery
COPY docker-compose.yml ./docker-compose.yml

# Copy project
COPY services/inventory-service .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8002

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]