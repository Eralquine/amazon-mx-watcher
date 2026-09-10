from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import SmtpConfig

SMTP_TIMEOUT_SECONDS = 15


class EmailNotifier:
    def __init__(self, config: SmtpConfig) -> None:
        self._config = config

    def send(self, subject: str, message: str) -> None:
        email = EmailMessage()
        email["Subject"] = subject
        email["From"] = self._config.from_addr
        email["To"] = self._config.to_addr
        email.set_content(message)

        with smtplib.SMTP(self._config.host, self._config.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.starttls()
            if self._config.username and self._config.password:
                smtp.login(self._config.username, self._config.password)
            smtp.send_message(email)
