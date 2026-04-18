FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create data & logs directories
RUN mkdir -p data logs

# Expose API port
EXPOSE 3003

# Run the bot with API server
CMD ["python", "main.py", "--api"]
