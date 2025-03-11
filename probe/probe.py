import os
import time
import signal
import sys
import logging
import requests
import subprocess
import json
from datetime import datetime

# Logger configuration
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/probe.log')
    ]
)

logger = logging.getLogger('uptime-probe')

# Environment variables
API_KEY = os.environ.get('API_KEY')
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5001')
FETCH_INTERVAL = int(os.environ.get('FETCH_INTERVAL', 300))  # 5 minutes by default
HEARTBEAT_INTERVAL = int(os.environ.get('HEARTBEAT_INTERVAL', 60))  # 1 minute by default

# Validate configs
if not API_KEY:
    logger.error("API_KEY not defined. Please set the API_KEY environment variable.")
    sys.exit(1)

# Initialize jobs
jobs = []
jobs_last_execution = {}  # Stores timestamp of last execution for each job

# Indicator for application termination
running = True

# Handler for termination signal
def signal_handler(sig, frame):
    global running
    logger.info("Termination signal received. Shutting down probe...")
    running = False

# Register handlers for termination signals
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def fetch_jobs():
    """Gets jobs from the server"""
    try:
        response = requests.get(f"{SERVER_URL}/api/probe/{API_KEY}/jobs")
        if response.status_code == 200:
            jobs_data = response.json()
            logger.info(f"Retrieved {jobs_data['jobs_count']} jobs from server")
            
            # Adiciona logs detalhados para cada job recebido
            for job in jobs_data['jobs']:
                logger.debug(f"Job ID: {job['id']}, Name: {job['name']}, Target: {job['target_host']}")
                if 'kuma_url' in job:
                    logger.debug(f"Kuma URL for job {job['id']}: {job['kuma_url']}")
                else:
                    logger.warning(f"Job {job['id']} is missing kuma_url field")
            
            return jobs_data['jobs']
        else:
            logger.error(f"Error getting jobs: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error connecting to server: {str(e)}")
        return []

def send_heartbeat():
    """Sends heartbeat signal to the server"""
    try:
        response = requests.post(f"{SERVER_URL}/api/probe/{API_KEY}/heartbeat")
        if response.status_code == 200:
            logger.debug("Heartbeat sent successfully")
            return True
        else:
            logger.error(f"Error sending heartbeat: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to server for heartbeat: {str(e)}")
        return False

