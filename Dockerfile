# Base image: Python 3.11 Bullseye
FROM python:3.11-bullseye

# Set working directory
WORKDIR /app

# Copy only dependencies first for better Docker caching
COPY requirements.txt .

# Install system libraries and Google Chrome Stable
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget gnupg2 ca-certificates fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libasound2 libpango-1.0-0 libcairo2 libfontconfig1 \
      libx11-xcb1 libxrender1 libglib2.0-0 libsm6 libice6 && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create migrations directory if it doesn't exist
RUN mkdir -p migrations/versions

# Expose the app port
EXPOSE 10000

# Start the application with database setup
CMD ["sh", "-c", "python setup_database.py && gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 1 --threads 2"]
