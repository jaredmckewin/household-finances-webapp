"""Conversation page (home).

Run with: streamlit run app.py
"""
from __future__ import annotations
import os
from datetime import date
import streamlit as st

from shared import (
    page_setup, load_data, render_sidebar_summary,
    render_narrative_card, render_decision_card,
    pacing_chart, fmt_money,
)

HOUSEHOLD_NAME = os.environ.get("HOUSEHOLD_NAME", "Household")

page_setup("Conversation", icon="💬")

data = load_data()
render_sidebar_summary(data)

cur = data["current_year"]
prv = data["prior_year"]
latest_m = data["latest_month"]
month_name = date(cur, max(latest_m, 1), 1).strftime("%B")

st.title(f"{HOUSEHOLD_NAME} Finances")
st.caption(
    f"Current year: **{cur}** ({latest_m} of 12 months populated) · "
    f"vs prior years **{prv}** & **{prv-1}** · "
    f"Generated {date.today().isoformat()}"
)

pacing = data["pacing"]
if not pacing.empty and latest_m > 0:
    row = pacing[pacing["month_num"] == latest_m].iloc[0]
    actual_cum = row.get("actual_cum")
    forecast_cum = row.get("forecast_cum")
    py_cum = row.get(f"py_{prv}_cum")

    col1, col2, col3, col4 = st.columns(4)
    if actual_cum is not None and forecast_cum:
        pct = (actual_cum / forecast_cum) * 100
        col1.metric(
            "Spent YTD",
            fmt_money(actual_cum),
            f"{pct:.0f}% of forecast pace",
            delta_color="off",
        )
        col2.metric(
            "Forecast pace YTD",
            fmt_money(forecast_cum),
            f"Through {month_name}",
            delta_color="off",
        )
    if py_cum:
        delta = (actual_cum or 0) - py_cum
        col3.metric(
            f"vs {prv} same period",
            fmt_money(py_cum),
            f"{fmt_money(delta, signed=True)}",
            delta_color="inverse",
        )
    cf = data["cashflow"]
    cur_cf = cf[cf["year"] == cur]
    if not cur_cf.empty and latest_m > 0:
        annualised = (cur_cf.iloc[0]["total_income"] / latest_m) * 12
        prv_cf = cf[cf["year"] == prv]
        if not prv_cf.empty:
            delta = annualised - prv_cf.iloc[0]["total_income"]
            col4.metric(
                "Income (annualised)",
                fmt_money(annualised),
                f"{fmt_money(delta, signed=True)} vs {prv}",
                delta_color="normal",
            )

st.subheader(f"Pacing — {cur} vs forecast vs prior years")
st.plotly_chart(pacing_chart(pacing, cur, prv), use_container_width=True)

st.subheader("Headlines")
headlines = data["headlines"]
if headlines:
    for i, h in enumerate(headlines, 1):
        render_narrative_card(h, idx=i)
else:
    st.info("No notable signals yet — data needs more months to settle.")

st.subheader("What to talk about")
talk = data["talk_about"]
if talk:
    for prompt in talk:
        render_decision_card(prompt)
else:
    st.info("No decisions surface this period — things look stable.")

st.markdown("---")
with st.expander("How is this calculated?"):
    st.markdown("""
    **Forecast** = average of the last 2 complete prior years per category × (1 + inflation factor, default 4%),
    split equally across 12 months.

    **Pacing** = cumulative actual spend YTD vs cumulative forecast YTD vs prior years' same-period totals.

    **Excluded from spend totals**: internal transfers between household accounts, wages and other income,
    opening/closing balance markers, Unknown rows.
    """)
