import nmap
import socket

scanner = nmap.PortScanner()


def scan_network(network):

    scanner.scan(
        hosts=network,
        arguments="-sn"
    )

    devices = []


    for host in scanner.all_hosts():

        hostname = ""

        try:
            hostname = socket.gethostbyaddr(host)[0]

        except:
            hostname = host


        state = scanner[host].state()


        devices.append({

            "hostname": hostname,

            "ip": host,

            "status": "online" if state in ["up", "online"] else "offline",

            "os": "Unknown",

            "cpu": 0,

            "ram": 0,

            "disk": 0,

            "department": "Unknown",

            "lab": "Unknown",

            "location": "Unknown"

        })


    return devices
