"""Carga de configuración: products.yaml y variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

MIN_POLL_INTERVAL_SECONDS = 120
DEFAULT_POLL_INTERVAL_SECONDS = 600


@dataclass
class ProductConfig:
    url: str
    nickname: str
    target_price: float | None = None
    notify_on_restock: bool = True


@dataclass
class SearchConfig:
    """Vigila los resultados de búsqueda de Amazon MX en vez de una URL de producto fija.

    Útil para productos que todavía no existen como listado (p. ej. un lanzamiento
    aún no publicado): se avisa en cuanto aparece un resultado nuevo que coincide.
    """

    query: str
    nickname: str
    keywords: list[str] = field(default_factory=list)
    max_price: float | None = None


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    from_addr: str
    to_addr: str


@dataclass
class AppConfig:
    poll_interval_seconds: int
    products: list[ProductConfig] = field(default_factory=list)
    searches: list[SearchConfig] = field(default_factory=list)
    telegram: TelegramConfig | None = None
    smtp: SmtpConfig | None = None


def load_env(env_path: Path | None = None) -> None:
    load_dotenv(dotenv_path=env_path, override=False)


def _telegram_config_from_env() -> TelegramConfig | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if token and chat_id:
        return TelegramConfig(bot_token=token, chat_id=chat_id)
    return None


def _smtp_config_from_env() -> SmtpConfig | None:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("SMTP_FROM", "").strip()
    to_addr = os.getenv("SMTP_TO", "").strip()
    if host and from_addr and to_addr:
        return SmtpConfig(
            host=host,
            port=int(os.getenv("SMTP_PORT", "587")),
            username=username,
            password=password,
            from_addr=from_addr,
            to_addr=to_addr,
        )
    return None


def load_products_file(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Copia products.example.yaml a products.yaml y "
            "ajusta tus productos."
        )

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    poll_interval = int(raw.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
    if poll_interval < MIN_POLL_INTERVAL_SECONDS:
        poll_interval = MIN_POLL_INTERVAL_SECONDS

    products = [
        ProductConfig(
            url=item["url"],
            nickname=item.get("nickname", item["url"]),
            target_price=(
                float(item["target_price"]) if item.get("target_price") is not None else None
            ),
            notify_on_restock=bool(item.get("notify_on_restock", True)),
        )
        for item in raw.get("products", [])
    ]

    searches = [
        SearchConfig(
            query=item["query"],
            nickname=item.get("nickname", item["query"]),
            keywords=[str(k).lower() for k in item.get("keywords", [])],
            max_price=(float(item["max_price"]) if item.get("max_price") is not None else None),
        )
        for item in raw.get("searches", [])
    ]

    return AppConfig(
        poll_interval_seconds=poll_interval,
        products=products,
        searches=searches,
        telegram=_telegram_config_from_env(),
        smtp=_smtp_config_from_env(),
    )


def save_products_file(path: Path, config: AppConfig) -> None:
    data = {
        "poll_interval_seconds": config.poll_interval_seconds,
        "products": [
            {
                "url": p.url,
                "nickname": p.nickname,
                "target_price": p.target_price,
                "notify_on_restock": p.notify_on_restock,
            }
            for p in config.products
        ],
        "searches": [
            {
                "query": s.query,
                "nickname": s.nickname,
                "keywords": s.keywords,
                "max_price": s.max_price,
            }
            for s in config.searches
        ],
    }
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
