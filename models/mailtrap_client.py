# -*- coding: utf-8 -*-
"""
Mailtrap Sandbox Integration Client
Provides helper functions to send and test emails using Python smtplib and Mailtrap SMTP credentials.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_logger = logging.getLogger(__name__)

# Mailtrap Sandbox Configuration
MAILTRAP_HOST = "sandbox.smtp.mailtrap.io"
MAILTRAP_PORT = 2525
MAILTRAP_USER = "5bff227338f5dc"
MAILTRAP_PASSWORD = "8a08e6b78b7f05"
DEFAULT_SENDER = "Private Person <from@example.com>"
DEFAULT_RECEIVER = "A Test User <to@example.com>"


def send_mailtrap_email(
    sender=None,
    receiver=None,
    subject="Hi Mailtrap",
    message_text="This is a test e-mail message.",
    message_html=None,
):
    """Send an email to Mailtrap Sandbox using smtplib.

    :param sender: email address of the sender
    :param receiver: email address of the recipient
    :param subject: subject string
    :param message_text: plain text body
    :param message_html: optional HTML body
    :return: tuple (bool success, str message)
    """
    sender = sender or DEFAULT_SENDER
    receiver = receiver or DEFAULT_RECEIVER

    try:
        if message_html:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = receiver

            part_text = MIMEText(message_text or "", "plain", "utf-8")
            part_html = MIMEText(message_html, "html", "utf-8")
            msg.attach(part_text)
            msg.attach(part_html)
            raw_message = msg.as_string()
        else:
            raw_message = f"""\
Subject: {subject}
To: {receiver}
From: {sender}

{message_text}"""

        with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT, timeout=20) as server:
            server.starttls()
            server.login(MAILTRAP_USER, MAILTRAP_PASSWORD)
            server.sendmail(sender, receiver, raw_message)

        _logger.info("Mailtrap email sent successfully to %s", receiver)
        return True, f"Email sent successfully to Mailtrap ({receiver})"
    except Exception as exc:
        _logger.error("Failed to send email to Mailtrap: %s", str(exc))
        return False, str(exc)


def test_mailtrap_connection():
    """Verify SMTP connection and authentication with Mailtrap Sandbox.

    :return: tuple (bool success, str status_message)
    """
    try:
        with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT, timeout=10) as server:
            server.starttls()
            server.login(MAILTRAP_USER, MAILTRAP_PASSWORD)
            return True, "Connected & Authenticated to Mailtrap Sandbox"
    except Exception as exc:
        return False, str(exc)
