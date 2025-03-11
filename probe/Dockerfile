FROM python:3.11-alpine

WORKDIR /app

# Install ping utility
RUN apk add --no-cache iputils

# Copy dependencies and script
COPY requirements.txt .
COPY probe.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory with correct permissions
RUN mkdir -p /var/log
RUN chmod 777 /var/log

# Set default environment variables
# API_KEY must be provided when running the container
ENV SERVER_URL="http://uptime-server:5000"
ENV FETCH_INTERVAL=300
ENV HEARTBEAT_INTERVAL=60

# Note: The container must be run with --cap-add=NET_RAW for ping to work

CMD ["python", "-u", "probe.py"]
