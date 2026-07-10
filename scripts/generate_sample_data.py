"""
generate_sample_data.py
------------------------
Creates small, fully synthetic versions of the four processed tables so this
repo runs out-of-the-box for anyone who clones it - no real company data
required. This is what gets committed to git; the real, employer-owned data
stays local in data/processed/ (which is gitignored).

Usage:
    python scripts/generate_sample_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT_DIR = Path("data/sample")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = ["Google", "Youtube", "Facebook", "Phone", "attentive", "PMAX", "Email"]
DEVICES = ["Desktop", "Phone", "Tablet", "Unknown"]
PRODUCTS = ["Product A", "Product B", "Product C", "Product D"]
OFFER_TYPES = ["Subscription", "One Time Purchase"]
REVENUE_TYPES = ["Initial", "Recurring"]

# --- channel_summary.csv ---
rows = []
for src in SOURCES:
    for dev in DEVICES:
        orders = int(rng.integers(200, 4000))
        line_items = orders + int(rng.integers(0, orders * 0.4))
        revenue = round(orders * rng.uniform(35, 90), 2)
        customers = int(orders * rng.uniform(0.85, 1.0))
        recurring_line_items = int(line_items * rng.uniform(0.3, 0.7))
        rows.append(dict(
            utm_source=src, device_type=dev, orders=orders, line_items=line_items,
            revenue=revenue, customers=customers,
            recurring_line_items=recurring_line_items,
            aov=round(revenue / orders, 2),
            pct_recurring=round(recurring_line_items / line_items * 100, 1),
        ))
pd.DataFrame(rows).to_csv(OUT_DIR / "channel_summary.csv", index=False)

# --- cohort_retention.csv ---
rows = []
for month in ["2026-01", "2026-02", "2026-03"]:
    cohort_size = int(rng.integers(800, 2000))
    for week in range(0, 10):
        retention = max(2, 100 * (0.6 ** week) + rng.normal(0, 3))
        rows.append(dict(
            cohort_month=month, period_week=week,
            active_customers=int(cohort_size * retention / 100),
            cohort_size=cohort_size, retention_pct=round(retention, 1),
        ))
pd.DataFrame(rows).to_csv(OUT_DIR / "cohort_retention.csv", index=False)

# --- funnel_summary.csv ---
rows = []
for prod in PRODUCTS:
    for offer_type in OFFER_TYPES:
        for rev_type in REVENUE_TYPES:
            orders = int(rng.integers(100, 3000))
            revenue = round(orders * rng.uniform(20, 80), 2)
            rows.append(dict(
                product_family_name=prod, offer_type=offer_type, revenue_type=rev_type,
                orders=orders, revenue=revenue, avg_order_value=round(revenue / orders, 2),
            ))
pd.DataFrame(rows).to_csv(OUT_DIR / "funnel_summary.csv", index=False)

# --- daily_revenue.csv ---
dates = pd.date_range("2026-01-01", "2026-03-31", freq="D")
revenue = 12000 + rng.normal(0, 1500, size=len(dates)).cumsum() * 0.05 + rng.normal(0, 800, size=len(dates))
orders = (revenue / rng.uniform(45, 55)).astype(int)
pd.DataFrame({
    "order_date": dates, "revenue": revenue.round(2), "orders": orders,
}).to_csv(OUT_DIR / "daily_revenue.csv", index=False)

print(f"Synthetic sample data written to {OUT_DIR}/")