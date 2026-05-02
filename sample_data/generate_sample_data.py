"""Generate a synthetic transactions CSV for demo purposes.

The output is deterministic (fixed seed) so tweaking the script and rerunning
gives a stable baseline. None of the merchants, names, or account suffixes are
real — they're chosen to look reasonable to a stranger reading the dashboard.

Run from the repo root:
    python sample_data/generate_sample_data.py
"""
from __future__ import annotations
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(20260101)

OUT = Path(__file__).resolve().parent / "transactions_categorised.csv"

# (merchant, domain, source, sub_source, mean, stdev, freq_per_month)
EXPENSES = [
    ("FreshMart Supermarket",      "Groceries",                     "expense", "FreshMart",      120, 25, 8),
    ("Corner Grocer",              "Groceries",                     "expense", "Corner Grocer",   45, 10, 4),
    ("BeanCo Coffee",              "Dining Out & Takeaway",         "expense", "BeanCo",          12,  3, 12),
    ("Pizza Palace",               "Dining Out & Takeaway",         "expense", "Pizza Palace",    35,  8, 3),
    ("FastFoods Drive-Thru",       "Dining Out & Takeaway",         "expense", "FastFoods",       22,  6, 6),
    ("FuelStop Petrol",            "Vehicle Expenses",              "expense", "FuelStop",        85, 12, 5),
    ("CityRail",                   "Transport & Parking",           "expense", "CityRail",         8,  2, 8),
    ("Parking Authority",          "Transport & Parking",           "expense", "Parking Authority", 15,  4, 4),
    ("HomePower Utilities",        "Utilities & Rates",             "expense", "HomePower",      280, 30, 1),
    ("WaterCorp",                  "Utilities & Rates",             "expense", "WaterCorp",      120, 15, 1),
    ("Council Rates",              "Utilities & Rates",             "expense", "Council Rates",  450, 20, 1),
    ("Telco Plus Mobile",          "Communications & Internet",     "expense", "Telco Plus",      60,  0, 1),
    ("FibreNet Internet",          "Communications & Internet",     "expense", "FibreNet",        85,  0, 1),
    ("HealthShield Insurance",     "Insurance",                     "expense", "HealthShield",   220, 10, 1),
    ("AutoSure Car Insurance",     "Insurance",                     "expense", "AutoSure",       105, 10, 1),
    ("HomeSafe Insurance",         "Insurance",                     "expense", "HomeSafe",       180, 10, 1),
    ("MedCentre",                  "Medical & Health",              "expense", "MedCentre",       90, 25, 2),
    ("CityPharmacy",               "Medical & Health",              "expense", "CityPharmacy",    32, 12, 3),
    ("VetCare Animal Hospital",    "Pet Expenses",                  "expense", "VetCare",        120, 40, 1),
    ("PetSupplies Co",             "Pet Expenses",                  "expense", "PetSupplies",     55, 15, 2),
    ("BookworldOnline",            "Media Subscriptions",           "expense", "BookworldOnline", 16,  0, 1),
    ("StreamFlix",                 "Media Subscriptions",           "expense", "StreamFlix",      19,  0, 1),
    ("MusicCloud",                 "Media Subscriptions",           "expense", "MusicCloud",      12,  0, 1),
    ("Big Box Hardware",           "Home & Garden",                 "expense", "Big Box Hardware", 65, 30, 2),
    ("Garden Nursery",             "Home & Garden",                 "expense", "Garden Nursery",   40, 18, 1),
    ("Fashion Outlet",             "Clothing & Footwear",           "expense", "Fashion Outlet",   80, 35, 2),
    ("ShoeStore",                  "Clothing & Footwear",           "expense", "ShoeStore",       110, 20, 1),
    ("WineCellar",                 "Alcohol",                       "expense", "WineCellar",       55, 15, 2),
    ("LocalBrewery",               "Alcohol",                       "expense", "LocalBrewery",     38, 12, 2),
    ("CinemaWorld",                "Social & Recreation",           "expense", "CinemaWorld",      28,  6, 2),
    ("Mini Golf Co",               "Social & Recreation",           "expense", "Mini Golf Co",     45,  8, 1),
    ("FitnessFirst Gym",           "Sport & Hobbies",               "expense", "FitnessFirst",     65,  0, 1),
    ("YogaStudio",                 "Sport & Hobbies",               "expense", "YogaStudio",       45,  0, 1),
    ("TechMegaStore",              "Technology & Equipment",        "expense", "TechMegaStore",   180, 80, 1),
    ("Hairdresser",                "Personal Care",                 "expense", "Hairdresser",      55, 10, 1),
    ("Beauty Spa",                 "Personal Care",                 "expense", "Beauty Spa",       95, 25, 1),
    ("Charity Foundation",         "Donations & Charity",           "expense", "Charity Foundation", 25, 0, 1),
    ("Birthday Gift Shop",         "Gifts",                         "expense", "Birthday Gift Shop", 60, 25, 1),
    ("Travel Agency",              "Holidays & Travel",             "expense", "Travel Agency",   850, 200, 0.3),
    ("BankFee",                    "Bank Fees",                     "expense", "BankFee",           4,  0, 1),
    ("Accounting Services",        "Accounting & Tax",              "expense", "Accounting Services", 350, 0, 0.1),
    ("Australia Post",             "Administrative & Post",         "expense", "Australia Post",   18,  6, 2),
    ("Online Learning",            "Education & Training",          "expense", "Online Learning",  45, 0, 0.5),
    ("Professional Body Membership", "Professional Fees & Memberships", "expense", "Professional Body", 220, 0, 0.1),
    ("OnceOff Repair",             "One-off Expenses",              "expense", "OnceOff Repair",  120, 80, 0.4),
]

