from fastapi import APIRouter, Depends
from app.services.network_scanner import scan_network
from app.database import SessionLocal
from app.role_dependency import require_admin

router = APIRouter()

@router.get("/scan")
def network_scan(current_user=Depends(require_admin)):

    db = SessionLocal()

    try:

        from app.services.settings_service import get_scan_ranges

        ranges = get_scan_ranges(db)

        network = ranges[0] if ranges else "192.168.1.0/24"

    finally:

        db.close()

    return scan_network(network)