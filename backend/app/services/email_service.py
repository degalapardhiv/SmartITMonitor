import smtplib
import logging

from email.mime.text import MIMEText

from app.database import SessionLocal

from app.settings_model import SystemSetting

from app.email_settings_model import EmailSetting
from app.email_history_model import EmailHistory
from app.services.notification_service import save_notification


logger = logging.getLogger(__name__)


def _truncate(text, limit=500):

    text = str(text)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def email_enabled():

    db = SessionLocal()

    try:

        setting = (
            db.query(SystemSetting)
            .filter(
                SystemSetting.key == "email"
            )
            .first()
        )


        if setting:

            return setting.value


        return False


    finally:

        db.close()



def send_email(subject, message, alert_id=None):

    if not email_enabled():

        return False


    db = SessionLocal()


    try:

        config = (
            db.query(EmailSetting)
            .first()
        )


        if not config:

            logger.warning("Email config missing; skipping send")

            return False


        msg = MIMEText(message)


        msg["Subject"] = subject
        msg["From"] = config.username
        msg["To"] = config.receiver


        server = None

        try:

            if config.smtp_port == 465:

                server = smtplib.SMTP_SSL(
                    config.smtp_server,
                    config.smtp_port,
                    timeout=15
                )

            else:

                server = smtplib.SMTP(
                    config.smtp_server,
                    config.smtp_port,
                    timeout=15
                )

                server.starttls()


            server.login(
                config.username,
                config.password
            )


            server.send_message(msg)

        finally:

            if server is not None:

                try:
                    server.quit()
                except Exception:
                    pass


        save_notification(
            alert_id,
            "Email",
            "SENT",
            _truncate(subject)
        )


        history = EmailHistory(
            receiver=config.receiver,
            subject=subject,
            status="SENT"
        )

        db.add(history)
        db.commit()

        return True


    except Exception as e:

        logger.error(
            "Email error: %s",
            e,
        )

        try:

            save_notification(
                alert_id,
                "Email",
                "FAILED",
                _truncate(e)
            )

        except Exception:
            pass

        try:

            db.add(
                EmailHistory(
                    receiver=config.receiver
                    if config
                    else "unknown",
                    subject=subject,
                    status="FAILED"
                )
            )

            db.commit()

        except Exception:
            db.rollback()

        return False


    finally:

        db.close()
