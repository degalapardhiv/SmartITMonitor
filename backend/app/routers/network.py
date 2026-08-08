from fastapi import APIRouter
from app.services.network_scanner import scan_network

router = APIRouter()

@router.get("/scan")
def network_scan():

    return scan_network("192.168.1.0/24")
