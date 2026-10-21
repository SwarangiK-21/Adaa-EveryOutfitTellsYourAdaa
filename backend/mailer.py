"""Sends Adaa's few emails (only "reset your password" for now) through any SMTP service.

Set ADAA_SMTP_HOST, ADAA_SMTP_PORT, ADAA_SMTP_USER, ADAA_SMTP_PASSWORD and ADAA_MAIL_FROM.
Without them (e.g. on your own laptop) the email is printed in the backend terminal instead.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

import config

log = logging.getLogger("adaa.mail")


def send_email(to: str, subject: str, body: str) -> None:
    if not config.SMTP_HOST:
        print(f"\n--- Email not sent (no ADAA_SMTP_HOST set). It would go to {to} ---\n{subject}\n\n{body}\n---\n", flush=True)
        return
    msg = EmailMessage()
    msg["From"] = f"Adaa <{config.MAIL_FROM}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        if config.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(config.SMTP_HOST, 465, context=ssl.create_default_context(), timeout=20) as smtp:
                _send(smtp, msg)
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                _send(smtp, msg)
    except (OSError, smtplib.SMTPException):
        # Runs after the reply was sent, so the person sees the same message either way; note it for the admin.
        log.exception("Couldn't send email to %s", to)


def _send(smtp, msg):
    if config.SMTP_USER:
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
    smtp.send_message(msg)
