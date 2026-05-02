"""Compute aggregations and narrative content for the Streamlit dashboard.

Single source of truth for "what the numbers say". Pages consume these and
render them.

Data source: a CSV with one row per transaction. Path is taken from
TRANSACTIONS_CSV env var; defaults to ``sample_data/transactions_categorised.csv``
next to this module.

Required CSV columns:
  date, description, debit, credit, balance, account_suffix, domain,
  source, sub_source, rule_used, parse_confidence

`debit` / `credit` are positive numbers (or empty string). `domain` is one
of the labels in NON_DISCRETIONARY, DISCRETIONARY, or one of the special
labels INCOME / Other Income / INTERNAL / Unknown.

Optional config:
  HOUSEHOLD_NAME       — used for chart/page titles (default: "Household")
  MORTGAGE_LABEL       — domain label for the household's mortgage row
                         (default: "Housing – Mortgage")
  TIMELINE_EVENTS_JSON — path to a JSON list of {date, label} chart annotations.
                         If absent, no timeline events are emitted.
"""
from __future__ import annotations
import json
import os
import re
from datetime import date
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = ROOT / "sample_data" / "transactions_categorised.csv"
CAT_CSV = Path(os.environ.get("TRANSACTIONS_CSV", str(DEFAULT_CSV)))

HOUSEHOLD_NAME = os.environ.get("HOUSEHOLD_NAME", "Household")
MORTGAGE_LABEL = os.environ.get("MORTGAGE_LABEL", "Housing – Mortgage")

NON_DISCRETIONARY = {
    "Accounting & Tax", "Administrative & Post", "Baby Expenses", "Bank Fees",
    "Communications & Internet", "Debt Repayment", "Groceries",
    MORTGAGE_LABEL, "Insurance", "Medical & Health",
    "Pet Expenses", "Transport & Parking", "Utilities & Rates", "Vehicle Expenses",
    "Rent (historical)",
}
DISCRETIONARY = {
    "Alcohol", "Clothing & Footwear", "Dining Out & Takeaway", "Donations & Charity",
    "Education & Training", "Gifts", "Holidays & Travel", "Home & Garden",
    "Investment Fees & Costs", "Media Subscriptions", "One-off Expenses",
    "Personal Care", "Professional Fees & Memberships", "Social & Recreation",
    "Sport & Hobbies", "Technology & Equipment",
}
EXCLUDED_FROM_SPEND = {"INTERNAL", "INCOME", "Other Income", "—", "Unknown"}


def _load_timeline_events() -> list[tuple[date, str]]:
    path = os.environ.get("TIMELINE_EVENTS_JSON")
    if not path:
        path = str(ROOT / "timeline_events.json")
    p = Path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for item in raw:
        out.append((date.fromisoformat(item["date"]), str(item["label"])))
    return out


TIMELINE_EVENTS = _load_timeline_events()


def _to_float(v) -> float:
    try:
        return float(v) if v not in (None, "", "—") else 0.0
    except (TypeError, ValueError):
        return 0.0


def load_transactions() -> pd.DataFrame:
    df = pd.read_csv(CAT_CSV, dtype=str).fillna("")
    df["debit_f"] = df["debit"].apply(_to_float)
    df["credit_f"] = df["credit"].apply(_to_float)
    df["amount_signed"] = df["debit_f"] - df["credit_f"]
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["date_dt"].dt.year
    df["month"] = df["date_dt"].dt.to_period("M").astype(str)
    df = df[df["date_dt"].notna()].copy()
    return df


def by_year_domain(df: pd.DataFrame) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)].copy()
    pivot = spend.pivot_table(
        index="domain", columns="year", values="amount_signed",
        aggfunc="sum", fill_value=0.0,
    )
    return pivot.round(2)


def by_month_domain(df: pd.DataFrame) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)].copy()
    pivot = spend.pivot_table(
        index="domain", columns="month", values="amount_signed",
        aggfunc="sum", fill_value=0.0,
    )
    return pivot.round(2)


