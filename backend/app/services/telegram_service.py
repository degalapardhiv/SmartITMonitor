import requests

from app.database import SessionLocal

from app.services.notification_service import save_notification


from app.notification_config import (
    TELEGRAM_ENABLED,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)


def _truncate(text, limit=500):

    text = str(text)

    if len(text) > limit:
        return text[:limit] + "..."

    return text



def send_telegram(
    message,
    alert_id=None
):

    if not TELEGRAM_ENABLED:
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

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
                _truncate(response.text)
            )


    except Exception as e:


        save_notification(
            alert_id,
            "Telegram",
            "FAILED",
            _truncate(e)
        )