"""
build_features.py
------------------
Step 2 of the pipeline: turn the cleaned order-level data into a handful of
small, pre-aggregated tables. The dashboard reads these directly instead of
recomputing aggregations on every click, which is what keeps a Dash app fast.

Produces (all in data/processed/):
    channel_summary.csv    revenue / orders / AOV by marketing channel & device
    cohort_retention.csv   week-by-week retention curve per acquisition cohort
    funnel_summary.csv     revenue by product, offer type, and funnel stage
    daily_revenue.csv      daily revenue time series for the trend chart

Usage:
    python scripts/build_features.py
"""

import pandas as pd
from pathlib import Path

IN_PATH = Path("data/processed/clean_orders.csv")
OUT_DIR = Path("data/processed")


def build_channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue, order volume, and AOV broken down by acquisition channel."""
    # Note: order_id repeats within a single checkout when a customer buys a main
    # offer plus an upsell/downsell, so we track "line_items" (rows) separately
    # from "orders" (distinct order_id) to keep AOV and recurring-% meaningful.
    grp = (
        df.groupby(["utm_source", "device_type"])
        .agg(
            orders=("order_id", "nunique"),
            line_items=("order_id", "size"),
            revenue=("net_revenue", "sum"),
            customers=("customer_hash", "nunique"),
            recurring_line_items=("revenue_type", lambda s: (s == "Recurring").sum()),
        )
        .reset_index()
    )
    grp["aov"] = (grp["revenue"] / grp["orders"]).round(2)
    grp["pct_recurring"] = (grp["recurring_line_items"] / grp["line_items"] * 100).round(1)
    return grp.sort_values("revenue", ascending=False)


def build_cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weekly retention curve: for customers acquired in a given cohort month,
    what share of them place another order N weeks later?
    """
    orders = df[["customer_hash", "created_at"]].dropna().copy()
    orders["created_at"] = pd.to_datetime(orders["created_at"])

    first_order = orders.groupby("customer_hash")["created_at"].min().rename("cohort_date")
    orders = orders.join(first_order, on="customer_hash")
    orders["cohort_month"] = orders["cohort_date"].dt.to_period("M").astype(str)
    orders["period_week"] = (
        (orders["created_at"] - orders["cohort_date"]).dt.days // 7
    )

    cohort_sizes = (
        orders.groupby("cohort_month")["customer_hash"].nunique().rename("cohort_size")
    )

    active = (
        orders.groupby(["cohort_month", "period_week"])["customer_hash"]
        .nunique()
        .reset_index(name="active_customers")
    )
    active = active.join(cohort_sizes, on="cohort_month")
    active["retention_pct"] = (
        active["active_customers"] / active["cohort_size"] * 100
    ).round(1)
    return active.sort_values(["cohort_month", "period_week"])


def build_funnel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and order counts by product family, offer type, and revenue type."""
    grp = (
        df.groupby(["product_family_name", "offer_type", "revenue_type"])
        .agg(
            orders=("order_id", "nunique"),
            revenue=("net_revenue", "sum"),
            avg_order_value=("net_revenue", "mean"),
        )
        .reset_index()
    )
    grp["avg_order_value"] = grp["avg_order_value"].round(2)
    return grp.sort_values("revenue", ascending=False)


def build_daily_revenue(df: pd.DataFrame) -> pd.DataFrame:
    daily = (
        df.groupby("order_date")
        .agg(revenue=("net_revenue", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    return daily.sort_values("order_date")


def main() -> None:
    df = pd.read_csv(IN_PATH, low_memory=False)
    print(f"Loaded {len(df):,} cleaned rows")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    channel = build_channel_summary(df)
    channel.to_csv(OUT_DIR / "channel_summary.csv", index=False)
    print(f"  channel_summary.csv       -> {len(channel):,} rows")

    cohort = build_cohort_retention(df)
    cohort.to_csv(OUT_DIR / "cohort_retention.csv", index=False)
    print(f"  cohort_retention.csv      -> {len(cohort):,} rows")

    funnel = build_funnel_summary(df)
    funnel.to_csv(OUT_DIR / "funnel_summary.csv", index=False)
    print(f"  funnel_summary.csv        -> {len(funnel):,} rows")

    daily = build_daily_revenue(df)
    daily.to_csv(OUT_DIR / "daily_revenue.csv", index=False)
    print(f"  daily_revenue.csv         -> {len(daily):,} rows")


if __name__ == "__main__":
    main()