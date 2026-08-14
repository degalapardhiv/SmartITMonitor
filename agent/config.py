# ==========================================
# Smart IT Monitor Agent Configuration
# ==========================================
import os

# Backend API base URL (env-driven, matches smartit_agent.py)
API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

# Device identity (required for the token-based /devices/{id}/metrics flow)
DEVICE_ID = os.getenv("SMARTIT_DEVICE_ID", "")
AGENT_TOKEN = os.getenv("SMARTIT_AGENT_TOKEN", "")

# Device Information
DEPARTMENT = os.getenv(
    "SMARTIT_DEPARTMENT",
    "Computer Science & Engineering",
)

LAB = os.getenv("SMARTIT_LAB", "Cyber Security Lab")

LOCATION = os.getenv("SMARTIT_LOCATION", "Block A")

# Monitoring Interval (seconds)
INTERVAL = int(os.getenv("SMARTIT_INTERVAL", "5"))

# Request Timeout (seconds)
REQUEST_TIMEOUT = int(os.getenv("SMARTIT_REQUEST_TIMEOUT", "10"))
