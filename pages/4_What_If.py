"""What-If page - hypothetical category cuts and their effect on savings rate.

A slider per discretionary category. Move sliders to model 0%-50% cuts; the
total annual saving and projected new savings rate update in real time.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import analytics
from shared import (
    page_setup, load_data, render_sidebar_summary,
    fmt_money, PALETTE,
)

page_setup("What-If", icon="🎯")

data = load_data()
render_sidebar_summary(data)

cur = data["current_year"]
prv = data["prior_year"]
df = data["df"]

st.title("What-If — explore cuts")
st.caption("Slide a category down to see how much you'd save annually and what it does to your savings rate.")

baseline_year = prv

disc_spend = df[(df["year"] == baseline_year) &
                (df["domain"].isin(analytics.DISCRETIONARY))].groupby("domain")["amount_signed"].sum()
disc_spend = disc_spend[disc_spend > 100].sort_values(ascending=False)

if disc_spend.empty:
    st.warning(f"No discretionary spending data for {baseline_year}.")
    st.stop()

cf = data["cashflow"]
prv_cf = cf[cf["year"] == baseline_year]
if prv_cf.empty:
    st.warning(f"No cashflow data for {baseline_year}.")
    st.stop()

baseline = prv_cf.iloc[0]
income = baseline["total_income"]
spend = baseline["total_spend"]
saved = baseline["net"]
savings_rate = baseline["savings_rate"]

st.markdown(f"**Baseline year: {baseline_year}** — earned ${income:,.0f}, "
            f"spent ${spend:,.0f}, saved ${saved:,.0f} ({savings_rate*100:.1f}%)")

st.markdown("---")

st.subheader("Adjust cuts (per category)")
st.caption("Drag right to model spending less. The annual saving accumulates.")

cut_pcts = {}
cols_per_row = 2
domains_list = disc_spend.index.tolist()
for i in range(0, len(domains_list), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, domain in enumerate(domains_list[i:i+cols_per_row]):
        with cols[j]:
            current_spend = disc_spend[domain]
            cut_pcts[domain] = st.slider(
                f"{domain} (currently ${current_spend:,.0f}/yr)",
                min_value=0, max_value=50, value=0, step=5,
                format="%d%%",
                key=f"cut_{domain}",
            )

total_saved = sum(disc_spend[d] * (cut_pcts[d] / 100.0) for d in domains_list)
new_spend = spend - total_saved
new_saved = income - new_spend
new_savings_rate = new_saved / income if income else 0

st.markdown("---")
st.subheader("Projected impact")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Annual saving from cuts", fmt_money(total_saved))
col2.metric("New annual spend", fmt_money(new_spend),
            fmt_money(-total_saved, signed=True), delta_color="inverse")
col3.metric("New annual savings", fmt_money(new_saved),
            fmt_money(total_saved, signed=True), delta_color="normal")
col4.metric("New savings rate", f"{new_savings_rate*100:.1f}%",
            f"{(new_savings_rate - savings_rate)*100:+.1f} pp",
            delta_color="normal")

fig = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=new_savings_rate * 100,
    number={"suffix": "%", "valueformat": ".1f"},
    delta={"reference": savings_rate * 100, "valueformat": "+.1f",
           "suffix": " pp", "increasing": {"color": PALETTE["good_dark"]}},
    title={"text": f"Projected savings rate (baseline {savings_rate*100:.1f}%)"},
    gauge={
        "axis": {"range": [0, 60]},
        "bar": {"color": PALETTE["navy"]},
        "steps": [
            {"range": [0, 15], "color": "#FADADA"},
            {"range": [15, 30], "color": "#FFF2CC"},
            {"range": [30, 60], "color": "#E2F0E2"},
        ],
        "threshold": {
            "line": {"color": PALETTE["bad_dark"], "width": 4},
            "thickness": 0.75,
            "value": savings_rate * 100,
        },
    },
))
fig.update_layout(height=320, margin=dict(t=60, b=20, l=40, r=40))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Where the savings come from")
breakdown = pd.DataFrame([
    {"Category": d, "Annual saving": disc_spend[d] * (cut_pcts[d] / 100.0)}
    for d in domains_list if cut_pcts[d] > 0
])
if not breakdown.empty:
    breakdown = breakdown.sort_values("Annual saving", ascending=True)
    fig2 = go.Figure(go.Bar(
        y=breakdown["Category"], x=breakdown["Annual saving"],
        orientation="h",
        marker_color=PALETTE["good"],
        text=[f"${v:,.0f}" for v in breakdown["Annual saving"]],
        textposition="auto",
    ))
    fig2.update_layout(
        height=max(300, 30 * len(breakdown)),
        plot_bgcolor="white",
        margin=dict(t=20, l=200, r=40, b=40),
        xaxis_title="Annual saving ($)",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Slide some categories to see where the savings would come from.")

st.markdown("---")
st.markdown(
    f'<div style="background:{PALETTE["narrative"]}; padding:14px; border-radius:4px;">'
    f'<b>How this works:</b> Cuts are applied as straight percentage reductions to '
    f'last year\'s spend in each discretionary category. Real life is messier - some '
    f'categories you can cut sharply (an unused subscription), others you can\'t '
    f'(a gym you genuinely use). Use this as a thought experiment for the conversation, '
    f'not a budget commitment.'
    f'</div>',
    unsafe_allow_html=True,
)
