"""Pacing & Forecast page.

The inflation slider drives a live forecast and variance recompute across the page.
"""
from __future__ import annotations
import streamlit as st

from shared import (
    page_setup, load_data, recompute_for_inflation, render_sidebar_summary,
    pacing_chart, variance_chart, domain_monthly_chart,
    fmt_money,
)

page_setup("Pacing & Forecast", icon="📊")

base = load_data()
render_sidebar_summary(base)

st.title("Pacing & Forecast")
st.caption("Drag the inflation slider to see how the forecast and variance shift.")

inflation_pct = st.slider(
    "Inflation factor (applied to 2-year prior average)",
    min_value=0.0, max_value=10.0, value=4.0, step=0.5, format="%.1f%%",
    help="Default 4%. Slide right for a more conservative forecast (higher), left for a leaner one.",
)
inflation = inflation_pct / 100.0

data = recompute_for_inflation(inflation)
cur = data["current_year"]
prv = data["prior_year"]
forecast = data["forecast"]
variance = data["variance"]
pacing = data["pacing"]
latest_m = data["latest_month"]

total_forecast = forecast["forecast_total"].sum() if not forecast.empty else 0
ytd_actual = variance["ytd_actual"].sum() if not variance.empty else 0
ytd_forecast = variance["ytd_forecast"].sum() if not variance.empty else 0
ytd_variance = ytd_actual - ytd_forecast

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Annual forecast {cur}", fmt_money(total_forecast))
c2.metric(f"Forecast YTD (M{latest_m})", fmt_money(ytd_forecast))
c3.metric(f"Actual YTD", fmt_money(ytd_actual),
          fmt_money(ytd_variance, signed=True), delta_color="inverse")
c4.metric("Pacing % of forecast",
          f"{(ytd_actual/ytd_forecast*100):.0f}%" if ytd_forecast else "—")

st.markdown("---")

st.subheader("Cumulative pacing")
st.plotly_chart(pacing_chart(pacing, cur, prv), use_container_width=True)

st.markdown("---")

st.subheader("YTD variance vs forecast")
st.plotly_chart(variance_chart(variance), use_container_width=True)

st.markdown("---")

st.subheader(f"Annual forecast — {cur}")
if forecast.empty:
    st.warning("Not enough prior-year data to build a forecast.")
else:
    actual_cols = [c for c in forecast.columns if c.startswith("actual_")]
    display = forecast[["domain"] + actual_cols + ["prior_avg", "forecast_total", "forecast_monthly"]].copy()
    rename_map = {"domain": "Category", "prior_avg": "2-yr avg",
                  "forecast_total": f"{cur} forecast", "forecast_monthly": "monthly"}
    for ac in actual_cols:
        rename_map[ac] = ac.replace("actual_", "") + " actual"
    display = display.rename(columns=rename_map)
    money_cols = [c for c in display.columns if c != "Category"]
    fmt_dict = {c: "${:,.0f}" for c in money_cols}
    st.dataframe(
        display.style.format(fmt_dict).background_gradient(
            subset=[f"{cur} forecast"], cmap="Blues"),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.subheader("Drill into a category")
domains_with_data = sorted([d for d in forecast["domain"].tolist() if d])
selected = st.selectbox("Choose a category", options=["—"] + domains_with_data)
if selected and selected != "—":
    df = data["df"]
    sub = df[(df["domain"] == selected) & (df["year"] == cur)]
    fc_row = forecast[forecast["domain"] == selected]
    monthly_forecast = float(fc_row["forecast_monthly"].iloc[0]) if not fc_row.empty else None

    col_a, col_b = st.columns([1, 2])
    with col_a:
        ytd = sub["amount_signed"].sum()
        n = len(sub)
        st.metric(f"{selected} YTD", fmt_money(ytd), f"{n} transactions", delta_color="off")
        if monthly_forecast is not None:
            forecast_ytd = monthly_forecast * latest_m
            st.metric(f"Forecast YTD (M{latest_m})", fmt_money(forecast_ytd),
                      fmt_money(ytd - forecast_ytd, signed=True), delta_color="inverse")

    with col_b:
        st.plotly_chart(
            domain_monthly_chart(df, selected, cur, monthly_forecast),
            use_container_width=True,
        )

    st.markdown("**Top merchants this year:**")
    top = (sub.groupby("sub_source")["amount_signed"].sum()
           .sort_values(ascending=False).head(10).reset_index())
    top.columns = ["Merchant / sub-source", "$ YTD"]
    st.dataframe(top.style.format({"$ YTD": "${:,.2f}"}),
                 use_container_width=True, hide_index=True)

    st.markdown("**Latest 20 transactions:**")
    cols = ["date", "description", "debit", "credit", "account_suffix", "rule_used"]
    latest = sub[cols].sort_values("date", ascending=False).head(20)
    st.dataframe(latest, use_container_width=True, hide_index=True)
