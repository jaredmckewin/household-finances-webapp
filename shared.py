"""Shared data loaders, theme, and chart helpers for the Streamlit app."""
from __future__ import annotations
import os

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import analytics

HOUSEHOLD_NAME = os.environ.get("HOUSEHOLD_NAME", "Household")


PALETTE = {
    "navy": "#1F3864",
    "soft_blue": "#D9E1F2",
    "yellow": "#FFF2CC",
    "good": "#6BBF59",
    "good_dark": "#256029",
    "bad": "#E07A6E",
    "bad_dark": "#7A1F1F",
    "neutral": "#9AA0A6",
    "warm": "#FFF6E5",
    "narrative": "#EAF1F8",
}
DOMAIN_COLORS_BASE = (
    px.colors.qualitative.Bold + px.colors.qualitative.Pastel +
    px.colors.qualitative.Safe + px.colors.qualitative.Vivid
)


def page_setup(title: str, icon: str = "💸"):
    st.set_page_config(
        page_title=f"{HOUSEHOLD_NAME} Finances — {title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        f"""
        <style>
        .block-container {{padding-top: 2rem; padding-bottom: 2rem;}}
        .stMetric label {{ font-size: 0.85rem !important; color: #555; }}
        .stMetric [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; }}
        .narrative-card {{
            background: {PALETTE['narrative']};
            border-left: 4px solid {PALETTE['navy']};
            padding: 12px 16px; margin: 8px 0;
            border-radius: 4px;
            font-size: 0.95rem; line-height: 1.4;
        }}
        .decision-card {{
            background: {PALETTE['warm']};
            border-left: 4px solid #C68A00;
            padding: 12px 16px; margin: 8px 0;
            border-radius: 4px;
            font-size: 0.95rem; line-height: 1.4;
        }}
        .kpi-banner {{
            background: {PALETTE['navy']};
            color: white;
            padding: 16px 20px; border-radius: 6px;
            font-weight: 600; font-size: 1.1rem;
            margin: 8px 0 16px 0;
        }}
        h1, h2, h3 {{ color: {PALETTE['navy']}; }}
        section[data-testid="stSidebar"] h1 {{ font-size: 1.2rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_data() -> dict:
    base = analytics.compute_all()
    cur = base["current_year"]
    df = base["df"]
    base["forecast"] = analytics.forecast_annual(df, cur, inflation=0.04, prior_years=2)
    base["pacing"] = analytics.pacing_data(df, cur, compare_years=2)
    base["variance"] = analytics.variance_to_forecast(df, cur, inflation=0.04)
    base["latest_month"] = analytics.latest_month_with_data(df, cur)
    return base


def recompute_for_inflation(inflation: float) -> dict:
    df = analytics.load_transactions()
    cur, prv = analytics.detect_current_year(df)
    return {
        "df": df,
        "current_year": cur,
        "prior_year": prv,
        "forecast": analytics.forecast_annual(df, cur, inflation=inflation, prior_years=2),
        "pacing": analytics.pacing_data(df, cur, compare_years=2),
        "variance": analytics.variance_to_forecast(df, cur, inflation=inflation),
        "latest_month": analytics.latest_month_with_data(df, cur),
    }


def render_sidebar_summary(data: dict):
    cur = data["current_year"]
    prv = data["prior_year"]
    latest_m = data["latest_month"]
    pacing = data.get("pacing", pd.DataFrame())
    st.sidebar.markdown(f"### Current year: **{cur}**")
    st.sidebar.markdown(f"_{latest_m} of 12 months populated_")
    if not pacing.empty and latest_m > 0:
        row = pacing[pacing["month_num"] == latest_m].iloc[0]
        actual = row["actual_cum"]
        forecast = row["forecast_cum"]
        if actual is not None and forecast:
            pct = (actual / forecast) * 100
            st.sidebar.metric(
                f"Through Mo. {latest_m} pace",
                f"{pct:.0f}% of forecast",
                f"${actual - forecast:+,.0f} vs forecast",
                delta_color="inverse",
            )
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"vs prior year **{prv}** & **{prv-1}**")


def fmt_money(v: float, signed: bool = False) -> str:
    if v is None or pd.isna(v):
        return "—"
    if signed and v != 0:
        return f"${v:+,.0f}"
    return f"${v:,.0f}"


def fmt_pct(v: float) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v*100:.1f}%"


def pacing_chart(pacing: pd.DataFrame, current_year: int, prior_year: int) -> go.Figure:
    fig = go.Figure()
    if pacing.empty:
        return fig

    months = pacing["month"].tolist()
    fig.add_trace(go.Scatter(
        x=months, y=pacing["forecast_cum"], mode="lines",
        name=f"{current_year} forecast",
        line=dict(color=PALETTE["navy"], width=3, dash="dash"),
        hovertemplate="<b>%{x}</b><br>Forecast: $%{y:,.0f}<extra></extra>",
    ))
    actuals = pacing["actual_cum"].tolist()
    fig.add_trace(go.Scatter(
        x=months, y=actuals, mode="lines+markers",
        name=f"{current_year} actual",
        line=dict(color=PALETTE["good_dark"], width=4),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Actual: $%{y:,.0f}<extra></extra>",
        connectgaps=False,
    ))
    py_col = f"py_{prior_year}_cum"
    if py_col in pacing.columns:
        fig.add_trace(go.Scatter(
            x=months, y=pacing[py_col], mode="lines",
            name=f"{prior_year}",
            line=dict(color=PALETTE["neutral"], width=2),
            hovertemplate="<b>%{x}</b><br>" + str(prior_year) + ": $%{y:,.0f}<extra></extra>",
        ))
    py2_col = f"py_{prior_year-1}_cum"
    if py2_col in pacing.columns:
        fig.add_trace(go.Scatter(
            x=months, y=pacing[py2_col], mode="lines",
            name=f"{prior_year-1}",
            line=dict(color=PALETTE["neutral"], width=1, dash="dot"),
            hovertemplate="<b>%{x}</b><br>" + str(prior_year-1) + ": $%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title=f"Cumulative spend pacing — {current_year}",
        xaxis_title="Month",
        yaxis_title="Cumulative spend ($)",
        height=460,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    fig.update_yaxes(gridcolor="#EAEAEA")
    fig.update_xaxes(gridcolor="#EAEAEA")
    return fig


def variance_chart(variance: pd.DataFrame) -> go.Figure:
    if variance.empty:
        return go.Figure()
    df = variance.copy()
    df = df[(df["ytd_actual"].abs() >= 50) | (df["ytd_forecast"].abs() >= 50)]
    df = df.sort_values("variance")
    colors = [PALETTE["bad"] if v > 0 else PALETTE["good"] for v in df["variance"]]
    fig = go.Figure(go.Bar(
        x=df["variance"], y=df["domain"],
        orientation="h",
        marker_color=colors,
        text=[f"${v:+,.0f}" for v in df["variance"]],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Variance: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="YTD variance vs forecast — red = over, green = under",
        xaxis_title="Variance ($)",
        yaxis_title=None,
        height=max(400, 22 * len(df)),
        plot_bgcolor="white",
        margin=dict(t=60, l=200, r=20, b=60),
    )
    fig.update_xaxes(gridcolor="#EAEAEA", zerolinecolor=PALETTE["navy"], zerolinewidth=2)
    return fig


def domain_monthly_chart(df: pd.DataFrame, domain: str, current_year: int,
                          forecast_monthly: float | None = None) -> go.Figure:
    sub = df[(df["domain"] == domain) & (df["year"] == current_year)].copy()
    sub["m"] = sub["date_dt"].dt.month
    monthly = sub.groupby("m")["amount_signed"].sum().reindex(range(1, 13), fill_value=0.0)
    months = [pd.Timestamp(year=current_year, month=m, day=1).strftime("%b") for m in monthly.index]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=monthly.values,
        marker_color=PALETTE["navy"],
        name="Actual",
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    if forecast_monthly is not None:
        fig.add_trace(go.Scatter(
            x=months, y=[forecast_monthly] * 12,
            mode="lines",
            name="Forecast monthly",
            line=dict(color=PALETTE["bad_dark"], dash="dash", width=2),
        ))
    fig.update_layout(
        title=f"{domain} - monthly {current_year}",
        height=320,
        plot_bgcolor="white",
        margin=dict(t=50, l=50, r=20, b=40),
        showlegend=True,
    )
    return fig


def render_kpi_banner(text: str):
    st.markdown(f'<div class="kpi-banner">{text}</div>', unsafe_allow_html=True)


def render_narrative_card(text: str, idx: int | None = None):
    prefix = f"<b>{idx}.</b> " if idx is not None else ""
    st.markdown(
        f'<div class="narrative-card">{prefix}{text}</div>',
        unsafe_allow_html=True,
    )


def render_decision_card(text: str):
    st.markdown(
        f'<div class="decision-card">→ {text}</div>',
        unsafe_allow_html=True,
    )
