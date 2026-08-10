from app.database import SessionLocal

from app.notification_history_model import NotificationHistory
from app.websocket_manager import manager



def save_notification(
    alert_id,
    channel,
    status,
    message
):

    db = SessionLocal()


    try:

        record = NotificationHistory(

            alert_id=alert_id,

            channel=channel,

            status=status,

            message=message

        )


        db.add(record)

        db.commit()


        try:

            manager.broadcast_from_thread(
                {
                    "type": "notification",
                    "channel": channel,
                    "status": status,
                    "message": message
                }
            )

        except Exception:
            pass


    finally:

        db.close()
