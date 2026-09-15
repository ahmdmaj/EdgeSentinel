FROM python:3.11-slim

# Create dedicated non-root system group and user
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure non-root appuser owns the application directory for SQLite outbox read/write
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Start Edge Service with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
