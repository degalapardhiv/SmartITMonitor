import ipaddress
import os
import socket
import subprocess
from typing import Dict, List, Optional


def get_network_ranges_from_env() -> List[str]:
    raw = (
        os.getenv("SMARTIT_NETWORK_RANGES")
        or os.getenv("SMARTIT_NETWORK_RANGE")
        or os.getenv("SMART_MONITOR_NETWORK_RANGES")
        or ""
    )

    ranges = []

    for part in raw.split(","):
        value = part.strip()

        if not value:
            continue

        try:
            ranges.append(str(ipaddress.ip_network(value, strict=False)))
        except ValueError:
            continue

    return ranges


_CONTAINER_IFACE_PREFIXES = (
    "br-",
    "docker",
    "veth",
    "virbr",
    "vboxnet",
)

_LEGACY_DOCKER_NETWORKS = (
    "172.17.0.0/16",
    "172.18.0.0/16",
    "172.19.0.0/16",
    "172.20.0.0/16",
)


def _is_container_interface(interface: str) -> bool:
    return interface.startswith(_CONTAINER_IFACE_PREFIXES)


def get_local_networks() -> List[Dict[str, str]]:
    """
    Return IPv4 networks associated with local interfaces
    plus any explicit ranges configured via env vars.

    Container/virtual interfaces (Docker bridges, veth, virbr, VBox) are
    skipped so LAN discovery doesn't stall scanning huge private ranges.
    """
    networks = []

    try:
        output = subprocess.check_output(
            ["ip", "-o", "-4", "addr", "show", "scope", "global"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        output = ""

    for line in output.splitlines():
        parts = line.split()

        if len(parts) < 4:
            continue

        interface = parts[1]
        address = parts[3]

        if _is_container_interface(interface):
            continue

        try:
            network = ipaddress.ip_interface(address).network
        except ValueError:
            continue

        if network.is_link_local or network.is_loopback:
            continue

        if str(network) in _LEGACY_DOCKER_NETWORKS:
            continue

        networks.append(
            {
                "interface": interface,
                "network": str(network),
            }
        )

    for network in get_network_ranges_from_env():
        networks.append(
            {
                "interface": "",
                "network": network,
            }
        )

    seen = set()
    unique = []

    for entry in networks:
        if entry["network"] in seen:
            continue

        seen.add(entry["network"])
        unique.append(entry)

    return unique


def discover_network(
    network: str,
    interface: Optional[str] = None,
) -> List[Dict[str, Optional[str]]]:
    """
    Discover hosts on a configured private IPv4 network.

    Uses the local nmap executable when available.
    """
    try:
        ipaddress.ip_network(network, strict=False)
    except ValueError:
        raise ValueError(f"Invalid network: {network}")

    command = [
        "nmap",
        "-sn",
        "-n",
        network,
    ]

    if interface:
        command.extend(["-e", interface])

    try:
        output = subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return []

    return parse_nmap_output(output)


def parse_nmap_output(
    output: str,
) -> List[Dict[str, Optional[str]]]:
    devices = []

    current = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if line.startswith("Nmap scan report for "):
            if current:
                devices.append(current)

            target = line.split(
                "Nmap scan report for ",
                1,
            )[1]

            hostname = None
            ip = target

            if target.startswith("(") and target.endswith(")"):
                ip = target[1:-1]

            elif " (" in target and target.endswith(")"):
                hostname, ip = target.rsplit(" (", 1)
                ip = ip[:-1]

            current = {
                "ip": ip,
                "mac": None,
                "hostname": hostname,
                "vendor": None,
            }

        elif current and "MAC Address:" in line:
            value = line.split(
                "MAC Address:",
                1,
            )[1].strip()

            if " " in value:
                mac, vendor = value.split(" ", 1)
                current["mac"] = mac
                current["vendor"] = vendor.strip("()")

            else:
                current["mac"] = value

    if current:
        devices.append(current)

    return devices


def reverse_dns(ip: str) -> Optional[str]:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except (socket.herror, socket.gaierror, OSError):
        return None


def enrich_devices(
    devices: List[Dict[str, Optional[str]]],
    interface: str,
    network: str,
) -> List[Dict[str, Optional[str]]]:
    enriched = []

    for device in devices:
        hostname = device.get("hostname")

        if not hostname and device.get("ip"):
            hostname = reverse_dns(device["ip"])

        enriched.append(
            {
                "ip": device.get("ip"),
                "mac": device.get("mac"),
                "hostname": hostname,
                "vendor": device.get("vendor"),
                "interface": interface,
                "network": network,
            }
        )

    return enriched
