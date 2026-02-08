import smtplib
from email.message import EmailMessage
from app.core.config import get_settings


def send_email(to_email: str, subject: str, html_body: str):
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_pass or not settings.smtp_from:
        raise RuntimeError("SMTP settings are not configured")

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg)
