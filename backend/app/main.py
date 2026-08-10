from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.metrics import REQUEST_COUNT
from app.system_metrics import start_metrics_thread
from app.device_metrics import start_device_metrics
from app.services.heartbeat_service import start_heartbeat
from app.services.alert_monitor import start_alert_monitor
from fastapi.middleware.cors import CORSMiddleware

from . import settings_model
from . import email_settings_model
from . import email_history_model
from . import notification_history_model
from .database import Base, engine

# Database Models
from .models import Device
from .metric_model import DeviceMetric
from .user_model import User
from .alert_model import Alert

# API Routers
from .routes import router
from .auth_routes import router as auth_router
from .alert_routes import router as alert_router
from .usb_routes import router as usb_router
from .exam_mode import router as exam_mode_router

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart IT Monitor API",
    description="Enterprise Smart IT Monitoring System",
    version="2.0.0",
)

@app.get("/metrics")
def metrics():
    REQUEST_COUNT.inc()
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )



# ---------------------------------------
# CORS
# ---------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------
# Routes
# ---------------------------------------

app.include_router(auth_router)
app.include_router(alert_router)
for route in router.routes:
    app.router.routes.append(route)

# ---------------------------------------
# Root
# ---------------------------------------

@app.get("/")
def root():
    return {
        "application": "Smart IT Monitor",
        "status": "Running",
        "version": "2.0.0",
    }

# ---------------------------------------
# Health Check
# ---------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
    }

# ---------------------------------------
# Information
# ---------------------------------------

@app.get("/info")
def info():
    return {
        "name": "Smart IT Monitor",
        "backend": "FastAPI",
        "frontend": "React + Vite",
        "database": "PostgreSQL",
        "authentication": "JWT",
        "monitoring": "Agent Based",
        "version": "2.0.0",
    }



@app.on_event("startup")
def startup_metrics():
    start_metrics_thread()



@app.on_event("startup")
def startup_device_metrics():
    start_device_metrics()
    start_heartbeat()
    start_alert_monitor()


app.include_router(usb_router)

app.include_router(exam_mode_router)
