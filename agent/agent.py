import time
import socket
import platform
import psutil
import requests
import json
import os

def get_local_ip():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]

    except:
        ip = "127.0.0.1"

    finally:
        s.close()

    return ip



API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

CONFIG_FILE = os.getenv(
    "SMARTIT_CONFIG_FILE",
    "config.json",
)


DEVICE_ID = None
AGENT_TOKEN = None



def save_config():

    data = {
        "device_id": DEVICE_ID,
        "agent_token": AGENT_TOKEN
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)



def load_config():

    global DEVICE_ID, AGENT_TOKEN

    if os.path.exists(CONFIG_FILE):

        with open(CONFIG_FILE) as f:
            data = json.load(f)


        DEVICE_ID = data["device_id"]
        AGENT_TOKEN = data["agent_token"]

        print(
            "Loaded device:",
            DEVICE_ID
        )

        return True


    return False



def register():

    global DEVICE_ID, AGENT_TOKEN


    hostname = socket.gethostname()


    data = {

        "hostname": hostname,

        "ip": get_local_ip(),

        "os": platform.system()

    }


    try:

        response = requests.post(
            f"{API_URL}/agent/register",
            json=data,
            timeout=10
        )

        response.raise_for_status()

    except Exception as e:

        print("Error: failed to register with backend:", e)
        print("Check that SMARTIT_API_URL points at a running backend.")
        raise SystemExit(1)


    result = response.json()


    DEVICE_ID = result["device_id"]

    AGENT_TOKEN = result["agent_token"]


    save_config()


    print(
        "Registered:",
        DEVICE_ID
    )



def get_metrics():

    return {

        "cpu": psutil.cpu_percent(interval=1),

        "ram": psutil.virtual_memory().percent,

        "disk": psutil.disk_usage("/").percent

    }



def send_metrics():

    metrics = get_metrics()


    response = requests.post(

        f"{API_URL}/devices/{DEVICE_ID}/metrics",

        params=metrics,

        headers={
            "X-Agent-Token": AGENT_TOKEN
        }

    )


    print(
        metrics,
        response.json()
    )



if not load_config():

    register()



while True:

    try:

        send_metrics()


    except Exception as e:

        print(
            "Error:",
            e
        )


    time.sleep(10)
