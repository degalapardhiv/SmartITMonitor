import ipaddress
import socket
import subprocess
from typing import Dict, List, Optional


def get_local_networks() -> List[Dict[str, str]]:
    """
    Return IPv4 networks associated with local interfaces.

    Only private/local IPv4 networks are considered.
    """
    networks = []

    try:
        output = subprocess.check_output(
            ["ip", "-o", "-4", "addr", "show", "scope", "global"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return networks

    for line in output.splitlines():
        parts = line.split()

        if len(parts) < 4:
            continue

        interface = parts[1]
        address = parts[3]

        try:
            network = ipaddress.ip_interface(address).network

            if not network.is_private:
                continue

            networks.append(
                {
                    "interface": interface,
                    "network": str(network),
                }
            )
        except ValueError:
            continue

    return networks


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
