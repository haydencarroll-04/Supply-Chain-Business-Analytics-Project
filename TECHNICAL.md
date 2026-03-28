# Technical Documentation — Data Generation

## How `generate_data.py` Works

The script runs in four sequential steps, each handled by a dedicated function. Running `python generate_data.py` executes them all and writes five CSV files to `/data`.

---

### Step 1 — `build_suppliers()`

Builds the 50-row supplier master table that everything else depends on.

- Generates supplier IDs (`SUP-001` through `SUP-050`)
- Randomly assigns each supplier a **category** (Raw Materials 40%, Electronics 35%, Packaging 25%) and **country of origin** (weighted toward China, Germany, Mexico, India)
- Randomly selects **12 underperforming suppliers** and assigns them a low baseline on-time rate (55–74%). Healthy suppliers get 88–98%
- Assigns **SUP-007** as the escalating defect supplier — it is also flagged as an underperformer
- Sets a **base defect rate** per supplier, calibrated by category: Raw Materials runs highest (1–5%), Electronics moderate (0.5–3%), Packaging lowest (0.2–1.5%)

This table is the reference that all purchase order logic reads from.

---

### Step 2 — `generate_orders()`

Generates the 2,000-row purchase order fact table by looping over each order and computing every field from first principles.

**Order distribution** — Supplier selection uses a Dirichlet distribution (`alpha=0.8`) to create unequal order volumes across suppliers, mimicking the real-world Pareto pattern where a minority of suppliers handle the majority of orders.

**Dates** — PO dates are randomly spread across the 18-month window (Jan 2023 – Jun 2024). Promised delivery date is PO date plus a random lead time drawn from category-specific ranges (Packaging 7–21 days, Raw Materials 14–45 days, Electronics 21–60 days).

**Late delivery logic** — For each order, the script computes whether it arrives late using:

```
is_late = random() > (supplier_on_time_rate / seasonal_multiplier)
```

The seasonal multiplier degrades the effective on-time rate by month — Q4 (Oct–Dec) applies a 1.3–1.5× multiplier, pushing more orders into late status during peak season. If late, underperformers are delayed 5–25 days; healthy suppliers 1–7 days, with an additional 0–5 day Q4 pile-on.

**Defect rate logic** — Three tiers:
- **SUP-007**: defect rate grows linearly from baseline to ~5× baseline over the 18-month window using `escalation = 1 + (months_elapsed / 18) * 4`
- **Other underperformers**: defect rate is 1.5–3× their baseline, randomly varied per order
- **Healthy suppliers**: defect rate floats ±20% around baseline per order

**Derived fields** — `total_value`, `days_late`, and `on_time_flag` are computed inline during the loop so they're available immediately for aggregation steps.

---

### Step 3 — `build_supplier_scorecard()` and `build_monthly_trends()`

Two aggregation functions that produce pre-summarised tables from the raw orders.

`build_supplier_scorecard()` groups by `supplier_id` and computes total orders, on-time percentage, average days late, average defect rate, and total spend. It then left-joins the supplier master to attach name, category, country, and the underperformer flag.

`build_monthly_trends()` converts `po_date` to a year-month period string (`2023-07`), then groups by `po_month` + `category` to produce the 54-row trends table used for time-series charting.

---

### Step 4 — `run_quality_checks()`

Runs before any file is written. Asserts five hard constraints:

1. No null values in any column
2. `actual_delivery_date` is never before `po_date`
3. All `unit_cost` values are positive
4. All `quantity` values are positive
5. All `defect_rate` values are between 0 and 1

Also verifies the escalation pattern by splitting SUP-007's orders at the median date and confirming the second-half defect mean exceeds the first-half mean. The script halts with an error message if any assertion fails.

---

## Data Topology

The five output files form a simple star schema. `purchase_orders.csv` is the central fact table; all other files are either dimension tables or pre-aggregated views derived from it.

```
suppliers.csv  ──────────────────────────────┐
(50 rows | dimension)                        │
  supplier_id (PK)                           │ supplier_id (FK)
  supplier_name                              │
  category                          purchase_orders.csv
  country_of_origin          ───────(2,000 rows | fact table)
  base_on_time_rate                  po_id (PK)
  base_defect_rate                   supplier_id (FK)
  is_underperformer                  category
                                     country_of_origin
                                     po_date
                                     promised_delivery_date
                                     actual_delivery_date
                                     unit_cost
                                     quantity
                                     defect_rate

                                          │
                         ┌────────────────┴──────────────────┐
                         │                                   │
             supplier_scorecard.csv             monthly_trends.csv
             (49 rows | supplier rollup)        (54 rows | month × category)
               supplier_id                       po_month
               total_orders                      category
               on_time_pct                       order_count
               avg_days_late                     on_time_pct
               avg_defect_rate                   avg_days_late
               total_spend                       avg_defect_rate
               avg_unit_cost                     total_spend
               + supplier dimension fields
```

`purchase_orders_enriched.csv` is a convenience copy of the fact table with `total_value`, `days_late`, and `on_time_flag` included — intended for direct import into Power BI without requiring calculated columns.

---

## Intentional Analytical Signals

| Signal | Where to find it | How it was introduced |
|--------|-----------------|----------------------|
| 12 chronic late-delivery suppliers | `suppliers.csv` → `is_underperformer = True` | Baseline on-time rate set to 55–74% |
| Q4 seasonal delay spike | `monthly_trends.csv` → Oct–Dec `avg_days_late` | Seasonal multiplier 1.3–1.5× applied to late probability |
| SUP-007 defect escalation | `purchase_orders.csv` filtered to `supplier_id = SUP-007` | Linear escalation formula over `months_elapsed` |
| Spend concentration (Pareto) | `supplier_scorecard.csv` → `total_spend` distribution | Dirichlet distribution (`alpha=0.8`) for order allocation |

---

## Reproducibility

All randomness is seeded at the top of the script:

```python
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
```

Running `python generate_data.py` on any machine with the same dependency versions will produce byte-identical CSV files.

**Dependencies:** `pandas >= 2.0.0`, `numpy >= 1.24.0`
