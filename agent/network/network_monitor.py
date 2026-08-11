import logging
import os
import time
from typing import Optional

import requests

from .discovery import (
    discover_network,
    enrich_devices,
    get_local_networks,
)


logger = logging.getLogger("smart-monitor-network")


def get_api_url() -> str:
    return os.getenv(
        "SMART_MONITOR_API_URL",
        os.getenv(
            "API_URL",
            "http://backend:8000",
        ),
    ).rstrip("/")


def get_agent_token() -> Optional[str]:
    return (
        os.getenv("SMART_MONITOR_AGENT_TOKEN")
        or os.getenv("SMARTIT_AGENT_TOKEN")
        or os.getenv("AGENT_TOKEN")
    )


def submit_devices(devices):
    token = get_agent_token()

    if not token:
        logger.warning(
            "Network discovery disabled: agent token not configured"
        )
        return False

    url = (
        f"{get_api_url()}/network/discovery"
    )

    headers = {
        "X-Agent-Token": token,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            json={"devices": devices},
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        logger.info(
            "Submitted %d discovered network devices",
            len(devices),
        )

        return True

    except requests.RequestException as exc:
        logger.warning(
            "Network discovery submission failed: %s",
            exc,
        )
        return False


def run_discovery_once():
    networks = get_local_networks()

    if not networks:
        logger.info(
            "No IPv4 networks found for discovery"
        )
        return

    for item in networks:
        interface = item["interface"] or None
        network = item["network"]

        logger.info(
            "Discovering network %s on %s",
            network,
            interface or "any interface",
        )

        devices = discover_network(
            network,
            interface,
        )

        devices = enrich_devices(
            devices,
            interface or "",
            network,
        )

        if devices:
            submit_devices(devices)


def start_network_discovery(
    interval: int = 60,
):
    while True:
        try:
            run_discovery_once()
        except Exception:
            logger.exception(
                "Network discovery cycle failed"
            )

        time.sleep(interval)
