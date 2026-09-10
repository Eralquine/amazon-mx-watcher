"""Bucle de monitoreo: revisa cada producto y decide si hay que notificar."""

from __future__ import annotations

import logging
import time

import requests

from .config import AppConfig, ProductConfig
from .notifiers import EmailNotifier, Notifier, TelegramNotifier
from .scraper import ScrapeBlockedError, fetch_product_page, parse_product_page
from .storage import StateStore

logger = logging.getLogger(__name__)


def build_notifiers(config: AppConfig) -> list[Notifier]:
    notifiers: list[Notifier] = []
    if config.telegram:
        notifiers.append(TelegramNotifier(config.telegram))
    if config.smtp:
        notifiers.append(EmailNotifier(config.smtp))
    return notifiers


def _notify_all(notifiers: list[Notifier], subject: str, message: str) -> None:
    if not notifiers:
        logger.warning("Sin notificadores configurados. Mensaje: %s | %s", subject, message)
        return
    for notifier in notifiers:
        try:
            notifier.send(subject, message)
        except Exception:
            logger.exception("Fallo al enviar notificación con %s", type(notifier).__name__)


def check_product(
    product: ProductConfig,
    store: StateStore,
    notifiers: list[Notifier],
    session: requests.Session,
) -> None:
    try:
        html = fetch_product_page(product.url, session=session)
        snapshot = parse_product_page(html, product.url)
    except ScrapeBlockedError as exc:
        logger.warning("Bloqueado por Amazon al revisar %s: %s", product.nickname, exc)
        return
    except requests.RequestException as exc:
        logger.warning("Error de red al revisar %s: %s", product.nickname, exc)
        return

    previous = store.get(product.url)
    store.upsert(product.url, snapshot.price, snapshot.in_stock)

    title = snapshot.title or product.nickname
    price_text = f"${snapshot.price:,.2f} MXN" if snapshot.price is not None else "precio no disponible"

    restocked = (
        product.notify_on_restock
        and snapshot.in_stock
        and previous is not None
        and not previous.last_in_stock
    )
    first_seen_in_stock = product.notify_on_restock and snapshot.in_stock and previous is None

    price_hit_target = (
        product.target_price is not None
        and snapshot.price is not None
        and snapshot.price <= product.target_price
        and (previous is None or previous.last_price != snapshot.price)
    )

    if restocked or first_seen_in_stock:
        _notify_all(
            notifiers,
            subject=f"De vuelta en stock: {title}",
            message=f"{title}\n{price_text}\n{product.url}",
        )
    elif price_hit_target:
        _notify_all(
            notifiers,
            subject=f"Bajó de precio: {title}",
            message=(
                f"{title}\n{price_text} (objetivo: ${product.target_price:,.2f} MXN)\n{product.url}"
            ),
        )
    else:
        logger.info(
            "%s: en_stock=%s precio=%s (sin cambios notificables)",
            title,
            snapshot.in_stock,
            price_text,
        )


def run_once(config: AppConfig, store: StateStore) -> None:
    notifiers = build_notifiers(config)
    if not config.products:
        logger.warning("No hay productos configurados en products.yaml")
        return

    with requests.Session() as session:
        for product in config.products:
            check_product(product, store, notifiers, session)


def run_forever(config: AppConfig, store: StateStore) -> None:
    logger.info(
        "Iniciando monitoreo de %d producto(s) cada %d segundos",
        len(config.products),
        config.poll_interval_seconds,
    )
    while True:
        run_once(config, store)
        time.sleep(config.poll_interval_seconds)
