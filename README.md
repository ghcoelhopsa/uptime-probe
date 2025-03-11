# Uptime Monitor

Web service monitoring system with distributed probe architecture. It has a web interface for registering probes and jobs, similar to Uptime Kuma in push mode.

## Features

- User authentication
- Probe registration with API Key generation
- Monitoring job configuration (ping or application)
- Monitoring results visualization
- Dashboard with system overall status

## Technologies Used

- Backend: Flask, SQLAlchemy
- Frontend: Bootstrap 5, FontAwesome
- Database: SQLite (can be configured for other DBMSs)

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Server Deployment

1. Clone the repository
2. Build and start the server container:

```bash
cd uptime
sudo docker compose build
sudo docker compose up -d
```

3. Access the application at http://localhost:5000 (default username/password: admin/admin)
4. Create a new probe in the web interface and copy the generated API key

#### Probe Deployment

**Important**: The probe requires the Uptime Monitor server to be deployed and accessible first. The probe connects to the server for job instructions and reports results back to the server. For proper visualization, the jobs you configure in the Uptime Monitor should include valid Uptime Kuma push URLs.

##### Option 1A: Docker Deployment (Recommended)

1. Copy the probe directory to the machine that will run the probe:
```bash
scp -r /path/to/uptime/probe user@probe-machine:/destination/path/
# or use any other file transfer method
```

2. Navigate to the probe directory and edit the docker-compose.yml file:
```bash
cd /path/to/probe
nano docker-compose.yml
```

3. Update the environment variables with your server details and the API key generated from the server web interface:
```yaml
environment:
  - API_KEY=your_probe_api_key_here  # Replace with the API key from the server
  - SERVER_URL=http://your_server_ip:5000  # Your server's IP address and port
  - FETCH_INTERVAL=300  # Interval in seconds to fetch jobs (5 minutes)
  - HEARTBEAT_INTERVAL=60  # Interval in seconds to send heartbeat (1 minute)
```

4. Build and start the probe container:
```bash
sudo docker compose build
sudo docker compose up -d
```

5. Verify in the server web interface that the probe is connected

##### Option 1B: Manual Installation

#### Requirements

- Python 3.8 or higher
- Pip

#### Server Installation

1. Clone the repository
2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

```bash
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the application:

```bash
flask run --host=0.0.0.0
```

6. Access the application at http://localhost:5000
7. Create a new probe in the web interface and copy the generated API key

#### Probe Installation

**Important**: The probe requires the Uptime Monitor server to be deployed and accessible first. The probe connects to the server for job instructions and reports results back to the server. For proper visualization, the jobs you configure in the Uptime Monitor should include valid Uptime Kuma push URLs.

1. Copy the probe directory to the machine that will run the probe
2. Create a virtual environment and install dependencies:

```bash
cd probe
python -m venv venv
source venv/bin/activate  # On Linux/Mac
pip install -r requirements.txt
```

3. Create a `.env` file with the required configuration:

```bash
echo "API_KEY=your_probe_api_key_here" > .env
echo "SERVER_URL=http://your_server_ip:5000" >> .env
echo "FETCH_INTERVAL=300" >> .env
echo "HEARTBEAT_INTERVAL=60" >> .env
```

4. Run the probe:

```bash
python probe.py
```

## Architecture

- **Server**: Central application that manages users, probes, jobs, and results
- **Probes**: Distributed components that connect to the server through an API Key and execute monitoring jobs
- **Jobs**: Monitoring tasks configured to check host availability and services
- **Results**: Data collected from the monitoring jobs
- **Integration**: The system works in conjunction with Uptime Kuma, sending monitoring results to it for visualization and alerting

## System Dependencies

- **Uptime Monitor Server**: Main application that manages users, probes, jobs, and results
- **Uptime Kuma**: External monitoring visualization tool that the Uptime Monitor forwards data to
- **Probes**: Depend on the Uptime Monitor server for job configuration, and can report results to Uptime Kuma if configured in jobs

## Security Considerations

- Always change the default admin password
- Use HTTPS in production environments
- Keep API keys secure
- The server container uses a persistent volume for the SQLite database
- Probes require the NET_RAW capability for ping functionality

## Performance Optimizations

- SQLite is configured with WAL mode for better concurrency
- Efficient transaction management for database operations
- The server uses Gunicorn for production deployment
- Containers are built using lightweight base images
