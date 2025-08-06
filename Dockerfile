FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/config.yaml ./config/

# Create non-root user
RUN useradd -m -u 1000 foxreport && \
    chown -R foxreport:foxreport /app
USER foxreport

# Set default command - use the comprehensive config for Docker
CMD ["python", "-m", "src.cli.send_report", "--config", "config/config.yaml"]
