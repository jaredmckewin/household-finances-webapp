"""Transactions page — full filterable master with search and quick categorise.

Quick categorise: pick an Unknown row, choose a domain, and the override is
saved to a JSON file (path from OVERRIDES_PATH env var, default
``manual_overrides.json`` next to the app).
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import streamlit as st
import pandas as pd

from shared import page_setup, load_data, render_sidebar_summary, fmt_money
from analytics import MORTGAGE_LABEL

page_setup("Transactions", icon="📋")

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES_FILE = Path(os.environ.get("OVERRIDES_PATH", str(ROOT / "manual_overrides.json")))

DOMAINS = sorted([
    "Accounting & Tax", "Administrative & Post", "Baby Expenses", "Bank Fees",
    "Communications & Internet", "Debt Repayment", "Groceries",
    MORTGAGE_LABEL, "Insurance", "Medical & Health",
    "Pet Expenses", "Transport & Parking", "Utilities & Rates", "Vehicle Expenses",
    "Rent (historical)", "Alcohol", "Clothing & Footwear", "Dining Out & Takeaway",
    "Donations & Charity", "Education & Training", "Gifts", "Holidays & Travel",
    "Home & Garden", "Investment Fees & Costs", "Media Subscriptions",
    "One-off Expenses", "Personal Care", "Professional Fees & Memberships",
    "Social & Recreation", "Sport & Hobbies", "Technology & Equipment",
    "INCOME", "Other Income", "INTERNAL", "Unknown",
])


def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return {}


def save_overrides(overrides: dict):
    OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2), encoding="utf-8")


def transaction_key(row: pd.Series) -> str:
    return f"{row['date']}|{row['debit']}|{row['credit']}|{row['description'][:80]}"


data = load_data()
render_sidebar_summary(data)

st.title("Transactions")
st.caption("Filter, search, and click any Unknown row to assign a category.")

df = data["df"].copy()
overrides = load_overrides()


def apply_override(row):
    k = transaction_key(row)
    return overrides.get(k, row["domain"])


if overrides:
    df["domain"] = df.apply(apply_override, axis=1)

with st.sidebar:
    st.markdown("### Filters")
    search = st.text_input("Search description", placeholder="e.g. Coles, Uber, Bunnings")
    domains_filter = st.multiselect("Domain", options=DOMAINS, default=[])
    accounts_filter = st.multiselect(
        "Card / suffix",
        options=sorted(df["account_suffix"].dropna().unique().tolist()),
        default=[],
    )
    sources_filter = st.multiselect(
        "Source",
        options=sorted(df["source"].dropna().unique().tolist()),
        default=[],
    )
    years_filter = st.multiselect(
        "Year",
        options=sorted(df["year"].dropna().unique().astype(int).tolist(), reverse=True),
        default=[int(data["current_year"])],
    )
    only_unknown = st.checkbox("Only Unknown rows", value=False)
    show_internal = st.checkbox("Include INTERNAL transfers", value=False)

filtered = df.copy()
if search:
    filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
if domains_filter:
    filtered = filtered[filtered["domain"].isin(domains_filter)]
if accounts_filter:
    filtered = filtered[filtered["account_suffix"].isin(accounts_filter)]
if sources_filter:
    filtered = filtered[filtered["source"].isin(sources_filter)]
if years_filter:
    filtered = filtered[filtered["year"].isin(years_filter)]
if only_unknown:
    filtered = filtered[filtered["domain"] == "Unknown"]
if not show_internal:
    filtered = filtered[filtered["domain"] != "INTERNAL"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", f"{len(filtered):,}")
col2.metric("Total debits", fmt_money(filtered["debit_f"].sum()))
col3.metric("Total credits", fmt_money(filtered["credit_f"].sum()))
unknown_count = (filtered["domain"] == "Unknown").sum()
col4.metric("Unknown rows", f"{unknown_count:,}",
            f"{unknown_count/max(len(filtered),1)*100:.1f}% of filter",
            delta_color="off")

unknown_rows = filtered[filtered["domain"] == "Unknown"].copy()
if len(unknown_rows) > 0:
    st.subheader("⚡ Quick categorise an Unknown row")
    pick_cols = st.columns([3, 2, 1])
    with pick_cols[0]:
        unknown_rows = unknown_rows.sort_values("date", ascending=False).head(50)
        options = [
            f"[{r['date']}] ${(r['debit_f'] or r['credit_f']):,.2f} - {r['description'][:80]}"
            for _, r in unknown_rows.iterrows()
        ]
        chosen_idx = st.selectbox(
            "Pick an Unknown transaction (50 most recent shown):",
            options=range(len(options)),
            format_func=lambda i: options[i] if i < len(options) else "",
        )
    with pick_cols[1]:
        new_domain = st.selectbox("Assign category", options=DOMAINS,
                                   index=DOMAINS.index("Dining Out & Takeaway"))
    with pick_cols[2]:
        st.write("")
        if st.button("💾 Save", use_container_width=True):
            row = unknown_rows.iloc[chosen_idx]
            key = transaction_key(row)
            overrides[key] = new_domain
            save_overrides(overrides)
            st.success(f"Saved override: '{row['description'][:60]}' → {new_domain}")
            st.cache_data.clear()
            st.rerun()

if overrides:
    with st.expander(f"Active overrides ({len(overrides)})"):
        for k, v in list(overrides.items())[-20:]:
            st.text(f"→ {v}: {k[:90]}")

st.markdown("---")
st.subheader("Transactions")

cols = ["date", "description", "debit", "credit", "balance", "account_suffix",
        "domain", "source", "sub_source", "rule_used", "parse_confidence"]
display = filtered[cols].sort_values("date", ascending=False)

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    height=600,
)

st.caption(f"Showing {len(display):,} rows. To clear all filters, "
           "remove selections in the sidebar.")
