"""
Supply Chain Analytics - Synthetic Dataset Generator
Generates 50 suppliers, 2,000 purchase orders, 18 months of history
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

# ── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# ── Config ───────────────────────────────────────────────────────────────────
N_SUPPLIERS    = 50
N_ORDERS       = 2000
START_DATE     = datetime(2023, 1, 1)
END_DATE       = datetime(2024, 6, 30)   # 18 months
N_UNDERPERFORM = 12                       # suppliers with chronic late delivery
ESCALATING_SUP = "SUP-007"              # one supplier with worsening defects
OUTPUT_DIR     = "data"

# ── Lookup tables ─────────────────────────────────────────────────────────────
CATEGORIES = ["Raw Materials", "Electronics", "Packaging"]

CATEGORY_WEIGHTS = [0.40, 0.35, 0.25]   # realistic procurement mix

COUNTRIES = [
    "China", "Germany", "Mexico", "India", "United States",
    "Vietnam", "South Korea", "Brazil", "Taiwan", "Japan",
    "Canada", "Poland", "Thailand", "Indonesia", "Turkey",
]

COUNTRY_WEIGHTS = [
    0.20, 0.10, 0.10, 0.10, 0.08,
    0.08, 0.07, 0.06, 0.06, 0.05,
    0.04, 0.02, 0.02, 0.01, 0.01,
]

# Cost ranges (USD per unit) by category
COST_PARAMS = {
    "Raw Materials": (5,   500),
    "Electronics":  (20, 2500),
    "Packaging":    (1,    80),
}

# Typical lead times (calendar days) by category
LEAD_TIME_PARAMS = {
    "Raw Materials": (14, 45),
    "Electronics":  (21, 60),
    "Packaging":    (7,  21),
}

# Seasonal delay multiplier by month (1 = no extra delay, >1 = longer delays)
SEASONAL_DELAY = {
    1: 1.0, 2: 1.0, 3: 1.1,   # Q1: slight spring ramp-up
    4: 0.95, 5: 0.95, 6: 1.0,
    7: 1.05, 8: 1.1, 9: 1.2,  # Q3: summer slowdown + pre-holiday rush
    10: 1.3, 11: 1.5, 12: 1.4, # Q4: peak season crunch
}


# ── Step 1 — Build supplier master ───────────────────────────────────────────
def build_suppliers() -> pd.DataFrame:
    supplier_ids = [f"SUP-{str(i).zfill(3)}" for i in range(1, N_SUPPLIERS + 1)]

    # Assign underperforming flag (exclude escalating supplier from this pool)
    underperform_pool = [s for s in supplier_ids if s != ESCALATING_SUP]
    underperformers   = set(random.sample(underperform_pool, N_UNDERPERFORM))
    underperformers.add(ESCALATING_SUP)  # escalating supplier also underperforms

    categories = np.random.choice(CATEGORIES, size=N_SUPPLIERS, p=CATEGORY_WEIGHTS)
    countries  = np.random.choice(COUNTRIES,  size=N_SUPPLIERS, p=COUNTRY_WEIGHTS)

    # Base on-time rate: normal ~92%, underperformer ~60-75%
    on_time_rates = []
    for sid in supplier_ids:
        if sid in underperformers:
            on_time_rates.append(round(np.random.uniform(0.55, 0.74), 2))
        else:
            on_time_rates.append(round(np.random.uniform(0.88, 0.98), 2))

    # Base defect rate by category
    base_defects = []
    for cat in categories:
        if cat == "Electronics":
            base_defects.append(round(np.random.uniform(0.005, 0.03), 4))
        elif cat == "Raw Materials":
            base_defects.append(round(np.random.uniform(0.01, 0.05), 4))
        else:
            base_defects.append(round(np.random.uniform(0.002, 0.015), 4))

    suppliers = pd.DataFrame({
        "supplier_id":     supplier_ids,
        "supplier_name":   [f"Supplier {sid}" for sid in supplier_ids],
        "category":        categories,
        "country_of_origin": countries,
        "base_on_time_rate": on_time_rates,
        "base_defect_rate":  base_defects,
        "is_underperformer": [sid in underperformers for sid in supplier_ids],
    })

    return suppliers


# ── Step 2 — Generate purchase orders ────────────────────────────────────────
def generate_orders(suppliers: pd.DataFrame) -> pd.DataFrame:
    records = []

    # Weight orders toward higher-volume suppliers (realistic Pareto-ish)
    supplier_order_weights = np.random.dirichlet(np.ones(N_SUPPLIERS) * 0.8)

    po_supplier_ids = np.random.choice(
        suppliers["supplier_id"].values,
        size=N_ORDERS,
        p=supplier_order_weights,
    )

    # Spread PO dates across 18-month window, slightly weighted toward working days
    date_range_days = (END_DATE - START_DATE).days
    po_offsets = np.random.randint(0, date_range_days, size=N_ORDERS)
    po_dates   = [START_DATE + timedelta(days=int(d)) for d in po_offsets]

    for i, (sid, po_date) in enumerate(zip(po_supplier_ids, po_dates)):
        sup_row = suppliers[suppliers["supplier_id"] == sid].iloc[0]
        cat     = sup_row["category"]

        # Lead time & promised delivery
        min_lead, max_lead = LEAD_TIME_PARAMS[cat]
        promised_lead      = np.random.randint(min_lead, max_lead + 1)
        promised_date      = po_date + timedelta(days=int(promised_lead))

        # Seasonal multiplier on the month PO was placed
        seasonal_mult = SEASONAL_DELAY[po_date.month]

        # Determine if this order is late
        on_time_rate = sup_row["base_on_time_rate"]
        is_late      = np.random.random() > (on_time_rate / seasonal_mult)

        if is_late:
            # Underperformers are later (5-25 days), others 1-7 days
            if sup_row["is_underperformer"]:
                delay_days = np.random.randint(5, 26)
            else:
                delay_days = np.random.randint(1, 8)
            # Additional seasonal pile-on in Q4
            if po_date.month in [10, 11, 12]:
                delay_days += np.random.randint(0, 6)
        else:
            # Occasionally delivers slightly early
            delay_days = np.random.randint(-2, 3)

        actual_date = promised_date + timedelta(days=int(delay_days))
        # Actual can't precede PO date
        actual_date = max(actual_date, po_date + timedelta(days=1))

        # Unit cost with noise
        min_cost, max_cost = COST_PARAMS[cat]
        unit_cost = round(np.random.uniform(min_cost, max_cost), 2)

        # Quantity by category
        if cat == "Raw Materials":
            qty = np.random.randint(100, 5001)
        elif cat == "Electronics":
            qty = np.random.randint(10, 501)
        else:
            qty = np.random.randint(500, 10001)

        # Defect rate — escalating supplier gets worse over time
        base_defect = sup_row["base_defect_rate"]
        if sid == ESCALATING_SUP:
            months_elapsed = (po_date - START_DATE).days / 30.0
            # Escalates from base to ~5x base over 18 months
            escalation = 1.0 + (months_elapsed / 18.0) * 4.0
            defect_rate = round(
                min(base_defect * escalation * np.random.uniform(0.9, 1.1), 0.35), 4
            )
        elif sup_row["is_underperformer"]:
            defect_rate = round(
                min(base_defect * np.random.uniform(1.5, 3.0), 0.30), 4
            )
        else:
            defect_rate = round(
                max(base_defect * np.random.uniform(0.8, 1.2), 0.001), 4
            )

        records.append({
            "po_id":               f"PO-{str(i + 1).zfill(5)}",
            "supplier_id":         sid,
            "category":            cat,
            "country_of_origin":   sup_row["country_of_origin"],
            "po_date":             po_date.date(),
            "promised_delivery_date": promised_date.date(),
            "actual_delivery_date":   actual_date.date(),
            "unit_cost":           unit_cost,
            "quantity":            qty,
            "defect_rate":         defect_rate,
            "total_value":         round(unit_cost * qty, 2),
            "days_late":           (actual_date - promised_date).days,
            "on_time_flag":        int((actual_date - promised_date).days <= 0),
        })

    return pd.DataFrame(records)


# ── Step 3 — Derived/summary tables ──────────────────────────────────────────
def build_supplier_scorecard(
    orders: pd.DataFrame, suppliers: pd.DataFrame
) -> pd.DataFrame:
    agg = (
        orders.groupby("supplier_id")
        .agg(
            total_orders    = ("po_id",          "count"),
            on_time_count   = ("on_time_flag",   "sum"),
            avg_days_late   = ("days_late",       "mean"),
            avg_defect_rate = ("defect_rate",     "mean"),
            total_spend     = ("total_value",     "sum"),
            avg_unit_cost   = ("unit_cost",       "mean"),
        )
        .reset_index()
    )
    agg["on_time_pct"] = (agg["on_time_count"] / agg["total_orders"]).round(4)
    agg["avg_days_late"] = agg["avg_days_late"].round(2)
    agg["avg_defect_rate"] = agg["avg_defect_rate"].round(4)
    agg["total_spend"] = agg["total_spend"].round(2)
    agg["avg_unit_cost"] = agg["avg_unit_cost"].round(2)

    scorecard = agg.merge(
        suppliers[["supplier_id", "supplier_name", "category",
                   "country_of_origin", "is_underperformer"]],
        on="supplier_id",
        how="left",
    )
    return scorecard


def build_monthly_trends(orders: pd.DataFrame) -> pd.DataFrame:
    orders = orders.copy()
    orders["po_month"] = pd.to_datetime(orders["po_date"]).dt.to_period("M").astype(str)

    monthly = (
        orders.groupby(["po_month", "category"])
        .agg(
            order_count     = ("po_id",        "count"),
            on_time_pct     = ("on_time_flag", "mean"),
            avg_days_late   = ("days_late",    "mean"),
            avg_defect_rate = ("defect_rate",  "mean"),
            total_spend     = ("total_value",  "sum"),
        )
        .reset_index()
    )
    monthly["on_time_pct"]     = monthly["on_time_pct"].round(4)
    monthly["avg_days_late"]   = monthly["avg_days_late"].round(2)
    monthly["avg_defect_rate"] = monthly["avg_defect_rate"].round(4)
    monthly["total_spend"]     = monthly["total_spend"].round(2)
    return monthly


# ── Step 4 — Data quality checks ─────────────────────────────────────────────
def run_quality_checks(orders: pd.DataFrame) -> None:
    print("\n── Data Quality Report ──────────────────────────────────────────")
    print(f"  Total orders      : {len(orders):,}")
    print(f"  Unique suppliers  : {orders['supplier_id'].nunique()}")
    print(f"  Date range        : {orders['po_date'].min()} → {orders['po_date'].max()}")
    print(f"  Null values       :\n{orders.isnull().sum().to_string()}")

    # Logical checks
    assert (
        pd.to_datetime(orders["actual_delivery_date"])
        >= pd.to_datetime(orders["po_date"])
    ).all(), "FAIL: actual_delivery_date before po_date"

    assert (orders["unit_cost"] > 0).all(),   "FAIL: non-positive unit_cost"
    assert (orders["quantity"]  > 0).all(),   "FAIL: non-positive quantity"
    assert (orders["defect_rate"].between(0, 1)).all(), "FAIL: defect_rate out of [0,1]"

    late_pct = 1 - orders["on_time_flag"].mean()
    defect_mean = orders["defect_rate"].mean()
    print(f"\n  Late delivery rate : {late_pct:.1%}")
    print(f"  Mean defect rate   : {defect_mean:.3%}")

    # Escalation check
    esc = orders[orders["supplier_id"] == ESCALATING_SUP].copy()
    esc["po_date"] = pd.to_datetime(esc["po_date"])
    esc = esc.sort_values("po_date")
    first_half = esc[esc["po_date"] < esc["po_date"].median()]["defect_rate"].mean()
    second_half = esc[esc["po_date"] >= esc["po_date"].median()]["defect_rate"].mean()
    print(f"\n  {ESCALATING_SUP} defect escalation:")
    print(f"    First-half mean  : {first_half:.3%}")
    print(f"    Second-half mean : {second_half:.3%}")
    assert second_half > first_half, "WARN: escalation not detected"

    print("\n  ✓ All quality checks passed.\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating suppliers...")
    suppliers = build_suppliers()

    print("Generating purchase orders...")
    orders = generate_orders(suppliers)

    print("Building scorecard & monthly trends...")
    scorecard = build_supplier_scorecard(orders, suppliers)
    monthly   = build_monthly_trends(orders)

    run_quality_checks(orders)

    # ── Write CSVs ────────────────────────────────────────────────────────────
    out_map = {
        "purchase_orders.csv":    orders.drop(columns=["total_value"]),
        "suppliers.csv":          suppliers,
        "supplier_scorecard.csv": scorecard,
        "monthly_trends.csv":     monthly,
    }

    # Also export a version with total_value for Power BI convenience
    orders_full = orders.copy()
    orders_full.to_csv(f"{OUTPUT_DIR}/purchase_orders_enriched.csv", index=False)

    for filename, df in out_map.items():
        path = os.path.join(OUTPUT_DIR, filename)
        df.to_csv(path, index=False)
        print(f"  ✓ Saved {path}  ({len(df):,} rows)")

    print(f"\nDone. All files written to /{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()


