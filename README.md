# Supply Chain Analytics

End-to-end supply chain performance analysis — synthetic dataset generation, SQL KPI queries, Power BI dashboarding, and late-delivery risk modelling. Built as a portfolio project demonstrating business analytics skills relevant to ERP implementation and procurement consulting.

---

## Project Roadmap

| Part | Focus | Status |
|------|-------|--------|
| **1 — Data Generation** | Python · synthetic dataset · data quality | ✅ Complete |
| **2 — SQL Analysis** | KPI queries · supplier ranking · trend detection | 🔲 Upcoming |
| **3 — Power BI Dashboard** | Scorecards · delivery trends · defect escalation | 🔲 Upcoming |
| **4 — Predictive Model** | Late delivery risk scoring · logistic regression | 🔲 Upcoming |
| **5 — Executive Summary** | Findings deck · procurement recommendations | 🔲 Upcoming |

---

## Part 1 — Data Generation

### What was built

A fully reproducible synthetic procurement dataset covering **50 suppliers**, **2,000 purchase orders**, and **18 months of history** (January 2023 – June 2024), generated entirely with Python.

The dataset is not randomly clean. Four realistic problems are embedded in the data by design:

- **12 chronically underperforming suppliers** with on-time delivery rates of 55–74% against a healthy-supplier baseline of 88–98%
- **Seasonal delivery degradation** — Q4 (Oct–Dec) applies a 1.3–1.5× delay multiplier to simulate peak-season logistics pressure
- **SUP-007 defect escalation** — one supplier's defect rate grows linearly from baseline to ~5× baseline across the 18-month window
- **Pareto-distributed order volume** — spend is concentrated unevenly across suppliers using a Dirichlet distribution, reflecting realistic procurement patterns

### Repository structure

```
supply-chain-analytics/
│
├── data/
│   ├── purchase_orders.csv             # Core fact table — 2,000 rows
│   ├── purchase_orders_enriched.csv    # Fact table + total_value, days_late, on_time_flag
│   ├── suppliers.csv                   # Supplier master — 50 rows
│   ├── supplier_scorecard.csv          # KPIs rolled up per supplier
│   └── monthly_trends.csv             # Metrics by month × category — 54 rows
│
├── generate_data.py                    # Data generation script
├── requirements.txt
├── TECHNICAL.md                        # Code walkthrough and data topology
└── README.md
```

### Quickstart

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/supply-chain-analytics.git
cd supply-chain-analytics

# Install dependencies
pip install -r requirements.txt

# Generate all five CSV files
python generate_data.py
```

The script prints a quality report on every run and halts with a descriptive error if any assertion fails. Output lands in `/data`.

### Data dictionary

**`purchase_orders.csv`** — one row per purchase order, the central fact table

| Field | Type | Description |
|-------|------|-------------|
| `po_id` | string | Unique PO identifier — `PO-00001` through `PO-02000` |
| `supplier_id` | string | Foreign key → `suppliers.csv` |
| `category` | string | Raw Materials · Electronics · Packaging |
| `country_of_origin` | string | Supplier country |
| `po_date` | date | Date the order was placed |
| `promised_delivery_date` | date | Contractually agreed delivery date |
| `actual_delivery_date` | date | Date goods were received |
| `unit_cost` | float | Cost per unit (USD) |
| `quantity` | int | Units ordered |
| `defect_rate` | float | Fraction of received units with quality defects (0–1) |

`purchase_orders_enriched.csv` adds three derived columns: `total_value` (unit_cost × quantity), `days_late` (actual minus promised, negative = early), and `on_time_flag` (1 = on time or early).

---

**`suppliers.csv`** — one row per supplier, the dimension table

| Field | Type | Description |
|-------|------|-------------|
| `supplier_id` | string | Primary key — `SUP-001` through `SUP-050` |
| `supplier_name` | string | Display name |
| `category` | string | Primary procurement category |
| `country_of_origin` | string | Country of manufacture |
| `base_on_time_rate` | float | Simulated baseline on-time delivery rate |
| `base_defect_rate` | float | Simulated baseline defect rate |
| `is_underperformer` | bool | `True` for the 12 flagged underperforming suppliers |

---

**`supplier_scorecard.csv`** — aggregated KPIs per supplier, pre-joined to supplier attributes

| Field | Description |
|-------|-------------|
| `total_orders` | Count of POs placed with this supplier |
| `on_time_pct` | Proportion of orders delivered on time |
| `avg_days_late` | Mean days past promised delivery date |
| `avg_defect_rate` | Mean defect rate across all orders |
| `total_spend` | Sum of total_value across all orders (USD) |

---

**`monthly_trends.csv`** — 18 months × 3 categories = 54 rows, used for time-series visualisation

| Field | Description |
|-------|-------------|
| `po_month` | Year-month string — e.g. `2023-07` |
| `category` | Procurement category |
| `order_count` | POs placed that month in that category |
| `on_time_pct` | On-time delivery rate |
| `avg_days_late` | Average days late |
| `avg_defect_rate` | Average defect rate |
| `total_spend` | Total order value (USD) |

### Skills demonstrated

`pandas` · `numpy` · `datetime` · data quality validation · seeded reproducibility · star schema design · Dirichlet sampling · assertion-based testing

---

## About

Built by Hayden — MSITM candidate (Business Analytics), Bryan School of Business, UNC Greensboro. Targeting ERP implementation consulting with a focus on supply chain and procurement analytics.

---

*All data is fully synthetic. No real suppliers, transactions, or organisations are represented.*
