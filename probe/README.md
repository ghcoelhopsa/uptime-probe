# Uptime Probe

This is a containerized probe for monitoring hosts and sending results to Uptime Kuma. The probe connects to the central server, obtains the list of jobs to monitor, executes pings, and sends the results directly to the Uptime Kuma URLs configured for each job.

## Features

- Automatic job retrieval every X minutes (configurable)
- Ping execution for target hosts with configurable parameters
- Automatic result submission to Uptime Kuma
- Heartbeat to indicate the probe is active
- Detailed operation logs

## Requirements

- Docker and Docker Compose
- Valid API key registered in the central server

## Configuration

Edit the `docker-compose.yml` file and configure the following environment variables:

- `API_KEY`: API key of the probe registered in the central server
- `SERVER_URL`: URL of the central server (e.g., http://server:5001)
- `FETCH_INTERVAL`: Interval in seconds to fetch jobs (default: 300)
- `HEARTBEAT_INTERVAL`: Interval in seconds to send heartbeat (default: 60)

## Building and Running

### Build the container

```bash
docker-compose build
```

### Run the probe

```bash
docker-compose up -d
```

### Check logs

```bash
docker-compose logs -f
```

### Stop the probe

```bash
docker-compose down
```

## Registering a Probe on the Central Server

Before running the probe, you must register it on the central server:

1. Access the server in a web browser
2. Log in with your credentials
3. Go to the "Probes" section and click on "New Probe"
4. Fill in the name and description and obtain the API key
5. Use this API key in the `docker-compose.yml` file

## File Structure

- `probe.py`: Main script that executes pings and sends results
- `requirements.txt`: Python dependencies
- `Dockerfile`: Instructions for building the container
- `docker-compose.yml`: Configuration for running the container

## Troubleshooting

### The probe cannot connect to the server

- Check if the server is accessible from the container
- Confirm if the URL in `SERVER_URL` is correct
- Verify if the API key is valid

### Results do not reach Uptime Kuma

- Check if the Uptime Kuma URLs configured in the jobs are correct
- Confirm if Uptime Kuma is accessible from the container
- Check the probe logs to identify errors
