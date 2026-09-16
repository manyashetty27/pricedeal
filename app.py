"""
app.py
-------
PriceDeal — Festival Sale Price Watch
Streamlit dashboard: search a product on Google Shopping (via SerpApi),
track it over time, compare live sellers, and see whether a "sale" price
is a genuine low or an inflated-then-discounted price.

Run:
    streamlit run app.py
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from anomaly import evaluate_price
from database import (
    add_or_get_product,
    delete_tracked_product,
    get_all_tracked_products,
    get_price_history,
    get_products_for_query,
    get_product_stats,
    init_db,
    record_price,
)
from serpapi_client import SerpApiClient, SerpApiError

st.set_page_config(
    page_title="PriceDeal — Festival Sale Price Watch",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


# ---------- Helpers ----------

@st.cache_resource
def get_client(api_key: str = None) -> SerpApiClient:
    key = api_key or os.environ.get("SERPAPI_API_KEY") or st.session_state.get("api_key")
    if not key:
        return None
    try:
        return SerpApiClient(api_key=key)
    except SerpApiError:
        return None


def price_history_df(product_row_id: int) -> pd.DataFrame:
    rows = get_price_history(product_row_id)
    if not rows:
        return pd.DataFrame(columns=["checked_at", "price"])
    df = pd.DataFrame([dict(r) for r in rows])
    df["checked_at"] = pd.to_datetime(df["checked_at"])
    return df[["checked_at", "price"]]


VERDICT_STYLE = {
    "genuine_low": ("✅ Genuine Low", "success"),
    "inflated_discount": ("🚩 Possibly Inflated Discount", "error"),
    "no_change": ("➖ Typical Price", "info"),
    "insufficient_data": ("⏳ Not Enough History Yet", "warning"),
}


# ---------- Sidebar ----------

with st.sidebar:
    st.title("🏷️ PriceDeal")
    st.caption("Festival Sale Price Watch — powered by SerpApi")

    env_key = os.environ.get("SERPAPI_API_KEY")
    if not env_key:
        api_key_input = st.text_input(
            "SerpApi API key",
            type="password",
            help="Get a free key (250 searches/month) at serpapi.com",
            value=st.session_state.get("api_key", ""),
        )
        if api_key_input:
            st.session_state["api_key"] = api_key_input
    else:
        st.success("🔑 SerpApi API key loaded from environment!")

    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Search any product below.\n"
        "2. Add listings to your watchlist.\n"
        "3. Re-check prices over days (or use `scheduler.py`) to build price history.\n"
        "4. Once enough data is recorded, PriceDeal analyzes whether a 'sale' price is "
        "a **genuine bargain** or **artificially inflated** prior to the discount."
    )
    
    st.divider()
    st.subheader("🧪 Hackathon Demo Controls")
    if st.button("🌱 Seed Demo Price History", use_container_width=True, help="Populate SQLite with 14-30 days of realistic price snapshots for instant demo testing"):
        from seed_demo import seed_data
        seed_data()
        st.success("Demo dataset seeded! Tracked items updated.")
        st.rerun()

    st.divider()
    st.caption("Built for SerpApi India Hackathon 2026 · Track: Commerce & Market Intelligence")


client = get_client()

# Header Warning if Key Missing
if not client:
    st.info(
        "💡 **No SerpApi Key Provided**: You can enter your free SerpApi key in the sidebar for live Google Shopping searches, or click **'🌱 Seed Demo Price History'** in the sidebar to test the app instantly with pre-built historical data."
    )

# ---------- Search & Track ----------

st.header("🔍 Search a product")
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Product name", placeholder="e.g. iPhone 15 Pro, Samsung 55 inch QLED TV, Sony WH-1000XM5")
with col2:
    st.write("")
    st.write("")
    search_clicked = st.button("Search Live Deals", type="primary", use_container_width=True)

if search_clicked and query:
    if not client:
        st.error("🔑 A SerpApi API Key is required to perform live search on Google Shopping. Paste your free key into the sidebar!")
        st.markdown(
            "👉 **Don't have a key?** Get a free key (250 searches/month) at [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up), "
            "or click the button below to populate the dashboard with realistic demo data (iPhone 15, TV, Headphones, MacBook):"
        )
        if st.button("🌱 Load Demo Products & Price History Now"):
            from seed_demo import seed_data
            seed_data()
            st.success("Loaded demo products into watchlist below!")
            st.rerun()
    else:
        with st.spinner("Searching Google Shopping via SerpApi..."):
            try:
                results = client.search_shopping(query)
                st.session_state["last_query"] = query
                st.session_state["last_results"] = results
            except SerpApiError as e:
                st.error(f"SerpApi error: {e}")
                st.session_state["last_results"] = []

results = st.session_state.get("last_results", [])
if results and st.session_state.get("last_query") == query:
    st.subheader(f"Results for “{query}”")
    for idx, r in enumerate(results[:10]):
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 4, 1.5])
            with c1:
                if r.get("thumbnail"):
                    st.image(r["thumbnail"], width=90)
                else:
                    st.write("📦")
            with c2:
                st.markdown(f"**{r['title']}**")
                rating_str = f" ⭐ {r['rating']}" if r.get("rating") else ""
                reviews_str = f" ({r['reviews']} reviews)" if r.get("reviews") else ""
                st.caption(f"{r.get('source', 'Unknown seller')} · {r.get('price', 'N/A')}{rating_str}{reviews_str}")
                if r.get("product_link"):
                    st.markdown(f"[🔗 View Listing]({r['product_link']})")
            with c3:
                track_btn = st.button("Track Price", key=f"track_{r.get('product_id')}_{idx}")
                if track_btn:
                    if r.get("extracted_price") is None:
                        st.error("No numeric price available for this listing.")
                    else:
                        pid = add_or_get_product(
                            query=query,
                            title=r["title"],
                            source=r.get("source") or "Unknown",
                            product_id=r.get("product_id") or "",
                            product_link=r.get("product_link") or "",
                            thumbnail=r.get("thumbnail") or "",
                        )
                        record_price(pid, r["extracted_price"], r.get("price") or "")
                        st.success("Added to tracked products!")
                        st.rerun()

                # Seller Breakdown Button
                if client and r.get("product_id"):
                    with st.popover("Compare Sellers"):
                        st.markdown(f"**Live Sellers for Product ID:** `{r['product_id']}`")
                        sellers = client.get_product_sellers(r["product_id"])
                        if sellers:
                            seller_df = pd.DataFrame(sellers)[["name", "price"]]
                            seller_df.columns = ["Seller", "Price"]
                            st.dataframe(seller_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No multi-seller data available for this listing.")

st.divider()

# ---------- Tracked products / dashboard ----------

st.header("📊 Tracked Products & Price Watch")

tracked = get_all_tracked_products()

if not tracked:
    st.info("You are not tracking any products yet. Click **'🌱 Seed Demo Price History'** in the sidebar to load pre-built demo data or search above to track live items!")
else:
    # Summary Cards & Actions Bar
    total_count = len(tracked)
    verdict_counts = {"genuine_low": 0, "inflated_discount": 0, "no_change": 0, "insufficient_data": 0}
    
    # Pre-calculate verdicts for counters
    tracked_with_verdict = []
    for t in tracked:
        history = get_price_history(t["id"])
        if history:
            current = history[-1]
            past_history = history[:-1]
            verdict = evaluate_price(current["price"], past_history)
            verdict_counts[verdict.verdict] += 1
            tracked_with_verdict.append((t, history, current, past_history, verdict))

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Tracked Items", total_count)
    mc2.metric("✅ Genuine Deals", verdict_counts["genuine_low"])
    mc3.metric("🚩 Inflated Discounts", verdict_counts["inflated_discount"])
    mc4.metric("⏳ Awaiting History", verdict_counts["insufficient_data"])

    st.write("")
    
    act_col1, act_col2, act_col3 = st.columns([2, 2, 2])
    with act_col1:
        refresh_btn = st.button("🔄 Refresh All Prices", use_container_width=True)
    with act_col2:
        # Export CSV feature
        csv_data = []
        for t, history, current, past, v in tracked_with_verdict:
            stats = get_product_stats(t["id"])
            csv_data.append({
                "ID": t["id"],
                "Query": t["query"],
                "Title": t["title"],
                "Source": t["source"],
                "Current Price": current["price"],
                "Lowest Recorded": stats["min_price"],
                "Average Recorded": stats["avg_price"],
                "Highest Recorded": stats["max_price"],
                "Verdict": v.verdict,
                "Explanation": v.explanation,
                "Snapshots": stats["snapshot_count"],
            })
        export_df = pd.DataFrame(csv_data)
        st.download_button(
            label="📥 Export History (CSV)",
            data=export_df.to_csv(index=False),
            file_name=f"pricedeal_price_watch_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Filter Bar
    filter_col1, filter_col2 = st.columns([2, 3])
    with filter_col1:
        verdict_filter = st.selectbox(
            "Filter by Status",
            options=["All Statuses", "Genuine Low ✅", "Inflated Discount 🚩", "Typical Price ➖", "Insufficient Data ⏳"],
        )
    with filter_col2:
        search_filter = st.text_input("Filter watchlist by name", placeholder="Type keyword to filter...")

    if refresh_btn:
        if not client:
            st.error("SerpApi API key required to perform price refreshes.")
        else:
            with st.spinner("Re-checking current live prices..."):
                queries = sorted(set(t["query"] for t in tracked))
                for q in queries:
                    try:
                        fresh_results = client.search_shopping(q)
                    except SerpApiError as e:
                        st.error(f"Could not refresh '{q}': {e}")
                        continue
                    by_key = {(r["title"], r.get("source")): r for r in fresh_results}
                    for t in get_products_for_query(q):
                        match = by_key.get((t["title"], t["source"]))
                        if match and match.get("extracted_price") is not None:
                            record_price(t["id"], match["extracted_price"], match.get("price") or "")
            st.success("Prices refreshed successfully.")
            st.rerun()

    st.write("")

    # Filter evaluation
    filtered_items = tracked_with_verdict
    if verdict_filter != "All Statuses":
        filter_map = {
            "Genuine Low ✅": "genuine_low",
            "Inflated Discount 🚩": "inflated_discount",
            "Typical Price ➖": "no_change",
            "Insufficient Data ⏳": "insufficient_data",
        }
        target_v = filter_map.get(verdict_filter)
        filtered_items = [item for item in filtered_items if item[4].verdict == target_v]

    if search_filter:
        sf = search_filter.lower()
        filtered_items = [item for item in filtered_items if sf in item[0]["title"].lower() or sf in item[0]["source"].lower()]

    # Render Product Cards
    for t, history, current, past_history, verdict in filtered_items:
        label, kind = VERDICT_STYLE[verdict.verdict]
        stats = get_product_stats(t["id"])

        with st.container(border=True):
            head_col1, head_col2 = st.columns([3.5, 1])
            with head_col1:
                st.markdown(f"### {t['title']}")
                created_str = t['created_at'][:10] if t.get('created_at') else "Recently"
                link_md = f" · [🔗 Open Listing]({t['product_link']})" if t.get("product_link") else ""
                st.caption(f"**Seller:** {t['source']} | **Tracked since:** {created_str}{link_md}")
            with head_col2:
                untrack_btn = st.button("🗑️ Untrack", key=f"untrack_{t['id']}", use_container_width=True)
                if untrack_btn:
                    delete_tracked_product(t["id"])
                    st.toast(f"Removed {t['title']} from watchlist!")
                    st.rerun()

            # Metric columns
            mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
            mcol1.metric("Current Price", f"₹{current['price']:,.0f}")
            mcol2.metric("Historical Low", f"₹{stats['min_price']:,.0f}" if stats['min_price'] else "N/A")
            mcol3.metric("Historical Avg", f"₹{stats['avg_price']:,.0f}" if stats['avg_price'] else "N/A")
            mcol4.metric("Historical High", f"₹{stats['max_price']:,.0f}" if stats['max_price'] else "N/A")
            mcol5.metric("Total Checks", f"{stats['snapshot_count']}")

            # Verdict Alert Box
            getattr(st, kind)(f"**{label}** — {verdict.explanation}")

            # History Chart & Seller Breakdown Tabs
            tab1, tab2 = st.tabs(["📈 Price Trend Chart", "🏪 Live Seller Comparison"])
            with tab1:
                df = price_history_df(t["id"])
                if len(df) >= 2:
                    st.line_chart(df.set_index("checked_at")["price"], use_container_width=True)
                else:
                    st.caption("Track for a few more days or run scheduler.py to view historical price trend charts.")

            with tab2:
                if client and t.get("product_id"):
                    with st.spinner("Fetching live seller breakdown..."):
                        sellers = client.get_product_sellers(t["product_id"])
                        if sellers:
                            seller_df = pd.DataFrame(sellers)[["name", "price", "link"]]
                            seller_df.columns = ["Seller", "Price", "Link"]
                            st.dataframe(seller_df, hide_index=True, use_container_width=True)
                        else:
                            st.info("No multi-seller comparison offers available for this specific product ID.")
                else:
                    st.caption("Multi-seller comparison requires a valid SerpApi key and product_id.")

st.divider()
st.caption(
    "PriceDeal uses SerpApi's Google Shopping engine for real-time search & seller price snapshots. "
    "Price history accumulates with every refresh cycle."
)
