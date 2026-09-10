from pathlib import Path

import requests

from amazon_mx_watcher import monitor
from amazon_mx_watcher.config import ProductConfig, SearchConfig
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


def _patch_fetch_search(monkeypatch, fixture_name: str) -> None:
    html = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    monkeypatch.setattr(monitor, "fetch_search_page", lambda query, session=None: html)


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


def test_search_first_check_establishes_baseline_without_notifying(tmp_path, monkeypatch):
    _patch_fetch_search(monkeypatch, "search_results.html")
    store = StateStore(tmp_path / "state.db")

    search = SearchConfig(query="consola x", nickname="Consola X")
    notifier = FakeNotifier()

    monitor.check_search(search, store, [notifier], requests.Session())

    assert notifier.sent == []
    assert store.has_seen_asin("consola x", "B0NEWITEM1")


def test_search_notifies_on_new_asin_after_baseline(tmp_path, monkeypatch):
    _patch_fetch_search(monkeypatch, "search_results.html")
    store = StateStore(tmp_path / "state.db")
    store.mark_asin_seen("consola x", "B0OTHERITEM")  # baseline ya establecida

    search = SearchConfig(query="consola x", nickname="Consola X")
    notifier = FakeNotifier()

    monitor.check_search(search, store, [notifier], requests.Session())

    assert len(notifier.sent) == 1
    subject, message = notifier.sent[0]
    assert "Nuevo resultado" in subject
    assert "B0NEWITEM1" in message


def test_search_filters_by_keyword_and_max_price(tmp_path, monkeypatch):
    _patch_fetch_search(monkeypatch, "search_results.html")
    store = StateStore(tmp_path / "state.db")
    store.mark_asin_seen("consola x", "B0NEWITEM1")
    store.mark_asin_seen("consola x", "B0OTHERITEM")

    # Simula que aparece un resultado nuevo que no cumple el filtro de precio.
    store._conn.execute("DELETE FROM search_seen_asin WHERE asin = 'B0OTHERITEM'")
    store._conn.commit()

    search = SearchConfig(query="consola x", nickname="Consola X", max_price=1.0)
    notifier = FakeNotifier()

    monitor.check_search(search, store, [notifier], requests.Session())

    assert notifier.sent == []