MORTGAGE = ("Home Loan Repayment", "Housing – Mortgage", "expense", "Home Loan", 920, 0, 4)  # weekly
INCOME_PAYER_A = ("Salary Employer A", "INCOME",  "income", "Employer A — Wage", 3400, 200, 2)  # fortnightly
INCOME_PAYER_B = ("Salary Employer B", "INCOME",  "income", "Employer B — Wage", 2800, 150, 2)  # fortnightly

START = date(2023, 1, 1)
END = date(2025, 5, 1)


def emit_row(writer, dt: date, description: str, debit: float, credit: float,
              domain: str, source: str, sub_source: str, suffix: str = "xx9001",
              rule: str = "merchant_match", balance: float = 0.0):
    writer.writerow({
        "date": dt.strftime("%Y-%m-%d"),
        "description": description,
        "debit": f"{debit:.2f}" if debit else "",
        "credit": f"{credit:.2f}" if credit else "",
        "balance": f"{balance:.2f}",
        "account_suffix": suffix,
        "domain": domain,
        "source": source,
        "sub_source": sub_source,
        "rule_used": rule,
        "parse_confidence": "high",
    })


def main():
    rows_written = 0
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "description", "debit", "credit", "balance",
            "account_suffix", "domain", "source", "sub_source", "rule_used",
            "parse_confidence",
        ])
        writer.writeheader()

        balance = 5000.0
        d = START
        while d <= END:
            month_start = d
            # Walk one month
            for day_offset in range(31):
                cur = month_start + timedelta(days=day_offset)
                if cur.month != month_start.month:
                    break

                # Mortgage every Monday
                if cur.weekday() == 0:
                    desc, dom, src, ss, mean, sd, _ = MORTGAGE
                    amt = round(mean + random.gauss(0, sd), 2)
                    balance -= amt
                    emit_row(writer, cur, desc, amt, 0, dom, src, ss, "xx9001",
                             "mortgage_pattern", balance)
                    rows_written += 1

                # Fortnightly wages every other Wednesday
                if cur.weekday() == 2:
                    days_since_start = (cur - START).days
                    weeks_since_start = days_since_start // 7
                    if weeks_since_start % 2 == 0:
                        for payer in (INCOME_PAYER_A, INCOME_PAYER_B):
                            desc, dom, src, ss, mean, sd, _ = payer
                            amt = round(mean + random.gauss(0, sd), 2)
                            balance += amt
                            emit_row(writer, cur, desc, 0, amt, dom, src, ss, "xx9001",
                                     "income_match", balance)
                            rows_written += 1

                # Random expenses for the day
                for merch in EXPENSES:
                    desc, dom, src, ss, mean, sd, freq = merch
                    daily_p = freq / 30.0
                    if random.random() < daily_p:
                        amt = round(max(1, mean + random.gauss(0, sd)), 2)
                        balance -= amt
                        suffix = random.choice(["xx9001", "xx9002", "xx9003"])
                        emit_row(writer, cur, desc,
                                 amt, 0, dom, src, ss, suffix, "merchant_match", balance)
                        rows_written += 1

            # Move to first of next month
            year = d.year + (1 if d.month == 12 else 0)
            month = 1 if d.month == 12 else d.month + 1
            d = date(year, month, 1)

    print(f"Wrote {rows_written:,} synthetic rows to {OUT}")


if __name__ == "__main__":
    main()
