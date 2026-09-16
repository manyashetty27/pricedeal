"""
scheduler.py
-------------
Optional standalone script to refresh prices for every tracked product
without opening the Streamlit UI. Intended to be run on a schedule
(cron, GitHub Actions, Windows Task Scheduler, etc.) so price history
builds up automatically in the run-up to a sale event.

Usage:
    python scheduler.py

Example cron entry (every day at 9am):
    0 9 * * * cd /path/to/sahi-daam && /path/to/venv/bin/python scheduler.py >> log.txt 2>&1
"""

import sys
from datetime import datetime

from database import get_all_tracked_products, get_products_for_query, init_db, record_price
from serpapi_client import SerpApiClient, SerpApiError


def main():
    init_db()
    try:
        client = SerpApiClient()
    except SerpApiError as e:
        print(f"[{datetime.utcnow().isoformat()}] Startup error: {e}")
        sys.exit(1)

    tracked = get_all_tracked_products()
    if not tracked:
        print("Nothing is being tracked yet. Add products via the Streamlit app first.")
        return

    queries = sorted(set(t["query"] for t in tracked))
    updated, failed = 0, 0

    for q in queries:
        try:
            fresh_results = client.search_shopping(q)
        except SerpApiError as e:
            print(f"[{datetime.utcnow().isoformat()}] Failed to refresh '{q}': {e}")
            failed += 1
            continue

        by_key = {(r["title"], r.get("source")): r for r in fresh_results}
        for t in get_products_for_query(q):
            match = by_key.get((t["title"], t["source"]))
            if match and match.get("extracted_price") is not None:
                record_price(t["id"], match["extracted_price"], match.get("price") or "")
                updated += 1

    print(f"[{datetime.utcnow().isoformat()}] Done. Snapshots recorded: {updated}, queries failed: {failed}")


if __name__ == "__main__":
    main()
