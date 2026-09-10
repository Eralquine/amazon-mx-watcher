from __future__ import annotations

import requests

from ..config import TelegramConfig

TELEGRAM_API_TIMEOUT_SECONDS = 10


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self._config = config

    def send(self, subject: str, message: str) -> None:
        url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
        text = f"*{subject}*\n{message}"
        response = requests.post(
            url,
            json={
                "chat_id": self._config.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=TELEGRAM_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