def income_by_year(df: pd.DataFrame) -> pd.DataFrame:
    inc = df[df["source"] == "income"].copy()
    inc["amount_in"] = inc["credit_f"]
    pivot = inc.pivot_table(
        index="sub_source", columns="year", values="amount_in",
        aggfunc="sum", fill_value=0.0,
    )
    return pivot.round(2)


def other_income_by_year(df: pd.DataFrame) -> pd.DataFrame:
    inc = df[df["domain"] == "Other Income"].copy()
    inc["amount_in"] = inc["credit_f"]
    pivot = inc.pivot_table(
        index="sub_source", columns="year", values="amount_in",
        aggfunc="sum", fill_value=0.0,
    )
    return pivot.round(2)


def cashflow_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, sub in df.groupby("year"):
        wage_income = sub.loc[sub["source"] == "income", "credit_f"].sum()
        other_inc = sub.loc[sub["domain"] == "Other Income", "credit_f"].sum()
        total_income = wage_income + other_inc
        spend = sub.loc[~sub["domain"].isin(EXCLUDED_FROM_SPEND), "amount_signed"].sum()
        net = total_income - spend
        savings_rate = (net / total_income) if total_income else 0.0
        non_disc = sub.loc[sub["domain"].isin(NON_DISCRETIONARY), "amount_signed"].sum()
        disc = sub.loc[sub["domain"].isin(DISCRETIONARY), "amount_signed"].sum()
        rows.append({
            "year": int(year),
            "wage_income": round(wage_income, 2),
            "other_income": round(other_inc, 2),
            "total_income": round(total_income, 2),
            "non_discretionary": round(non_disc, 2),
            "discretionary": round(disc, 2),
            "total_spend": round(spend, 2),
            "net": round(net, 2),
            "savings_rate": round(savings_rate, 4),
        })
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def discretionary_ranked(df: pd.DataFrame, year: int) -> pd.DataFrame:
    sub = df[(df["year"] == year) & (df["domain"].isin(DISCRETIONARY))]
    g = sub.groupby("domain")["amount_signed"].agg(["sum", "count"]).reset_index()
    g.columns = ["domain", "total", "transactions"]
    g["monthly_avg"] = (g["total"] / 12).round(2)
    top_merchants = []
    for domain in g["domain"]:
        d = sub[sub["domain"] == domain]
        merch = d.groupby("sub_source")["amount_signed"].sum().sort_values(ascending=False)
        top = merch.index[0] if len(merch) else ""
        top_merchants.append(top[:60])
    g["top_merchant"] = top_merchants
    g["if_cut_20pct"] = (g["total"] * 0.20).round(2)
    return g.sort_values("total", ascending=False).reset_index(drop=True)


