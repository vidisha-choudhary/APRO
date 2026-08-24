# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Prevent writing pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Copy requirements file (derived from pyproject.toml)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into container
COPY . .

# Expose the default application port
EXPOSE 8000

# Start application using uvicorn
CMD ["uvicorn", "apro.main:app", "--host", "0.0.0.0", "--port", "8000"]
