"""
clean_data.py
-------------
Step 1 of the pipeline: load the raw export, fix data types, and strip/hash
every personally identifiable field so nothing sensitive ever leaves this
folder. Run this once to produce data/processed/clean_orders.csv, which is
the only file the rest of the project (and the dashboard) touches.

Usage:
    python scripts/clean_data.py
"""

import hashlib
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_PATH = Path("data/processed/clean_orders.csv")

# Columns that are money-formatted strings like "$49.95 " and need to become floats
MONEY_COLS = [
    "offer_price", "offer_revenue", "offer_sales_tax", "shipping_fee",
    "shipping_sales_tax", "coupon_amount", "offer_total", "offer_cogs",
    "pick_fee", "freight",
]

# Columns with real PII that must never be committed to git or shown in the dashboard
PII_COLS = [
    "customer_email", "customer_phone", "first_name", "last_name",
    "address_1", "address_2", "zip_code",
]


def money_to_float(series: pd.Series) -> pd.Series:
    """Turn '$49.95 ' into 49.95 (and blank/NaN into 0.0)."""
    return (
        series.astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
        .replace({"": "0", "nan": "0"})
        .astype(float)
    )


def hash_id(series: pd.Series) -> pd.Series:
    """Turn a real customer_id into a short, non-reversible anonymous ID."""
    return series.astype(str).apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:12]
    )


def main() -> None:
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    print(f"Loading raw data from {len(raw_files)} file(s) in {RAW_DIR} ...")
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in raw_files], ignore_index=True)
    print(f"  {len(df):,} rows loaded (before de-dup)")

    # The exports overlap in date range, so drop duplicate line-items
    df = df.drop_duplicates(subset=["order_id", "offer_id", "created_at"])
    print(f"  {len(df):,} rows after de-dup")

    # --- Parse dates ---
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["finalized_at"] = pd.to_datetime(df["finalized_at"], errors="coerce")
    df["contact_creation_date"] = pd.to_datetime(
        df["contact_creation_date"], errors="coerce"
    )

    # --- Fix money columns ---
    for col in MONEY_COLS:
        df[col] = money_to_float(df[col])

    # --- Anonymize customer identity ---
    df["customer_hash"] = hash_id(df["customer_id"])
    df = df.drop(columns=PII_COLS + ["customer_id"])

    # --- Light cleanup on categorical text ---
    for col in ["utm_source", "leadsource", "device_type", "offer_type", "revenue_type"]:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    # --- Convenience columns used by every later step ---
    df["order_date"] = df["created_at"].dt.date
    df["order_month"] = df["created_at"].dt.to_period("M").astype(str)
    df["net_revenue"] = df["offer_total"] - df["offer_cogs"] - df["shipping_fee"] - df["freight"]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved cleaned, anonymized data to {OUT_PATH} ({len(df):,} rows, {df.shape[1]} cols)")


if __name__ == "__main__":
    main()