def drift_metrics(df: pd.DataFrame, current_year: int, prior_year: int) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)]
    cur = spend[spend["year"] == current_year].groupby("domain")["amount_signed"].sum()
    prv = spend[spend["year"] == prior_year].groupby("domain")["amount_signed"].sum()
    total_cur = cur.sum()
    total_prv = prv.sum()
    total_growth = (total_cur - total_prv) / total_prv if total_prv else 0.0
    rows = []
    for domain in sorted(set(cur.index) | set(prv.index)):
        c = cur.get(domain, 0.0)
        p = prv.get(domain, 0.0)
        if c < 100 and p < 100:
            continue
        growth = (c - p) / p if p else (1.0 if c > 0 else 0.0)
        delta_vs_total = growth - total_growth
        rows.append({
            "domain": domain,
            f"spend_{prior_year}": round(p, 2),
            f"spend_{current_year}": round(c, 2),
            "yoy_growth": round(growth, 4),
            "vs_total_growth": round(delta_vs_total, 4),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("vs_total_growth", ascending=False).reset_index(drop=True)


def headlines(df: pd.DataFrame, current_year: int, prior_year: int) -> list[str]:
    """Pacing-led headlines: 'are we on track?'"""
    cards: list[tuple[float, str]] = []
    pacing = pacing_data(df, current_year, compare_years=2)
    var = variance_to_forecast(df, current_year)
    latest_m = latest_month_with_data(df, current_year)

    if not pacing.empty and latest_m > 0:
        cur_row = pacing[pacing["month_num"] == latest_m].iloc[0]
        actual_cum = cur_row.get("actual_cum")
        forecast_cum = cur_row.get("forecast_cum")
        py_cum = cur_row.get(f"py_{prior_year}_cum")
        month_name = cur_row["month"]
        if actual_cum is not None and forecast_cum:
            pct_of_forecast = (actual_cum / forecast_cum) * 100
            year_pct = (latest_m / 12) * 100
            tone = ("on track" if 90 <= pct_of_forecast <= 110
                    else ("ahead of forecast" if pct_of_forecast > 110 else "behind forecast"))
            cards.append((
                100,
                f"Through {month_name} ({year_pct:.0f}% of {current_year}): "
                f"${actual_cum:,.0f} spent vs ${forecast_cum:,.0f} forecast - "
                f"{pct_of_forecast:.0f}% of forecast pace ({tone})."
            ))
        if actual_cum is not None and py_cum:
            delta = actual_cum - py_cum
            direction = "more than" if delta > 0 else "less than"
            cards.append((
                70,
                f"Same period vs {prior_year}: ${actual_cum:,.0f} spent through {month_name} "
                f"vs ${py_cum:,.0f} last year - ${abs(delta):,.0f} {direction} prior year."
            ))

    if not var.empty:
        material = var[(var["ytd_forecast"] >= 100) | (var["ytd_actual"] >= 100)]
        material = material[material["status"].isin(["ahead of forecast", "behind forecast"])]
        if not material.empty:
            material = material.reindex(material["variance"].abs().sort_values(ascending=False).index)
            top = material.iloc[0]
            direction = "over" if top["variance"] > 0 else "under"
            pct_str = f"{abs(top['variance_pct'])*100:.0f}%" if top["variance_pct"] is not None else "n/a"
            cards.append((
                60,
                f"{top['domain']} is {direction} forecast by ${abs(top['variance']):,.0f} "
                f"({pct_str}) YTD - ${top['ytd_actual']:,.0f} actual vs "
                f"${top['ytd_forecast']:,.0f} expected."
            ))

    cf = cashflow_summary(df)
    cur_cf = cf[cf["year"] == current_year]
    prv_cf = cf[cf["year"] == prior_year]
    if not cur_cf.empty and not prv_cf.empty and latest_m > 0:
        c = cur_cf.iloc[0]
        p = prv_cf.iloc[0]
        annualised = (c["total_income"] / latest_m) * 12 if latest_m > 0 else c["total_income"]
        delta_vs_py = annualised - p["total_income"]
        direction = "ahead of" if delta_vs_py >= 0 else "behind"
        cards.append((
            55,
            f"Income annualised pace: ${annualised:,.0f}/yr (based on {latest_m} months) - "
            f"{direction} {prior_year} by ${abs(delta_vs_py):,.0f}."
        ))

    if not var.empty:
        disc_var = var[var["domain"].isin(DISCRETIONARY)]
        if not disc_var.empty:
            top_disc = disc_var.sort_values("ytd_actual", ascending=False).iloc[0]
            cards.append((
                40,
                f"Largest discretionary YTD: {top_disc['domain']} at "
                f"${top_disc['ytd_actual']:,.0f} (forecast ${top_disc['ytd_forecast']:,.0f} "
                f"for the same period - {top_disc['status']})."
            ))

    cards.sort(key=lambda x: -x[0])
    return [c[1] for c in cards[:5]]


def things_to_talk_about(df: pd.DataFrame, current_year: int) -> list[str]:
    prompts = []
    var = variance_to_forecast(df, current_year)
    if not var.empty:
        over = var[(var["status"] == "ahead of forecast") & (var["variance"] >= 200)]
        over = over.sort_values("variance", ascending=False).head(2)
        for _, r in over.iterrows():
            prompts.append(
                f"{r['domain']} is ${r['variance']:,.0f} over the forecast pace YTD. "
                f"Was something planned different, or is this drift worth addressing?"
            )
    cf = cashflow_summary(df)
    cur = cf[cf["year"] == current_year]
    if not cur.empty:
        c = cur.iloc[0]
        if c["total_income"] > 0:
            disc_pct = c["discretionary"] / c["total_income"]
            if disc_pct > 0.30:
                prompts.append(
                    f"Discretionary spend is {disc_pct*100:.0f}% of take-home income "
                    f"in {current_year}. Comfortable with that, or worth cutting?"
                )
            elif disc_pct < 0.10:
                prompts.append(
                    f"Discretionary spend is only {disc_pct*100:.0f}% of take-home — quite "
                    f"lean. Anything you've been holding off on that you'd actually enjoy?"
                )

    return prompts[:3]


def unknown_for_review(df: pd.DataFrame) -> pd.DataFrame:
    unk = df[df["domain"] == "Unknown"].copy()
    if unk.empty:
        return pd.DataFrame()

    def k(s: str) -> str:
        s = re.sub(r"\s*\|\s*Card\s*xx\s*\d{4}|\s+Card\s*xx\s*\d{4}", "", str(s), flags=re.I)
        s = re.sub(r"\s+\d{3,5}\b.*$", "", s)
        s = re.sub(r"\s+", " ", s).upper().strip()
        return " ".join(s.split(" ")[:4])

    unk["key"] = unk["description"].apply(k)
    g = unk.groupby("key").agg(
        rows=("description", "count"),
        total=("amount_signed", "sum"),
        sample=("description", "first"),
    ).sort_values("rows", ascending=False).reset_index()
    g["sample"] = g["sample"].str.slice(0, 100)
    g["total"] = g["total"].round(2)
    return g.head(40)


def detect_current_year(df: pd.DataFrame) -> tuple[int, int]:
    years = sorted({int(y) for y in df["year"].dropna().unique()})
    if not years:
        return date.today().year, date.today().year - 1
    current = years[-1]
    prior = years[-2] if len(years) >= 2 else current - 1
    return current, prior


def complete_years(df: pd.DataFrame, min_months: int = 11) -> list[int]:
    months_per_year = df.groupby("year")["month"].nunique()
    return sorted([int(y) for y, m in months_per_year.items() if m >= min_months])


def latest_month_with_data(df: pd.DataFrame, year: int) -> int:
    sub = df[df["year"] == year]
    if sub.empty:
        return 0
    return int(sub["date_dt"].dt.month.max())


def forecast_annual(df: pd.DataFrame, year: int, inflation: float = 0.04,
                    prior_years: int = 2) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)].copy()
    eligible = [y for y in complete_years(spend) if y < year]
    eligible = eligible[-prior_years:]

    if not eligible:
        eligible = sorted({int(y) for y in spend["year"].dropna().unique() if y < year})[-prior_years:]
    if not eligible:
        return pd.DataFrame(columns=["domain", "prior_avg", "forecast_total",
                                      "forecast_monthly"])

    by_yr_dom = spend.pivot_table(index="domain", columns="year",
                                   values="amount_signed", aggfunc="sum",
                                   fill_value=0.0)
    rows = []
    for domain in by_yr_dom.index:
        prior_vals = []
        cells = {}
        for y in eligible:
            v = float(by_yr_dom.loc[domain, y]) if y in by_yr_dom.columns else 0.0
            prior_vals.append(v)
            cells[f"actual_{y}"] = round(v, 2)
        avg = sum(prior_vals) / len(prior_vals)
        forecast = avg * (1.0 + inflation)
        rows.append({
            "domain": domain,
            **cells,
            "prior_avg": round(avg, 2),
            "inflation": inflation,
            "forecast_total": round(forecast, 2),
            "forecast_monthly": round(forecast / 12.0, 2),
        })
    out = pd.DataFrame(rows)
    return out.sort_values("forecast_total", ascending=False).reset_index(drop=True)


