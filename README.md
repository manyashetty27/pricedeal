# 🏷️ PriceDeal — Festival Sale Price Watch

A price-tracking & price honesty dashboard built for the **SerpApi India Hackathon 2026**
(Track 04: Commerce & Market Intelligence) that answers one specific question during festival sale seasons:

> **Is this "sale" price actually a genuine low, or was the "original" price inflated right before the discount was applied?**

Instead of just comparing prices across sellers at a single point in time, PriceDeal records price snapshots over days/weeks and checks each new price against a product's own recent history. That's the difference between a price *comparison* tool and a price *honesty* tool.

---

## 🌟 Key Features

1. **Live Google Shopping Search** — Search products across Indian sellers (Amazon, Flipkart, Croma, Reliance Digital, etc.) using SerpApi's `google_shopping` engine.
2. **Multi-Seller Breakdown** — Compare live seller offers for any product using SerpApi's `google_product` engine.
3. **Price Watch & Automated Snapshots** — Save listings to local SQLite database and update price history manually or via `scheduler.py` cron jobs.
4. **Price Anomaly Detection Engine** — Evaluates each price snapshot and flags 4 distinct verdicts:
   - ✅ **Genuine Low** — At or near the lowest price ever recorded in recent history.
   - 🚩 **Possibly Inflated Discount** — Price raised prior to discount to inflate percentage drop.
   - ➖ **Typical Price** — Price within standard range.
   - ⏳ **Not Enough History Yet** — Less than 3 snapshots accumulated.
5. **Analytics & CSV Data Export** — View metric cards (Min, Max, Avg, Current), price trend line charts, and export complete tracking history as CSV.
6. **🌱 Hackathon Demo Data Seeder** — One-click demo data generation (`seed_demo.py`) that inserts 14–30 days of realistic price history for instant video recording and testing.

---

## 🛠️ Project Structure

```
pricedeal/
├── app.py              # Streamlit dashboard UI (Main Entry Point)
├── serpapi_client.py   # SerpApi wrapper (google_shopping, google_product)
├── database.py         # Lightweight SQLite storage layer
├── anomaly.py          # Price anomaly & fake discount verdict engine
├── seed_demo.py        # Demo script for seeding realistic 14-30 day price history
├── scheduler.py        # Automated cron script for daily price updates
├── test_anomaly.py     # Unit tests for anomaly engine
├── test_database.py    # Unit tests for database CRUD layer
├── requirements.txt    # Project dependencies
├── .env.example        # Environment variable template
└── data/               # SQLite database directory (data/pricedeal.db)
```

---

## 🚀 Quick Setup & Usage

### 1. Install Dependencies

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure SerpApi Key (Optional for Demo Mode)

Copy `.env.example` to `.env` and set your key:
```bash
cp .env.example .env
```
*(Or paste your SerpApi key directly into the Streamlit sidebar at runtime).*

### 3. Quick Demo Mode (Instant Historical Data)

To test the dashboard immediately without waiting days for real price accumulation:
```bash
python seed_demo.py
streamlit run app.py
```
*(Or click **'🌱 Seed Demo Price History'** directly in the Streamlit app sidebar).*

### 4. Live Search & Real Tracking

```bash
streamlit run app.py
```
- Open http://localhost:8501
- Search any product (e.g. `iPhone 15 128GB` or `Sony WH-1000XM5`).
- Click **Track Price** to begin recording snapshots.
- Click **Compare Sellers** to view live offers from multiple stores.

### 5. Automated Daily Price Refreshes

Run `scheduler.py` via Cron or Task Scheduler:
```bash
python scheduler.py
```
Example cron job (every day at 9 AM):
```cron
0 9 * * * cd /path/to/pricedeal && /path/to/venv/bin/python scheduler.py >> log.txt 2>&1
```

---

## 🧪 Running Unit Tests

Run automated unit tests for `anomaly.py` and `database.py`:
```bash
python -m unittest test_anomaly.py test_database.py
# or with pytest:
pytest
```

---

## 🎥 Hackathon Demo Video Script (< 3 min)

1. **Launch App**: `streamlit run app.py`
2. **Seed Demo History**: Click **"🌱 Seed Demo Price History"** in sidebar.
3. **Show Dashboard**:
   - Highlight **iPhone 15 (✅ Genuine Low)** showing price drop to ₹64,900.
   - Highlight **Samsung 55" QLED TV (🚩 Inflated Discount)** showing price spike right before claimed discount.
   - Demonstrate **Live Seller Comparison** and **Price Trend Chart**.
4. **Live Search**: Search a product live with SerpApi key and click **Track Price**.
5. **Code Overview**: Briefly highlight `anomaly.py` logic and `serpapi_client.py`.

---

## 📜 License & AI Tool Usage

- **License**: MIT
- **AI Tool Usage Disclosure**: Built with assistance from **Google Antigravity / Gemini** for code organization, Streamlit UI components, unit testing, and documentation.
