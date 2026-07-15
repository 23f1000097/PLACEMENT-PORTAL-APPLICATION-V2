import os
import smtplib
from email.message import EmailMessage

from flask import current_app


def get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in {"true", "1", "yes"},
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() in {"true", "1", "yes"},
        "from_address": os.getenv("SMTP_FROM", os.getenv("EMAIL_FROM", "no-reply@placement-portal.local")),
    }


def send_email(subject, body, recipients, html=None, attachments=None):
    if not recipients:
        return False

    config = get_smtp_config()

    if not config["username"] or not config["password"]:
        raise RuntimeError("SMTP credentials are not configured")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_address"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    for filename, filepath in (attachments or []):
        with open(filepath, "rb") as attachment_file:
            message.add_attachment(
                attachment_file.read(),
                maintype="application",
                subtype="octet-stream",
                filename=filename,
            )

    if config["use_ssl"]:
        with smtplib.SMTP_SSL(config["host"], config["port"]) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(config["host"], config["port"]) as smtp:
            smtp.ehlo()
            if config["use_tls"]:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(config["username"], config["password"])
            smtp.send_message(message)

    return True
