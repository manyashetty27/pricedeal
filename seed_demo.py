"""
seed_demo.py
-------------
Seeding script for hackathon demo & testing.
Populates local SQLite database (data/pricedeal.db) with 14-30 days of
synthetic historical price snapshots for key product scenarios:

1. Genuine Low (iPhone 15) - Price dropped to all-time recorded low.
2. Inflated Discount (Samsung 55" QLED TV) - Price artificially bumped up right before discount.
3. Typical Price (Sony WH-1000XM5) - Price normal within standard band.
4. Insufficient History (MacBook Air M2) - Only 2 snapshots recorded.

Usage:
    python seed_demo.py
"""

from datetime import datetime, timedelta, timezone
from database import init_db, add_or_get_product, record_price_with_timestamp, get_conn


def seed_data():
    init_db()
    print("Initializing demo seed data in SQLite database...")

    # Clean-up before seeding
    with get_conn() as conn:
        conn.execute("DELETE FROM price_history")
        conn.execute("DELETE FROM tracked_products")

    now = datetime.now(timezone.utc)

    # 1. Genuine Low: iPhone 15 128GB
    pid1 = add_or_get_product(
        query="iPhone 15 128GB",
        title="Apple iPhone 15 (128 GB) - Blue",
        source="Imagine Store",
        product_id="172839485019",
        product_link="https://www.google.com/shopping/product/172839485019",
        thumbnail="https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcR_iPhone15_demo",
    )
    # 20 days history: steady ~₹72,900, now dropped to ₹64,900
    for day in range(20, 0, -1):
        dt = (now - timedelta(days=day)).isoformat()
        price = 72900.0 if day > 2 else 64900.0
        record_price_with_timestamp(pid1, price, f"₹{price:,.0f}", dt)

    # 2. Inflated Discount: Samsung 55 inch QLED TV
    pid2 = add_or_get_product(
        query="Samsung 55 inch QLED TV",
        title="Samsung 55 inches 4K Ultra HD Smart QLED TV",
        source="ElectroKart",
        product_id="992837410293",
        product_link="https://www.google.com/shopping/product/992837410293",
        thumbnail="https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcR_SamsungTV_demo",
    )
    # 18 days history: usually ~₹52,000. 4 days ago raised to ₹68,000. Now ₹62,990 "Sale price".
    for day in range(18, 0, -1):
        dt = (now - timedelta(days=day)).isoformat()
        if day > 4:
            price = 52000.0
        elif day > 1:
            price = 68000.0
        else:
            price = 62990.0
        record_price_with_timestamp(pid2, price, f"₹{price:,.0f}", dt)

    # 3. Typical Price: Sony WH-1000XM5
    pid3 = add_or_get_product(
        query="Sony WH-1000XM5",
        title="Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        source="Croma",
        product_id="554920193847",
        product_link="https://www.google.com/shopping/product/554920193847",
        thumbnail="https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcR_SonyHeadphones_demo",
    )
    # 15 days history: hovering around ₹27,500
    for day in range(15, 0, -1):
        dt = (now - timedelta(days=day)).isoformat()
        price = 27490.0 if day % 2 == 0 else 27990.0
        record_price_with_timestamp(pid3, price, f"₹{price:,.0f}", dt)

    # 4. Insufficient Data: MacBook Air M2
    pid4 = add_or_get_product(
        query="MacBook Air M2",
        title="Apple MacBook Air Laptop M2 chip (8GB, 256GB SSD) - Starlight",
        source="Reliance Digital",
        product_id="882736451920",
        product_link="https://www.google.com/shopping/product/882736451920",
        thumbnail="https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcR_MacBookAir_demo",
    )
    # Only 2 snapshots
    dt1 = (now - timedelta(days=2)).isoformat()
    dt2 = (now - timedelta(days=1)).isoformat()
    record_price_with_timestamp(pid4, 92900.0, "₹92,900", dt1)
    record_price_with_timestamp(pid4, 91900.0, "₹91,900", dt2)

    print("SUCCESS: Demo data seeded successfully! 4 tracked products ready with historical snapshots.")


if __name__ == "__main__":
    seed_data()