def pacing_data(df: pd.DataFrame, year: int, compare_years: int = 2) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)].copy()
    spend["m"] = spend["date_dt"].dt.month

    monthly_by_year: dict[int, pd.Series] = {}
    for y in sorted({int(yy) for yy in spend["year"].dropna().unique()}):
        s = spend[spend["year"] == y].groupby("m")["amount_signed"].sum()
        s = s.reindex(range(1, 13), fill_value=0.0)
        monthly_by_year[y] = s

    fc = forecast_annual(df, year, inflation=0.04, prior_years=2)
    forecast_total_annual = fc["forecast_total"].sum() if not fc.empty else 0.0
    forecast_monthly_value = forecast_total_annual / 12.0

    rows = []
    cum_actual = cum_forecast = cum_py = cum_py2 = 0.0
    py_year = year - 1
    py2_year = year - 2
    for m in range(1, 13):
        cum_actual += monthly_by_year.get(year, pd.Series([0]*12, index=range(1, 13)))[m]
        cum_forecast += forecast_monthly_value
        cum_py += monthly_by_year.get(py_year, pd.Series([0]*12, index=range(1, 13)))[m]
        cum_py2 += monthly_by_year.get(py2_year, pd.Series([0]*12, index=range(1, 13)))[m]
        rows.append({
            "month": date(year, m, 1).strftime("%b"),
            "month_num": m,
            "actual_cum": round(cum_actual, 2) if year in monthly_by_year else None,
            "forecast_cum": round(cum_forecast, 2),
            f"py_{py_year}_cum": round(cum_py, 2) if py_year in monthly_by_year else None,
            f"py_{py2_year}_cum": round(cum_py2, 2) if py2_year in monthly_by_year else None,
        })
    out = pd.DataFrame(rows)

    latest = latest_month_with_data(df, year)
    if year in monthly_by_year:
        for i in range(len(out)):
            if out.loc[i, "month_num"] > latest:
                out.loc[i, "actual_cum"] = None
    return out


