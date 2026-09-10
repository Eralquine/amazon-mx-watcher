from pathlib import Path

import pytest

from amazon_mx_watcher.scraper import ScrapeBlockedError, parse_price, parse_product_page

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_price_handles_mx_format():
    assert parse_price("$8,999.00") == 8999.00
    assert parse_price("$1,234") == 1234.0
    assert parse_price("") is None
    assert parse_price("gratis") is None


def test_parse_in_stock_product():
    snapshot = parse_product_page(_load("in_stock.html"), url="https://example.com/dp/1")
    assert snapshot.title == "Consola de videojuegos X 1TB"
    assert snapshot.price == 8999.00
    assert snapshot.currency == "MXN"
    assert snapshot.in_stock is True


def test_parse_out_of_stock_product():
    snapshot = parse_product_page(_load("out_of_stock.html"), url="https://example.com/dp/2")
    assert snapshot.title == "Tarjeta gráfica Y 16GB"
    assert snapshot.price is None
    assert snapshot.in_stock is False


def test_parse_blocked_page_raises():
    with pytest.raises(ScrapeBlockedError):
        parse_product_page(_load("blocked.html"), url="https://example.com/dp/3")
