"""
app.py
------
Interactive Dash dashboard for the HBI order-revenue dataset.

Reads the pre-aggregated tables in data/processed/ (built by scripts/clean_data.py
and scripts/build_features.py) and serves four views:
    1. Overview            - headline KPIs + daily revenue trend
    2. Marketing Channel ROI- revenue/AOV/recurring-% by acquisition channel
    3. Cohort Retention     - weekly retention curve by acquisition cohort
    4. Funnel Analysis      - revenue by product, offer type, and stage

Run with:
    python app.py
Then open http://127.0.0.1:8050 in a browser.
"""

import pandas as pd
import plotly.express as px
from pathlib import Path

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

DATA_DIR = Path("data/processed")
SAMPLE_DIR = Path("data/sample")

if not (DATA_DIR / "daily_revenue.csv").exists():
    print("No local processed data found - running on the synthetic sample dataset "
          "in data/sample/. See README.md to plug in real data.")
    DATA_DIR = SAMPLE_DIR

# ---------------------------------------------------------------------------
# Load pre-aggregated data once, at startup
# ---------------------------------------------------------------------------
channel_df = pd.read_csv(DATA_DIR / "channel_summary.csv")
cohort_df = pd.read_csv(DATA_DIR / "cohort_retention.csv")
funnel_df = pd.read_csv(DATA_DIR / "funnel_summary.csv")
daily_df = pd.read_csv(DATA_DIR / "daily_revenue.csv", parse_dates=["order_date"])

PRODUCT_OPTIONS = [{"label": p, "value": p} for p in sorted(funnel_df["product_family_name"].unique())]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "HBI Revenue Intelligence Dashboard"
server = app.server  # exposed for gunicorn/deployment

# ---------------------------------------------------------------------------
# Reusable KPI card component
# ---------------------------------------------------------------------------
def kpi_card(title, value, color="primary"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(title, className="text-muted"),
                html.H3(value, className=f"text-{color}"),
            ]
        ),
        className="shadow-sm mb-3",
    )

# ---------------------------------------------------------------------------
# Tab 1: Overview
# ---------------------------------------------------------------------------
def overview_tab():
    total_revenue = daily_df["revenue"].sum()
    total_orders = daily_df["orders"].sum()
    avg_daily_rev = daily_df["revenue"].mean()

    fig = px.line(
        daily_df, x="order_date", y="revenue",
        title="Daily Net Revenue", markers=True,
    )
    fig.update_layout(template="plotly_white")

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(kpi_card("Total Net Revenue", f"${total_revenue:,.0f}")),
                    dbc.Col(kpi_card("Total Orders", f"{total_orders:,.0f}")),
                    dbc.Col(kpi_card("Avg Daily Revenue", f"${avg_daily_rev:,.0f}")),
                ]
            ),
            dcc.Graph(figure=fig),
        ]
    )

# ---------------------------------------------------------------------------
# Tab 2: Marketing Channel ROI
# ---------------------------------------------------------------------------
def channel_tab():
    return html.Div(
        [
            html.P("Top acquisition channels by revenue. Bubble size = number of unique customers."),
            dcc.Graph(id="channel-scatter"),
            dcc.Graph(id="channel-bar"),
        ]
    )


@app.callback(Output("channel-scatter", "figure"), Input("tabs", "value"))
def update_channel_scatter(_):
    top = channel_df.sort_values("revenue", ascending=False).head(20)
    fig = px.scatter(
        top, x="aov", y="pct_recurring", size="customers", color="utm_source",
        hover_name="utm_source", hover_data=["device_type", "revenue", "orders"],
        title="Channel Performance: AOV vs % Recurring Revenue (top 20 by revenue)",
    )
    fig.update_layout(template="plotly_white")
    return fig


@app.callback(Output("channel-bar", "figure"), Input("tabs", "value"))
def update_channel_bar(_):
    top = (
        channel_df.groupby("utm_source")["revenue"].sum()
        .sort_values(ascending=False).head(12).reset_index()
    )
    fig = px.bar(top, x="utm_source", y="revenue", title="Revenue by Channel (top 12)")
    fig.update_layout(template="plotly_white", xaxis_title="", yaxis_title="Net Revenue ($)")
    return fig

# ---------------------------------------------------------------------------
# Tab 3: Cohort Retention
# ---------------------------------------------------------------------------
def cohort_tab():
    pivot = cohort_df.pivot(index="cohort_month", columns="period_week", values="retention_pct")
    fig = px.imshow(
        pivot, text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
        labels=dict(x="Weeks Since First Order", y="Acquisition Cohort", color="Retention %"),
        title="Weekly Retention by Acquisition Cohort",
    )
    fig.update_layout(template="plotly_white")
    return html.Div(
        [
            html.P(
                "Each row is a group of customers acquired in the same month. Each cell shows "
                "what percentage of that cohort placed another order N weeks later."
            ),
            dcc.Graph(figure=fig),
        ]
    )


# ---------------------------------------------------------------------------
# Tab 4: Funnel Analysis
# ---------------------------------------------------------------------------
def funnel_tab():
    return html.Div(
        [
            html.Label("Filter by product family:"),
            dcc.Dropdown(
                id="product-filter",
                options=PRODUCT_OPTIONS,
                value=None,
                placeholder="All products",
                clearable=True,
            ),
            dcc.Graph(id="funnel-bar"),
        ]
    )


@app.callback(Output("funnel-bar", "figure"), Input("product-filter", "value"))
def update_funnel_bar(product):
    data = funnel_df if not product else funnel_df[funnel_df["product_family_name"] == product]
    grp = data.groupby(["offer_type", "revenue_type"])["revenue"].sum().reset_index()
    fig = px.bar(
        grp, x="offer_type", y="revenue", color="revenue_type", barmode="group",
        title=f"Revenue by Offer Type{f' — {product}' if product else ''}",
    )
    fig.update_layout(template="plotly_white", yaxis_title="Net Revenue ($)")
    return fig

# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------
app.layout = dbc.Container(
    [
        html.H2("HBI Revenue Intelligence Dashboard", className="my-4"),
        dcc.Tabs(
            id="tabs",
            value="overview",
            children=[
                dcc.Tab(label="Overview", value="overview"),
                dcc.Tab(label="Marketing Channel ROI", value="channel"),
                dcc.Tab(label="Cohort Retention", value="cohort"),
                dcc.Tab(label="Funnel Analysis", value="funnel"),
            ],
        ),
        html.Div(id="tab-content", className="mt-4"),
    ],
    fluid=True,
)


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    return {
        "overview": overview_tab,
        "channel": channel_tab,
        "cohort": cohort_tab,
        "funnel": funnel_tab,
    }[tab]()


if __name__ == "__main__":
    app.run(debug=False)