def variance_to_forecast(df: pd.DataFrame, year: int, inflation: float = 0.04) -> pd.DataFrame:
    spend = df[~df["domain"].isin(EXCLUDED_FROM_SPEND)].copy()
    latest = latest_month_with_data(df, year)
    if latest == 0:
        return pd.DataFrame()
    fc = forecast_annual(df, year, inflation=inflation, prior_years=2)
    if fc.empty:
        return pd.DataFrame()
    fc = fc.set_index("domain")
    ytd_actual = (spend[(spend["year"] == year) &
                        (spend["date_dt"].dt.month <= latest)]
                  .groupby("domain")["amount_signed"].sum())
    rows = []
    for domain, frow in fc.iterrows():
        actual = float(ytd_actual.get(domain, 0.0))
        forecast_ytd = float(frow["forecast_monthly"]) * latest
        variance = actual - forecast_ytd
        if forecast_ytd > 0:
            variance_pct = variance / forecast_ytd
        else:
            variance_pct = None
        if forecast_ytd == 0 and actual == 0:
            status = "no activity"
        elif variance_pct is None:
            status = "new spend (no forecast)"
        elif variance_pct > 0.10:
            status = "ahead of forecast"
        elif variance_pct < -0.10:
            status = "behind forecast"
        else:
            status = "on track"
        rows.append({
            "domain": domain,
            "ytd_actual": round(actual, 2),
            "ytd_forecast": round(forecast_ytd, 2),
            "variance": round(variance, 2),
            "variance_pct": variance_pct,
            "status": status,
        })
    out = pd.DataFrame(rows)
    return out.sort_values("variance", ascending=False).reset_index(drop=True)


def compute_all() -> dict:
    df = load_transactions()
    current, prior = detect_current_year(df)

    return {
        "df": df,
        "current_year": current,
        "prior_year": prior,
        "by_year_domain": by_year_domain(df),
        "by_month_domain": by_month_domain(df),
        "income_by_year": income_by_year(df),
        "other_income_by_year": other_income_by_year(df),
        "cashflow": cashflow_summary(df),
        "discretionary_ranked": discretionary_ranked(df, current),
        "drift": drift_metrics(df, current, prior),
        "headlines": headlines(df, current, prior),
        "talk_about": things_to_talk_about(df, current),
        "unknowns": unknown_for_review(df),
        "timeline_events": TIMELINE_EVENTS,
    }
