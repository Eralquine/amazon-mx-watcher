from pathlib import Path

import requests

from amazon_mx_watcher import monitor
from amazon_mx_watcher.config import ProductConfig
from amazon_mx_watcher.storage import StateStore

FIXTURES = Path(__file__).parent / "fixtures"


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, subject: str, message: str) -> None:
        self.sent.append((subject, message))


def _patch_fetch(monkeypatch, fixture_name: str) -> None:
    html = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    monkeypatch.setattr(monitor, "fetch_product_page", lambda url, session=None: html)


def test_notifies_on_restock(tmp_path, monkeypatch):
    _patch_fetch(monkeypatch, "in_stock.html")
    store = StateStore(tmp_path / "state.db")
    store.upsert("https://example.com/dp/1", price=8999.0, in_stock=False)

    product = ProductConfig(url="https://example.com/dp/1", nickname="Consola X")
    notifier = FakeNotifier()

    monitor.check_product(product, store, [notifier], requests.Session())

    assert len(notifier.sent) == 1
    assert "De vuelta en stock" in notifier.sent[0][0]


def test_does_not_notify_when_still_out_of_stock(tmp_path, monkeypatch):
    _patch_fetch(monkeypatch, "out_of_stock.html")
    store = StateStore(tmp_path / "state.db")
    store.upsert("https://example.com/dp/2", price=None, in_stock=False)

    product = ProductConfig(url="https://example.com/dp/2", nickname="Tarjeta Y")
    notifier = FakeNotifier()

    monitor.check_product(product, store, [notifier], requests.Session())

    assert notifier.sent == []


def test_notifies_on_price_drop_to_target(tmp_path, monkeypatch):
    _patch_fetch(monkeypatch, "in_stock.html")
    store = StateStore(tmp_path / "state.db")
    store.upsert("https://example.com/dp/1", price=9999.0, in_stock=True)

    product = ProductConfig(url="https://example.com/dp/1", nickname="Consola X", target_price=9000.0)
    notifier = FakeNotifier()

    monitor.check_product(product, store, [notifier], requests.Session())

    assert len(notifier.sent) == 1
    assert "Bajó de precio" in notifier.sent[0][0]
