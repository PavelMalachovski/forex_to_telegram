# Base image: Python 3.11 Bullseye
FROM python:3.11-bullseye

# Working directory
WORKDIR /app

# Copy only dependencies — this layer will update only when requirements.txt changes
COPY requirements.txt .

# Install system libraries for Playwright/Chromium in a single RUN
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libasound2 libpango-1.0-0 libcairo2 libfontconfig1 \
      libx11-xcb1 libxrender1 libglib2.0-0 libsm6 libice6 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps

# Copy the rest of the code (app.py, Procfile, etc.)
COPY . .

# Port and environment variables
EXPOSE 10000

# Start the application
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 1 --threads 2"]
