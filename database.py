"""
database.py
------------
Lightweight SQLite storage for tracked products and their price history.
No external DB server needed — keeps the project easy to run locally,
which matters for the hackathon demo (judges run this on their machine).
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

DB_PATH = Path(__file__).parent / "data" / "pricedeal.db"


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db():
    """Initialize database tables and indexes."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracked_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT,
                product_id TEXT,
                product_link TEXT,
                thumbnail TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(query, title, source)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL,
                raw_price TEXT,
                checked_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES tracked_products(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_product_time
            ON price_history(product_id, checked_at)
        """)


def add_or_get_product(query: str, title: str, source: str, product_id: str,
                        product_link: str, thumbnail: str) -> int:
    """Insert product into tracked_products if not present and return product ID."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id FROM tracked_products WHERE query=? AND title=? AND source=?",
            (query, title, source),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            """INSERT INTO tracked_products
               (query, title, source, product_id, product_link, thumbnail, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (query, title, source, product_id, product_link, thumbnail, get_utc_now_iso()),
        )
        return cur.lastrowid


def record_price(product_row_id: int, price: float, raw_price: str):
    """Save a price snapshot for a tracked product."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO price_history (product_id, price, raw_price, checked_at) VALUES (?, ?, ?, ?)",
            (product_row_id, price, raw_price, get_utc_now_iso()),
        )


def record_price_with_timestamp(product_row_id: int, price: float, raw_price: str, checked_at: str):
    """Save a price snapshot with a custom ISO timestamp (useful for seeding history)."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO price_history (product_id, price, raw_price, checked_at) VALUES (?, ?, ?, ?)",
            (product_row_id, price, raw_price, checked_at),
        )


def get_all_tracked_products() -> List[Dict[str, Any]]:
    """Fetch all tracked products ordered by creation date as a list of dicts."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tracked_products ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_price_history(product_row_id: int) -> List[Dict[str, Any]]:
    """Fetch full price history for a given product ID in chronological order as a list of dicts."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM price_history WHERE product_id=? ORDER BY checked_at ASC",
            (product_row_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_products_for_query(query: str) -> List[Dict[str, Any]]:
    """Fetch tracked products matching a search query as a list of dicts."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tracked_products WHERE query=? ORDER BY created_at ASC",
            (query,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_tracked_product(product_row_id: int) -> bool:
    """Delete a tracked product and its price history."""
    with get_conn() as conn:
        conn.execute("DELETE FROM price_history WHERE product_id=?", (product_row_id,))
        cur = conn.execute("DELETE FROM tracked_products WHERE id=?", (product_row_id,))
        return cur.rowcount > 0


def get_product_stats(product_row_id: int) -> Dict[str, Optional[float]]:
    """Compute summary statistics for a tracked product's price history."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price) as avg_price,
                COUNT(price) as snapshot_count
            FROM price_history
            WHERE product_id=? AND price IS NOT NULL
        """, (product_row_id,)).fetchone()
        
        if not row or row["snapshot_count"] == 0:
            return {
                "min_price": None,
                "max_price": None,
                "avg_price": None,
                "snapshot_count": 0,
            }
        
        return {
            "min_price": float(row["min_price"]),
            "max_price": float(row["max_price"]),
            "avg_price": float(row["avg_price"]),
            "snapshot_count": int(row["snapshot_count"]),
        }
