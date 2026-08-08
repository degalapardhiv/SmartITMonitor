from sqlalchemy.orm import Session

from ..alert_model import Alert


async def check_device_alert(device, db: Session, manager):

    print(
        "Checking alerts:",
        device.hostname,
        device.cpu,
        device.ram
    )

    alerts = []


    if device.cpu > 80:

        print("CPU alert triggered")

        alerts.append(
            Alert(
                device_id=device.id,
                hostname=device.hostname,
                alert_type="CPU",
                value=device.cpu,
                severity="High",
                message=f"High CPU usage: {device.cpu}%"
            )
        )


    if device.ram > 90:

        print("RAM alert triggered")

        alerts.append(
            Alert(
                device_id=device.id,
                hostname=device.hostname,
                alert_type="RAM",
                value=device.ram,
                severity="High",
                message=f"High RAM usage: {device.ram}%"
            )
        )


    for alert in alerts:

        db.add(alert)


    if alerts:

        db.commit()

        print(
            "Alerts saved:",
            len(alerts)
        )


        for alert in alerts:

            await manager.broadcast(
                {
                    "type":"alert",
                    "alert":{
                        "hostname":alert.hostname,
                        "severity":alert.severity,
                        "message":alert.message
                    }
                }
            )
