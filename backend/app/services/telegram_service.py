import requests

from app.database import SessionLocal

from app.services.notification_service import save_notification


from app.notification_config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)



def send_telegram(
    message,
    alert_id=None
):

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )


    try:

        response = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            }
        )


        if response.ok:

            save_notification(
                alert_id,
                "Telegram",
                "SENT",
                message
            )


        else:

            save_notification(
                alert_id,
                "Telegram",
                "FAILED",
                response.text
            )


    except Exception as e:


        save_notification(
            alert_id,
            "Telegram",
            "FAILED",
            str(e)
        )
