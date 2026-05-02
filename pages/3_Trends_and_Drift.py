"""Trends & Drift page — multi-year context."""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from shared import (
    page_setup, load_data, render_sidebar_summary,
    PALETTE,
)

page_setup("Trends & Drift", icon="📈")

data = load_data()
render_sidebar_summary(data)

cur = data["current_year"]
prv = data["prior_year"]
by_yr = data["by_year_domain"]
drift = data["drift"]

st.title("Trends & Drift")
st.caption("Where the multi-year story lives. Use the toggles to focus on what matters.")

st.subheader(f"{prv} vs {cur}")
if prv in by_yr.columns and cur in by_yr.columns:
    compare = by_yr[[prv, cur]].copy()
    compare = compare[(compare[prv].abs() >= 50) | (compare[cur].abs() >= 50)]
    compare = compare.sort_values(cur, ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=compare.index, x=compare[prv],
        orientation="h", name=str(prv),
        marker_color=PALETTE["neutral"],
    ))
    fig.add_trace(go.Bar(
        y=compare.index, x=compare[cur],
        orientation="h", name=str(cur),
        marker_color=PALETTE["navy"],
    ))
    fig.update_layout(
        barmode="group",
        height=max(500, 30 * len(compare)),
        plot_bgcolor="white",
        margin=dict(t=40, l=200, r=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="$",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Not enough data to compare {prv} vs {cur}.")

st.markdown("---")

st.subheader("5-year history — multi-line")
all_domains = by_yr.index.tolist()
default_top = (by_yr.max(axis=1).sort_values(ascending=False).head(8).index.tolist())
selected = st.multiselect(
    "Show categories (top 8 selected by default):",
    options=all_domains,
    default=default_top,
)
years = sorted(by_yr.columns)
fig2 = go.Figure()
for d in selected:
    fig2.add_trace(go.Scatter(
        x=years, y=[by_yr.loc[d, y] for y in years],
        mode="lines+markers", name=d,
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
fig2.update_layout(
    height=500,
    plot_bgcolor="white",
    xaxis=dict(tickmode="linear"),
    yaxis_title="Annual spend ($)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    margin=dict(t=20, l=60, r=20, b=120),
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

st.subheader(f"Drift — categories moving differently from total spend ({prv} → {cur})")
if drift.empty:
    st.info(f"Not enough data to compute drift between {prv} and {cur}.")
else:
    drift_view = drift.copy()
    drift_view = drift_view.rename(columns={
        "domain": "Category",
        f"spend_{prv}": str(prv),
        f"spend_{cur}": str(cur),
        "yoy_growth": "YoY growth",
        "vs_total_growth": "vs Total growth",
    })

    def _color_drift(val):
        if pd.isna(val):
            return ""
        if val > 0.2:
            return f"background-color: {PALETTE['bad']}; color: white"
        if val < -0.2:
            return f"background-color: {PALETTE['good']}; color: white"
        return ""

    styled = (drift_view.style
              .format({str(prv): "${:,.0f}", str(cur): "${:,.0f}",
                       "YoY growth": "{:+.0%}", "vs Total growth": "{:+.0%}"})
              .map(_color_drift, subset=["vs Total growth"]))
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown(
        f'<div style="background:{PALETTE["narrative"]}; padding:12px; '
        f'border-radius:4px; font-size:0.9rem; line-height:1.4;">'
        f'<b>How to read this:</b> "vs Total growth" shows whether a category grew '
        f'faster (red) or slower (green) than your overall spend YoY. '
        f'Drift isn\'t necessarily a problem - it can reflect a deliberate change. '
        f'Use it to spot conversation starters, not problems.'
        f'</div>', unsafe_allow_html=True)

st.markdown("---")

st.subheader("Annual cashflow — income, spend, savings rate")
cf = data["cashflow"]
display = cf.copy()
display.columns = [c.replace("_", " ").title() for c in display.columns]
fmt = {c: "${:,.0f}" for c in display.columns
       if c not in ("Year", "Savings Rate")}
fmt["Savings Rate"] = "{:.1%}"
st.dataframe(display.style.format(fmt), use_container_width=True, hide_index=True)
