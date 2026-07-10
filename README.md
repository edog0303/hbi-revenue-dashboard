# HBI Revenue Intelligence Dashboard

An interactive dashboard analyzing 180K+ direct-to-consumer orders across three
angles: **marketing channel ROI**, **subscription cohort retention**, and
**funnel/offer performance**. Built with Python, pandas, and Plotly Dash.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Dash](https://img.shields.io/badge/dash-plotly-informational)

## Why this project

Direct-to-consumer subscription businesses live and die by three questions:
*which channels are worth the ad spend, do subscribers stick around, and
which offers actually convert?* This project builds a repeatable pipeline
that answers all three from a raw order-export CSV.

## Live demo

This repo ships with a **synthetic sample dataset** (`data/sample/`) so it
runs immediately for anyone who clones it - no proprietary data required.
Real company data is processed locally and never committed (see
[Data privacy](#data-privacy) below).

## Screenshots

*(Add a screenshot of each tab here once you've run the app - drag the PNGs
into this section on GitHub, or use `![Overview](screenshots/overview.png)`.)*

## Project structure
hbi-dashboard/
├── data/
│   ├── raw/          # your real CSV exports go here (gitignored)
│   ├── processed/     # cleaned/anonymized + aggregated data (gitignored)
│   └── sample/        # synthetic demo data (committed to git)
├── scripts/
│   ├── clean_data.py          # Step 1: type-fix, anonymize
│   ├── build_features.py      # Step 2: build the 4 aggregate tables
│   └── generate_sample_data.py# builds the synthetic demo data
├── app.py              # the Dash application
├── requirements.txt
└── README.md

## Methodology

1. **Clean & anonymize** (`scripts/clean_data.py`): loads every CSV in
   `data/raw/`, combines them, de-duplicates overlapping line-items, parses
   dates and currency-formatted strings, and replaces every PII field (name,
   email, phone, address) with a one-way hash of the customer ID so
   downstream analysis can still group "the same customer" without ever
   exposing who they are.
2. **Feature engineering** (`scripts/build_features.py`): rolls the cleaned,
   order-level data up into four small tables so the dashboard never has to
   re-aggregate 100K+ rows on every click:
   - `channel_summary` - revenue, AOV, and % recurring by UTM source + device
   - `cohort_retention` - week-by-week retention % per acquisition cohort
   - `funnel_summary` - revenue by product, offer type, and revenue type
   - `daily_revenue` - a daily time series for the trend chart
3. **Dashboard** (`app.py`): a 4-tab Plotly Dash app reading those tables.

## Data privacy

The raw exports contain real customer names, emails, phone numbers, and
addresses. This repo is built so that data **never leaves your machine**:

- `data/raw/` and `data/processed/` are both in `.gitignore`.
- `clean_data.py` strips/hashes every PII column before anything downstream
  touches the data.
- Only the fully synthetic `data/sample/` folder is committed to git.

**Before publishing any real numbers from your own company's data** (even
aggregated), get sign-off from your employer - revenue and marketing
performance data is usually confidential even once anonymized.

## Setup

```bash
git clone <your-repo-url>
cd hbi-dashboard
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:8050 in your browser.

To run it on your own real data instead of the sample:
1. Drop your export(s) into `data/raw/`.
2. Run `python scripts/clean_data.py && python scripts/build_features.py`.
3. Run `python app.py` - it automatically prefers `data/processed/` over the
   sample data when both exist.

## Key findings *(fill in once you've explored your own data)*

- Which channel had the best AOV vs. worst recurring rate?
- How much retention drops off after week 4 vs. week 8?
- Which product/offer combo drives the most net revenue after COGS?

## Possible extensions

- Add a customer lifetime value (LTV) prediction model
- Swap the CSV pipeline for a proper database (Postgres/DuckDB)
- Deploy the dashboard (Render, Fly.io, or Heroku all support Dash apps)