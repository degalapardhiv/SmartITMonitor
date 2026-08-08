import smtplib

from email.mime.text import MIMEText

from app.database import SessionLocal

from app.settings_model import SystemSetting

from app.email_settings_model import EmailSetting
from app.email_history_model import EmailHistory
from app.services.notification_service import save_notification



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



def send_email(subject, message):

    if not email_enabled():

        return


    db = SessionLocal()


    try:

        config = (
            db.query(EmailSetting)
            .first()
        )


        if not config:

            print(
                "Email config missing"
            )

            return


        msg = MIMEText(message)


        msg["Subject"] = subject
        msg["From"] = config.username
        msg["To"] = config.receiver



        server = smtplib.SMTP(
            config.smtp_server,
            config.smtp_port
        )


        server.starttls()


        server.login(
            config.username,
            config.password
        )


        server.send_message(msg)


        save_notification(
            None,
            "Email",
            "SENT",
            subject
        )


        history = EmailHistory(
            receiver=config.receiver,
            subject=subject,
            status="SENT"
        )

        db.add(history)
        db.commit()


        server.quit()



    except Exception as e:

        print(
            "Email error:",
            e
        )


    finally:

        db.close()
