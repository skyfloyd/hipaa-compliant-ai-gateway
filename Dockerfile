FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy English model required by Presidio
# Using pip install instead of spacy download for better Docker compatibility
# Using medium model (md) for better accuracy while keeping reasonable size (~91 MB)
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1-py3-none-any.whl

# Set environment variable for Presidio to use the medium model
ENV PRESIDIO_SPACY_MODEL=en_core_web_md

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

