import socket
import platform
import time
import requests
import psutil

from config import (
    SERVER_URL,
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
print("Sending metrics every 30 seconds...")
print("=" * 60)


# ==========================================
# Collect Device Metrics
# ==========================================

def collect_metrics():

    cpu = psutil.cpu_percent(interval=1)

    ram = psutil.virtual_memory().percent

    disk = psutil.disk_usage("/").percent

    return {
        "hostname": HOSTNAME,
        "ip": IP_ADDRESS,

        "cpu": cpu,
        "ram": ram,
        "disk": disk,

        "status": "Online",

        "department": DEPARTMENT,
        "lab": LAB,
        "location": LOCATION,
        "os": OPERATING_SYSTEM,
    }

# ==========================================
# Send Metrics to Server
# ==========================================

def send_metrics():

    device = collect_metrics()

    try:

        response = requests.post(
            SERVER_URL,
            json=device,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        print("-" * 60)

        print(
            f"Time       : {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(f"Status     : {response.status_code}")

        print(f"Hostname   : {device['hostname']}")

        print(f"IP Address : {device['ip']}")

        print(f"CPU        : {device['cpu']:.1f}%")

        print(f"RAM        : {device['ram']:.1f}%")

        print(f"Disk       : {device['disk']:.1f}%")

        try:

            print(
                "Server     :",
                response.json()
            )

        except Exception:

            print(
                "Server     : No JSON response"
            )

    except requests.exceptions.Timeout:

        print("-" * 60)
        print("ERROR: Request timed out.")

    except requests.exceptions.ConnectionError:

        print("-" * 60)
        print("ERROR: Unable to connect to backend.")
        print(f"Backend URL: {SERVER_URL}")

    except requests.exceptions.HTTPError as error:

        print("-" * 60)
        print(f"HTTP Error : {error}")

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
            print("Next update in 30 seconds...")
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
            SERVER_URL.replace("/devices", "/health"),
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

    if check_backend():

        print()
        print("Starting Smart IT Monitor...")
        print()

        main()

    else:

        print()
        print("Backend is unavailable.")
        print("Please start the FastAPI server first.")
        print()

        exit(1)

