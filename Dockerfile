# Use Python 3.12 slim base image
FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt pyproject.toml ./

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY risk_manager /app/risk_manager
COPY data /app/data
COPY config /app/config

ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "risk_manager.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
