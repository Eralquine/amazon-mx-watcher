"""Extrae título, precio y disponibilidad de una página de producto de amazon.com.mx."""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT_SECONDS = 15

_PRICE_CLEAN_RE = re.compile(r"[^\d.,]")

OUT_OF_STOCK_MARKERS = (
    "no disponible",
    "actualmente no disponible",
    "no está disponible",
    "unavailable",
)


class ScrapeBlockedError(RuntimeError):
    """Amazon devolvió una página de bloqueo/CAPTCHA en vez del producto."""


@dataclass
class ProductSnapshot:
    url: str
    title: str | None
    price: float | None
    currency: str | None
    in_stock: bool
    availability_text: str | None


def fetch_product_page(url: str, session: requests.Session | None = None) -> str:
    http = session or requests
    response = http.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def parse_price(raw_text: str) -> float | None:
    """Convierte un precio con formato MX ("$1,234.50") a float."""
    cleaned = _PRICE_CLEAN_RE.sub("", raw_text).strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_product_page(html: str, url: str) -> ProductSnapshot:
    soup = BeautifulSoup(html, "lxml")

    if _looks_like_block_page(soup):
        raise ScrapeBlockedError(
            "Amazon devolvió una página de verificación/CAPTCHA en vez del producto. "
            "Aumenta el intervalo de revisión e inténtalo más tarde."
        )

    title = _extract_title(soup)
    price = _extract_price(soup)
    availability_text = _extract_availability_text(soup)
    in_stock = _is_in_stock(availability_text, price)

    return ProductSnapshot(
        url=url,
        title=title,
        price=price,
        currency="MXN" if price is not None else None,
        in_stock=in_stock,
        availability_text=availability_text,
    )


def _looks_like_block_page(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return (
        "escribe los caracteres" in text
        or "enter the characters" in text
        or "api-services-support@amazon.com" in text
    )


def _extract_title(soup: BeautifulSoup) -> str | None:
    node = soup.select_one("#productTitle")
    return node.get_text(strip=True) if node else None


def _extract_price(soup: BeautifulSoup) -> float | None:
    selectors = [
        "#corePrice_feature_div span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div span.a-offscreen",
        "span.a-price span.a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            price = parse_price(node.get_text())
            if price is not None:
                return price
    return None


def _extract_availability_text(soup: BeautifulSoup) -> str | None:
    node = soup.select_one("#availability span") or soup.select_one("#availability")
    return node.get_text(strip=True) if node else None


def _is_in_stock(availability_text: str | None, price: float | None) -> bool:
    if availability_text:
        lowered = availability_text.lower()
        if any(marker in lowered for marker in OUT_OF_STOCK_MARKERS):
            return False
        return True
    # Sin texto explícito de disponibilidad: si hay precio visible, se asume en stock.
    return price is not None