def execute_ping(job):
    """Executes ping to the target host and returns results"""
    target_host = job['target_host']
    timeout = job.get('timeout_seconds', 10)
    count = max(1, job.get('retries', 3))  # Ensure count is at least 1
    
    logger.info(f"Running ping to {target_host}")
    
    try:
        command = ['ping', '-c', str(count), '-W', str(timeout), target_host]
        logger.debug(f"Ping command: {' '.join(command)}")
        
        # Start process
        start_time = time.time()
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            end_time = time.time()
            
            # Parse the result
            output = stdout.decode('utf-8', errors='ignore')
            error_output = stderr.decode('utf-8', errors='ignore')
            
            # Log command execution details
            logger.debug(f"Ping command exit_code: {exit_code}")
            logger.debug(f"Ping command stdout: {output}")
            if error_output:
                logger.debug(f"Ping command stderr: {error_output}")
            
            # In Docker, there might be permission issues for using ping
            # Let's try to interpret the result even if the command fails
            if exit_code != 0 and "Operation not permitted" in error_output:
                logger.warning("Ping failed due to permission issues. Make sure the container has the necessary permissions (--cap-add=NET_RAW)")
            
            # Results
            # If we received any response, we can consider the ping successful even with exit_code != 0
            success = exit_code == 0 or "bytes from" in output
            duration_ms = (end_time - start_time) * 1000  # Converting to ms
            
            # Extract more details from the ping result
            packets_sent = count
            packets_received = 0
            min_rtt = max_rtt = avg_rtt = 0
            
            # Add debug logs to understand ping parsing
            logger.debug(f"Command output: {exit_code}, Output: {output}")
            
            # Try to extract statistics (works on most Linux-based systems)
            try:
                # For Linux, we look for lines like "3 packets transmitted, 3 received, 0% packet loss"
                for line in output.splitlines():
                    logger.debug(f"Processing line: {line}")
                    if "packets transmitted" in line and "received" in line:
                        parts = line.split(",")
                        packets_sent = int(parts[0].split()[0])
                        packets_received = int(parts[1].split()[0])
                        logger.debug(f"Found packets: sent={packets_sent}, received={packets_received}")
                    
                    # Look for "min/avg/max/mdev"
                    if "min/avg/max" in line:
                        logger.debug(f"Found RTT line: {line}")
                        rtt_parts = line.split("=")[1].strip().split("/")
                        min_rtt = float(rtt_parts[0])
                        avg_rtt = float(rtt_parts[1])
                        max_rtt = float(rtt_parts[2])
                        logger.debug(f"Extracted RTT: min={min_rtt}, avg={avg_rtt}, max={max_rtt}")
            except Exception as e:
                logger.warning(f"Could not extract all statistics: {e}")
                # Default values are already defined
            
            # Also check if we have lines with "bytes from X.X.X.X"
            # This indicates that at least some packet was received
            response_lines = [line for line in output.splitlines() if "bytes from" in line and "time=" in line]
            
            # If we have responses but the official ping failed, we can extract the time manually
            if response_lines and not (success and avg_rtt > 0):
                try:
                    # Extract response time from lines that have "time=X ms"
                    times = []
                    for line in response_lines:
                        logger.debug(f"Processing response line: {line}")
                        time_part = line.split("time=")[1].split()[0]
                        if "ms" in time_part:
                            time_value = float(time_part.replace("ms", ""))
                            times.append(time_value)
                            logger.debug(f"Extracted time: {time_value}ms")
                    
                    if times:
                        # Recalculate statistics based on response lines
                        packets_received = len(times)
                        min_rtt = min(times) if times else 0
                        avg_rtt = sum(times) / len(times) if times else 0
                        max_rtt = max(times) if times else 0
                        success = packets_received > 0  # If we received any packet, consider it a success
                        logger.debug(f"Recalculated statistics: received={packets_received}, min={min_rtt}, avg={avg_rtt}, max={max_rtt}")
                except Exception as e:
                    logger.warning(f"Error extracting times from response lines: {e}")
            
            # Determine response time to send to Kuma
            response_time = 0
            if success and avg_rtt > 0:
                response_time = round(avg_rtt, 2)
            elif success and duration_ms > 0:
                response_time = round(duration_ms, 2)
            
            logger.info(f"Ping result: success={success}, response_time={response_time}ms, received={packets_received}/{packets_sent}")
            
            result = {
                "timestamp": datetime.utcnow().isoformat(),
                "job_id": job['id'],
                "target_host": target_host,
                "success": success,
                "duration_ms": round(duration_ms, 2),
                "packets_sent": packets_sent,
                "packets_received": packets_received,
                "packet_loss": 100.0 if packets_sent == 0 else round(100 * (1 - packets_received / packets_sent), 2),
                "min_rtt": round(min_rtt, 2),
                "avg_rtt": round(avg_rtt, 2),
                "max_rtt": round(max_rtt, 2),
                "response_time_ms": response_time,
                "error_message": error_output if not success else None,
                "output": output
            }
            
            return result
        except Exception as e:
            logger.error(f"Error executing ping process: {str(e)}")
            raise
    
    except Exception as e:
        logger.error(f"Error executing ping to {target_host}: {str(e)}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job['id'],
            "target_host": target_host,
            "success": False,
            "duration_ms": 0,
            "packets_sent": 0,
            "packets_received": 0,
            "packet_loss": 100.0,
            "min_rtt": 0,
            "avg_rtt": 0,
            "max_rtt": 0,
            "response_time_ms": 0,
            "error_message": str(e),
            "output": ""
        }

