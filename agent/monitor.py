import socket
import platform
import time
import requests
import psutil

from config import (
    API_URL,
    DEVICE_ID,
    AGENT_TOKEN,
    DEPARTMENT,
    LAB,
    LOCATION,
    INTERVAL,
    REQUEST_TIMEOUT,
)

# ==========================================
# Smart IT Monitor Agent
# ==========================================


def get_ip_address():

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.connect(("8.8.8.8", 80))

        ip = sock.getsockname()[0]

        sock.close()

        return ip

    except Exception:

        return "127.0.0.1"


HOSTNAME = socket.gethostname()

IP_ADDRESS = get_ip_address()

OPERATING_SYSTEM = (
    f"{platform.system()} "
    f"{platform.release()}"
)
# ==========================================
# Startup Banner
# ==========================================

print("=" * 60)
print("          SMART IT MONITOR AGENT")
print("=" * 60)

print(f"Hostname   : {HOSTNAME}")
print(f"IP Address : {IP_ADDRESS}")
print(f"OS         : {OPERATING_SYSTEM}")

print(f"Department : {DEPARTMENT}")
print(f"Lab        : {LAB}")
print(f"Location   : {LOCATION}")

print("=" * 60)
print("Agent Started Successfully")
print(f"Sending metrics every {INTERVAL} seconds...")
print("=" * 60)


# ==========================================
# Agent Registration (token-based flow)
# ==========================================

def register():

    global DEVICE_ID, AGENT_TOKEN

    print("=" * 60)
    print("Registering agent with backend...")
    print("=" * 60)

    payload = {
        "hostname": HOSTNAME,
        "ip": IP_ADDRESS,
        "os": OPERATING_SYSTEM,
    }

    try:

        response = requests.post(
            f"{API_URL}/agent/register",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        DEVICE_ID = str(data.get("device_id", ""))
        AGENT_TOKEN = str(data.get("agent_token", ""))

        if not DEVICE_ID or not AGENT_TOKEN:
            raise RuntimeError(
                "registration response missing device_id/agent_token"
            )

        print(f"Registered device : {DEVICE_ID}")

    except Exception as error:

        print("=" * 60)
        print("ERROR: Agent registration failed.")
        print("The backend now requires a registered device + agent token.")
        print("Set SMARTIT_API_URL, SMARTIT_DEVICE_ID and SMARTIT_AGENT_TOKEN")
        print("in the environment (or agent/.agent.env) and re-run this agent.")
        print(f"Detail: {error}")
        print("=" * 60)

        raise SystemExit(1)


# ==========================================
# Collect Device Metrics
# ==========================================

def collect_metrics():

    cpu = psutil.cpu_percent(interval=1)

    ram = psutil.virtual_memory().percent

    disk = psutil.disk_usage("/").percent

    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
    }

# ==========================================
# Send Metrics to Server
# ==========================================

def send_metrics():

    metrics = collect_metrics()

    url = f"{API_URL}/devices/{DEVICE_ID}/metrics"

    try:

        response = requests.post(
            url,
            params={
                "cpu": metrics["cpu"],
                "ram": metrics["ram"],
                "disk": metrics["disk"],
            },
            headers={
                "X-Agent-Token": AGENT_TOKEN,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        print("-" * 60)

        print(
            f"Time       : {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(f"Status     : {response.status_code}")

        print(f"Hostname   : {HOSTNAME}")

        print(f"IP Address : {IP_ADDRESS}")

        print(f"CPU        : {metrics['cpu']:.1f}%")

        print(f"RAM        : {metrics['ram']:.1f}%")

        print(f"Disk       : {metrics['disk']:.1f}%")

    except requests.exceptions.Timeout:

        print("-" * 60)
        print("ERROR: Request timed out.")

    except requests.exceptions.ConnectionError:

        print("-" * 60)
        print("ERROR: Unable to connect to backend.")
        print(f"Backend URL: {url}")

    except requests.exceptions.HTTPError as error:

        print("-" * 60)
        print(f"HTTP Error : {error}")
        print("Check that SMARTIT_DEVICE_ID / SMARTIT_AGENT_TOKEN match")
        print("a device registered on the backend.")

    except Exception as error:

        print("-" * 60)
        print(f"Unexpected Error : {error}")
# ==========================================
# Main Monitoring Loop
# ==========================================

def main():

    print("Monitoring service is running...")
    print("Press CTRL + C to stop.\n")

    try:

        while True:

            send_metrics()

            print("-" * 60)
            print(f"Next update in {INTERVAL} seconds...")
            print("-" * 60)

            time.sleep(INTERVAL)

    except KeyboardInterrupt:

        print("\n" + "=" * 60)
        print("Smart IT Monitor Agent stopped.")
        print("=" * 60)

    except Exception as error:

        print("\n" + "=" * 60)
        print("Fatal Error")
        print(error)
        print("=" * 60)
# ==========================================
# Backend Connectivity Check
# ==========================================

def check_backend():

    print("=" * 60)
    print("Checking backend connection...")
    print("=" * 60)

    try:

        response = requests.get(
            f"{API_URL}/health",
            timeout=5
        )

        if response.status_code == 200:

            print("✓ Backend is online")

            try:
                print("Response:", response.json())
            except Exception:
                pass

            return True

        print(
            f"Backend returned status: {response.status_code}"
        )

        return False

    except Exception as error:

        print("✗ Unable to connect to backend")
        print(error)

        return False


# ==========================================
# Program Entry
# ==========================================

if __name__ == "__main__":

    if not check_backend():

        print()
        print("Backend is unavailable.")
        print("Please start the FastAPI server first.")
        print()

        exit(1)

    if not DEVICE_ID or not AGENT_TOKEN:

        register()

    print()
    print("Starting Smart IT Monitor...")
    print()

    main()
