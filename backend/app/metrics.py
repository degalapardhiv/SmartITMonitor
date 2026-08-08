from prometheus_client import Counter, Gauge


REQUEST_COUNT = Counter(
    "smart_monitor_requests_total",
    "Total API requests"
)


DEVICE_COUNT = Gauge(
    "smart_monitor_devices_total",
    "Total monitored devices"
)


ONLINE_DEVICES = Gauge(
    "smart_monitor_online_devices",
    "Online devices"
)


CPU_USAGE = Gauge(
    "smart_monitor_cpu_usage",
    "Average CPU usage"
)


RAM_USAGE = Gauge(
    "smart_monitor_ram_usage",
    "Average RAM usage"
)


DISK_USAGE = Gauge(
    "smart_monitor_disk_usage",
    "Average disk usage"
)


def update_device_metrics(devices):

    total = len(devices)

    online = 0
    cpu_total = 0
    ram_total = 0
    disk_total = 0


    for device in devices:

        if str(device.status).lower() in ["up", "online"]:
            online += 1

        cpu_total += device.cpu or 0
        ram_total += device.ram or 0
        disk_total += device.disk or 0


    DEVICE_COUNT.set(total)

    ONLINE_DEVICES.set(online)


    if total:

        CPU_USAGE.set(cpu_total / total)

        RAM_USAGE.set(ram_total / total)

        DISK_USAGE.set(disk_total / total)

    else:

        CPU_USAGE.set(0)

        RAM_USAGE.set(0)

        DISK_USAGE.set(0)
