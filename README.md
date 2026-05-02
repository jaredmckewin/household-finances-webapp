# Household Finances Web App

A Streamlit dashboard for a household to track spending, forecast the year
ahead, and have informed money conversations. Designed as a *conversation
tool* — narrative headlines and trend lines come first, raw tables come last.

The app is data-agnostic: point it at a categorised transactions CSV and it
computes pacing, forecasts, drift, and a what-if simulator from there.

## Quick start

```bash
git clone https://github.com/<your-username>/household-finances-webapp.git
cd household-finances-webapp
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The bundled `sample_data/transactions_categorised.csv`
holds about three years of synthetic transactions so the app has something to
chew on out of the box.

## Pages

| Page | What it does |
|---|---|
| **Conversation** | One-screen overview: hero KPIs, pacing chart, narrative headlines, decision prompts. |
| **Pacing & Forecast** | Inflation slider drives a live forecast and variance recompute. Drill into any category to see monthly bars, top merchants, latest transactions. |
| **Transactions** | Filterable master with full-text search and a quick-categorise widget for Unknown rows. |
| **Trends & Drift** | YoY comparison, multi-year history per category, and a "drift" table flagging categories growing faster than total spend. |
| **What-If** | A slider per discretionary category. Move them to model 0–50% cuts and watch the projected savings rate update live. |

## Bringing your own data

Replace `sample_data/transactions_categorised.csv` (or set the
`TRANSACTIONS_CSV` env var). The CSV must have these columns:

```
date, description, debit, credit, balance, account_suffix, domain,
source, sub_source, rule_used, parse_confidence
```

`debit` and `credit` are positive numbers, one of them empty per row. `domain`
must be one of the labels listed in `analytics.py` (`NON_DISCRETIONARY`,
`DISCRETIONARY`) plus the special values `INCOME`, `Other Income`, `INTERNAL`,
`Unknown`. Rows with `INTERNAL`, `INCOME`, `Other Income`, `Unknown`, or `—`
domains are excluded from spend totals.

For a forecast to be computed you need at least two complete prior years of
data plus a current year (any number of months).

## Configuration

All config is via environment variables. See `.env.example` for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `HOUSEHOLD_NAME` | `Household` | Shown in page titles and the sidebar. |
| `MORTGAGE_LABEL` | `Housing – Mortgage` | Mortgage-row label in the domain list. Must match the value in the CSV. |
| `TRANSACTIONS_CSV` | `sample_data/transactions_categorised.csv` | Path to your categorised CSV. |
| `TIMELINE_EVENTS_JSON` | *(unset)* | Optional path to a JSON list of `{date, label}` chart annotations. |
| `OVERRIDES_PATH` | `manual_overrides.json` | Where to persist manual category overrides. |

## Project layout

```
.
├── app.py                # Conversation home page
├── shared.py             # Theme, chart helpers, sidebar
├── analytics.py          # All aggregations + forecast math
├── pages/
│   ├── 1_Pacing_and_Forecast.py
│   ├── 2_Transactions.py
│   ├── 3_Trends_and_Drift.py
│   └── 4_What_If.py
├── sample_data/
│   ├── generate_sample_data.py    # Re-run to regenerate the demo CSV
│   └── transactions_categorised.csv
├── requirements.txt
├── .env.example
└── README.md
```

## Privacy

This repo contains **no real transaction data**. The bundled CSV is generated
deterministically by `sample_data/generate_sample_data.py` with synthetic
merchants and amounts. `.gitignore` excludes the typical extensions and folders
that would accidentally pull real data in (`*.csv` outside `sample_data/`,
`*.xlsx`, `*.pdf`, `data/`, `outputs/`, `.env`, etc.).

If you fork this and start using it with real data, double-check before every
push.

## License

MIT — see [LICENSE](LICENSE).
