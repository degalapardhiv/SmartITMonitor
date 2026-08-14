import requests

from app.database import SessionLocal

from app.services.notification_service import save_notification


def _truncate(text, limit=500):

    text = str(text)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def send_telegram(
    message,
    alert_id=None
):

    from app.settings_center_service import get_telegram_config

    config = get_telegram_config()

    if not config["enabled"]:
        return False

    bot_token = config["bot_token"]
    chat_id = config["chat_id"]

    if not bot_token or not chat_id:
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{bot_token}/sendMessage"
    )


    try:

        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
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

            return True


        else:

            save_notification(
                alert_id,
                "Telegram",
                "FAILED",
                _truncate(response.text)
            )

            return False


    except Exception as e:


        save_notification(
            alert_id,
            "Telegram",
            "FAILED",
            _truncate(e)
        )

        return False
