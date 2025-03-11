FROM python:3.11-slim

WORKDIR /app

# Install requirements including wget for healthcheck
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==21.2.0

# Create required directories with appropriate permissions
RUN mkdir -p /app/logs /app/data && chmod -R 777 /app/logs /app/data

# Copy application code
COPY . .

# Set database to in-memory for simplicity
ENV DATABASE_URI="sqlite:////app/data/uptime.db"
ENV SECRET_KEY="dev-key-change-in-production"

# Initialize database with proper Flask app context
RUN python -c "from app import create_app; app = create_app(); app.app_context().push(); from app import db; db.create_all()"

# Expose Gunicorn port
EXPOSE 5000

# Start Gunicorn
CMD ["gunicorn", "--config=gunicorn_config.py", "wsgi:app", "--bind", "0.0.0.0:5000"]
