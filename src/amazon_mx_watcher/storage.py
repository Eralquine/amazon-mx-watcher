"""Persistencia del último estado conocido de cada producto (SQLite)."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProductState:
    url: str
    last_price: float | None
    last_in_stock: bool
    last_checked_at: float


class StateStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_state (
                url TEXT PRIMARY KEY,
                last_price REAL,
                last_in_stock INTEGER NOT NULL,
                last_checked_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, url: str) -> ProductState | None:
        row = self._conn.execute(
            "SELECT url, last_price, last_in_stock, last_checked_at "
            "FROM product_state WHERE url = ?",
            (url,),
        ).fetchone()
        if row is None:
            return None
        return ProductState(
            url=row[0], last_price=row[1], last_in_stock=bool(row[2]), last_checked_at=row[3]
        )

    def upsert(self, url: str, price: float | None, in_stock: bool) -> None:
        self._conn.execute(
            """
            INSERT INTO product_state (url, last_price, last_in_stock, last_checked_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                last_price = excluded.last_price,
                last_in_stock = excluded.last_in_stock,
                last_checked_at = excluded.last_checked_at
            """,
            (url, price, int(in_stock), time.time()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