def send_result_to_server(job_id, result):
    """Sends the result to the server and to Uptime Kuma"""
    # Get the job to know the Kuma URL
    job = next((j for j in jobs if j['id'] == job_id), None)
    if not job:
        logger.error(f"Job ID {job_id} not found in job list")
        return
    
    # Format the result for the server
    data = {
        "job_id": job_id,
        "success": result["success"],
        "response_time_ms": result.get("response_time_ms"),
        "packets_sent": result.get("packets_sent"),
        "packets_received": result.get("packets_received"),
        "error_message": result.get("error_message"),
        "kuma_success": result.get("kuma_success", True),
        "kuma_error": result.get("kuma_error")
    }
    
    try:
        response = requests.post(
            f"{SERVER_URL}/api/results",
            json=data,
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        if response.status_code == 200:
            logger.debug(f"Result sent successfully to the server: Job ID {job_id}")
        else:
            logger.error(f"Error sending result to server: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception sending result to server: {str(e)}")

def send_ping_result_to_kuma(job_id, result):
    """Sends the ping result to Uptime Kuma"""
    job = next((j for j in jobs if j['id'] == job_id), None)
    if not job or not job.get('kuma_url'):
        logger.warning(f"Could not send result to Uptime Kuma: URL not configured for job {job_id}")
        result["kuma_success"] = False
        result["kuma_error"] = "Uptime Kuma URL not configured for this job"
        return
    
    # Remove any existing query parameters from kuma_url
    kuma_url = job['kuma_url']
    if '?' in kuma_url:
        kuma_url = kuma_url.split('?')[0]
        logger.debug(f"Removed query parameters from Kuma URL. Clean URL: {kuma_url}")
    
    # Prepare data to send to Uptime Kuma
    params = {
        "status": "up" if result["success"] else "down",
        "msg": result.get("error_message", "OK" if result["success"] else "Failed")
    }
    
    # Add ping only if successful and has a value
    if result["success"] and result.get("response_time_ms") is not None:
        # Ensure the ping is sent as a string
        params["ping"] = str(result["response_time_ms"])
    
    logger.info(f"Sending to Kuma: {params} to URL: {kuma_url}")
    
    try:
        # Using GET instead of POST
        response = requests.get(kuma_url, params=params, timeout=5)
        logger.debug(f"Response status: {response.status_code}, text: {response.text[:100]}")
        
        if response.status_code == 200:
            logger.info(f"Result sent successfully to Uptime Kuma: Job ID {job_id}")
            result["kuma_success"] = True
            result["kuma_error"] = None
        else:
            logger.error(f"Error sending result to Uptime Kuma: {response.status_code} - {response.text}")
            result["kuma_success"] = False
            result["kuma_error"] = f"HTTP Error {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Exception sending result to Uptime Kuma: {str(e)}")
        result["kuma_success"] = False
        result["kuma_error"] = f"Connection error: {str(e)}"

def check_job_execution_time(job):
    """Checks if it's time to execute the job"""
    job_id = job['id']
    current_time = time.time()
    
    # If the job has never been executed or if the interval has passed
    if job_id not in jobs_last_execution or \
       (current_time - jobs_last_execution[job_id]) >= job['interval_seconds']:
        return True
    
    return False

def main():
    global jobs
    last_fetch_time = 0
    last_heartbeat_time = 0
    
    logger.info("===== Starting Uptime Probe =====")
    logger.info(f"Connecting to server: {SERVER_URL}")
    logger.info(f"Job update interval: {FETCH_INTERVAL} seconds")
    logger.info(f"Heartbeat interval: {HEARTBEAT_INTERVAL} seconds")
    
    # Main loop
    while running:
        current_time = time.time()
        
        # Check if it's time to fetch jobs again
        if current_time - last_fetch_time >= FETCH_INTERVAL:
            jobs = fetch_jobs()
            last_fetch_time = current_time
        
        # Check if it's time to send heartbeat
        if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
            send_heartbeat()
            last_heartbeat_time = current_time
        
        # Process each job
        for job in jobs:
            if check_job_execution_time(job):
                # Execute ping
                result = execute_ping(job)
                
                # Send to Uptime Kuma
                send_ping_result_to_kuma(job['id'], result)
                
                # Send result to server
                send_result_to_server(job['id'], result)
                
                # Update timestamp of last execution
                jobs_last_execution[job['id']] = current_time
        
        # Small wait to not overload CPU
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Probe interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("===== Shutting down Uptime Probe =====")
        sys.exit(0)
