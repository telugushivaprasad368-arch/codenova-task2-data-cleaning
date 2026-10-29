"""CodeNova Task 2 - reproducible retail sales data-quality pipeline.

Creates an intentionally imperfect *synthetic* raw dataset, audits it, applies
documented cleaning rules, and writes clean data plus before/after evidence.
The raw file is never modified after it is created.
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "synthetic_dirty_sales.csv"
CLEAN = ROOT / "data" / "clean" / "clean_sales.csv"
OUTPUTS = ROOT / "outputs"
AUDIT = OUTPUTS / "data_quality_audit.md"
SUMMARY = OUTPUTS / "before_after_summary.json"
REPORT = ROOT / "quality_report.html"
FIELDS = ["order_id", "order_date", "region", "category", "units_sold", "unit_price", "gross_revenue"]
VALID_REGIONS = {"North", "South", "East", "West"}
VALID_CATEGORIES = {"Electronics", "Furniture", "Office Supplies", "Home & Kitchen"}


def safe_float(value: str) -> float | None:
    try:
        result = float(value)
        return result if result == result else None  # reject NaN
    except (TypeError, ValueError):
        return None


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def make_raw_data() -> None:
    """Create deterministic input once; do not overwrite source data on later runs."""
    if RAW.exists():
        return
    random.seed(20261011)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    categories = [("Electronics", (60, 220)), ("Furniture", (110, 320)),
                  ("Office Supplies", (8, 42)), ("Home & Kitchen", (40, 150))]
    regions = ["North", "South", "East", "West"]
    rows: list[dict[str, str]] = []
    start = date(2026, 1, 1)
    for i in range(560):
        category, price_range = random.choice(categories)
        units = random.randint(1, 6)
        price = round(random.uniform(*price_range), 2)
        row = {
            "order_id": f"ORD-{10001 + i}",
            "order_date": (start + timedelta(days=random.randint(0, 272))).isoformat(),
            "region": random.choice(regions),
            "category": category,
            "units_sold": str(units),
            "unit_price": f"{price:.2f}",
            "gross_revenue": f"{units * price:.2f}",
        }
        rows.append(row)

    # Purposeful quality issues for the audit exercise.
    rows[5]["region"] = "north "             # normalizable categorical inconsistency
    rows[17]["category"] = "office supplies" # normalizable categorical inconsistency
    rows[31]["units_sold"] = ""               # imputed from category median
    rows[44]["unit_price"] = ""               # imputed from category median
    rows[58]["order_date"] = "2026/03/15"     # standardized date format
    rows[73]["region"] = "Central"            # invalid category: remove
    rows[89]["units_sold"] = "many"           # invalid numeric type: remove
    rows[112]["unit_price"] = "-45.00"        # invalid numeric value: remove
    rows[143]["gross_revenue"] = "999999.00"  # IQR outlier: remove
    rows[201]["gross_revenue"] = "0.00"       # invalid financial value: remove
    rows[311]["order_id"] = ""                 # missing identifier: remove
    rows.append(rows[20].copy())                # exact duplicate
    rows.append(rows[143].copy())               # duplicate of outlier, caught as duplicate

    with RAW.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def null_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    return {field: sum(not (row.get(field) or "").strip() for row in rows) for field in FIELDS}


def invalid_type_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    invalid_date = sum(parse_date(row["order_date"].replace("/", "-")) is None for row in rows if row["order_date"])
    invalid_units = sum((safe_float(row["units_sold"]) is None or safe_float(row["units_sold"]) <= 0) for row in rows if row["units_sold"])
    invalid_price = sum((safe_float(row["unit_price"]) is None or safe_float(row["unit_price"]) <= 0) for row in rows if row["unit_price"])
    invalid_revenue = sum((safe_float(row["gross_revenue"]) is None or safe_float(row["gross_revenue"]) <= 0) for row in rows if row["gross_revenue"])
    return {"order_date": invalid_date, "units_sold": invalid_units, "unit_price": invalid_price, "gross_revenue": invalid_revenue}


def profile(rows: list[dict[str, str]]) -> dict:
    duplicates = len(rows) - len({tuple(row.get(field, "") for field in FIELDS) for row in rows})
    revenues = [safe_float(r["gross_revenue"]) for r in rows]
    revenues = [x for x in revenues if x is not None]
    return {
        "row_count": len(rows),
        "null_counts": null_counts(rows),
        "exact_duplicates": duplicates,
        "invalid_types_or_values": invalid_type_counts(rows),
        "gross_revenue": {
            "count": len(revenues),
            "min": round(min(revenues), 2) if revenues else None,
            "median": round(median(revenues), 2) if revenues else None,
            "max": round(max(revenues), 2) if revenues else None,
            "total": round(sum(revenues), 2),
        },
    }


def quartiles(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    lower = ordered[:midpoint]
    upper = ordered[midpoint + (len(ordered) % 2):]
    return median(lower), median(upper)


def clean_rows(raw_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], Counter, dict]:
    """Apply each cleaning rule in a deliberate, reproducible order."""
    actions: Counter = Counter()
    unique_rows: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in raw_rows:
        key = tuple(row.get(field, "") for field in FIELDS)
        if key in seen:
            actions["exact_duplicates_removed"] += 1
            continue
        seen.add(key)
        unique_rows.append(row.copy())

    # Normalize values before applying validation rules.
    for row in unique_rows:
        row["region"] = row["region"].strip().title()
        row["category"] = row["category"].strip().title()
        row["order_date"] = row["order_date"].replace("/", "-")
    normalized_count = sum(1 for raw, clean in zip(raw_rows, unique_rows)
                           if raw["region"] != clean["region"] or raw["category"] != clean["category"] or raw["order_date"] != clean["order_date"])
    actions["standardized_text_or_dates"] = normalized_count

    valid: list[dict[str, str]] = []
    for row in unique_rows:
        if not row["order_id"].strip() or row["region"] not in VALID_REGIONS or row["category"] not in VALID_CATEGORIES or parse_date(row["order_date"]) is None:
            actions["invalid_identifier_category_or_date_removed"] += 1
            continue
        units = safe_float(row["units_sold"])
        price = safe_float(row["unit_price"])
        revenue = safe_float(row["gross_revenue"])
        if (units is not None and units <= 0) or (price is not None and price <= 0) or (revenue is not None and revenue <= 0):
            actions["invalid_numeric_value_removed"] += 1
            continue
        if units is not None and units != int(units):
            actions["non_integer_units_removed"] += 1
            continue
        if row["units_sold"] and units is None or row["unit_price"] and price is None or row["gross_revenue"] and revenue is None:
            actions["invalid_numeric_type_removed"] += 1
            continue
        valid.append(row)

    # Median imputation is done only for isolated, numeric missing values, grouped by category.
    unit_medians = {category: median([safe_float(r["units_sold"]) for r in valid if r["category"] == category and safe_float(r["units_sold"]) is not None]) for category in VALID_CATEGORIES}
    price_medians = {category: median([safe_float(r["unit_price"]) for r in valid if r["category"] == category and safe_float(r["unit_price"]) is not None]) for category in VALID_CATEGORIES}
    completed: list[dict[str, str]] = []
    for row in valid:
        if not row["units_sold"]:
            row["units_sold"] = str(int(round(unit_medians[row["category"]])))
            actions["units_imputed_category_median"] += 1
        if not row["unit_price"]:
            row["unit_price"] = f"{price_medians[row['category']]:.2f}"
            actions["price_imputed_category_median"] += 1
        if not row["gross_revenue"]:
            row["gross_revenue"] = f"{int(row['units_sold']) * float(row['unit_price']):.2f}"
            actions["revenue_recalculated"] += 1
        # Revenue is recalculated to preserve the commercial identity of every order.
        row["gross_revenue"] = f"{int(row['units_sold']) * float(row['unit_price']):.2f}"
        completed.append(row)

    revenue_values = [float(row["gross_revenue"]) for row in completed]
    q1, q3 = quartiles(revenue_values)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    clean = []
    for row in completed:
        if not lower <= float(row["gross_revenue"]) <= upper:
            actions["iqr_revenue_outliers_removed"] += 1
            continue
        clean.append(row)
    return clean, actions, {"q1": round(q1, 2), "q3": round(q3, 2), "iqr": round(iqr, 2), "lower_bound": round(lower, 2), "upper_bound": round(upper, 2)}


def write_audit(before: dict, after: dict, actions: Counter, bounds: dict) -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    body = f"""# Data Quality Audit Report - CodeNova Task 2

## Scope and reproducibility

This audit evaluates a deliberately imperfect **synthetic retail sales** dataset. The source file at `data/raw/synthetic_dirty_sales.csv` is retained unchanged. Run `python data_cleaning.py` to reproduce every transformation and report.

## Diagnostic findings

| Metric | Before cleaning | After cleaning |
| --- | ---: | ---: |
| Rows | {before['row_count']} | {after['row_count']} |
| Exact duplicate rows | {before['exact_duplicates']} | {after['exact_duplicates']} |
| Missing values | {sum(before['null_counts'].values())} | {sum(after['null_counts'].values())} |
| Invalid typed/value fields | {sum(before['invalid_types_or_values'].values())} | {sum(after['invalid_types_or_values'].values())} |
| Revenue median | ${before['gross_revenue']['median']:,.2f} | ${after['gross_revenue']['median']:,.2f} |
| Revenue maximum | ${before['gross_revenue']['max']:,.2f} | ${after['gross_revenue']['max']:,.2f} |

## Cleaning log and rationale

| Action | Records affected | Rationale |
| --- | ---: | --- |
| Exact duplicates removed | {actions['exact_duplicates_removed']} | Prevents double-counting the same transaction. |
| Text/date values standardized | {actions['standardized_text_or_dates']} | Makes category and date grouping consistent. |
| Invalid ID/category/date rows removed | {actions['invalid_identifier_category_or_date_removed']} | These rows cannot be reliably assigned to a valid business dimension. |
| Invalid numeric values removed | {actions['invalid_numeric_value_removed']} | Negative or zero commercial values are outside this dataset's valid domain. |
| Invalid numeric types removed | {actions['invalid_numeric_type_removed']} | Text in numerical fields cannot be inferred with confidence. |
| Units imputed with category median | {actions['units_imputed_category_median']} | Preserves an otherwise valid transaction using a robust category-specific estimate. |
| Unit prices imputed with category median | {actions['price_imputed_category_median']} | Uses a robust, product-family-aligned estimate rather than a global average. |
| IQR revenue outliers removed | {actions['iqr_revenue_outliers_removed']} | Removes values outside ${bounds['lower_bound']:,.2f} to ${bounds['upper_bound']:,.2f}; the high value is not credible relative to the synthetic order range. |

## Outcome

The clean dataset contains no null fields, exact duplicates, invalid numeric values, or IQR revenue outliers. It is saved separately at `data/clean/clean_sales.csv`; the raw data remains intact for traceability.

## Limitations

This is a synthetic demonstration. In production, questionable rows should be checked against source systems before deletion, and business owners should approve outlier thresholds.
"""
    AUDIT.write_text(body, encoding="utf-8")


def write_html(before: dict, after: dict, actions: Counter) -> None:
    removed = before["row_count"] - after["row_count"]
    html = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Data Quality Audit | CodeNova Task 2</title><style>
body{{margin:0;background:#f5f7fb;color:#16263d;font:16px Inter,Segoe UI,Arial,sans-serif}}main{{max-width:1040px;margin:auto;padding:42px 22px}}header{{padding:40px;border-radius:24px;background:linear-gradient(125deg,#102a43,#0f766e);color:white}}h1{{margin:8px 0;font-size:40px}}.eyebrow{{font-size:13px;letter-spacing:.12em;font-weight:700;color:#a7f3d0}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}}.card,section{{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 18px #1018280d}}.card span{{color:#667085;font-size:12px;font-weight:700;text-transform:uppercase}}.card strong{{display:block;font-size:28px;margin-top:12px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:13px;border-bottom:1px solid #e4e7ec;text-align:left}}th{{color:#475467}}.ok{{color:#047857;font-weight:700}}@media(max-width:720px){{.grid{{grid-template-columns:1fr 1fr}}h1{{font-size:31px}}}}</style></head><body><main>
<header><div class='eyebrow'>CODENOVA • DATA SCIENCE • TASK 2</div><h1>Data Quality Audit</h1><p>Transparent, reproducible cleaning from raw transaction records to analysis-ready data.</p></header>
<div class='grid'><div class='card'><span>Raw rows</span><strong>{before['row_count']}</strong></div><div class='card'><span>Clean rows</span><strong>{after['row_count']}</strong></div><div class='card'><span>Rows removed</span><strong>{removed}</strong></div><div class='card'><span>Null fields after</span><strong class='ok'>0</strong></div></div>
<section><h2>Before vs. after</h2><table><tr><th>Metric</th><th>Before</th><th>After</th></tr><tr><td>Exact duplicates</td><td>{before['exact_duplicates']}</td><td class='ok'>{after['exact_duplicates']}</td></tr><tr><td>Missing values</td><td>{sum(before['null_counts'].values())}</td><td class='ok'>{sum(after['null_counts'].values())}</td></tr><tr><td>Invalid fields</td><td>{sum(before['invalid_types_or_values'].values())}</td><td class='ok'>{sum(after['invalid_types_or_values'].values())}</td></tr><tr><td>Revenue maximum</td><td>${before['gross_revenue']['max']:,.2f}</td><td>${after['gross_revenue']['max']:,.2f}</td></tr></table></section>
<section><h2>Cleaning decisions</h2><table><tr><th>Action</th><th>Records affected</th></tr>{''.join(f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' for key,value in actions.items())}</table><p><strong>Traceability:</strong> the raw source is retained unchanged; the detailed rationale is in <code>outputs/data_quality_audit.md</code>.</p></section>
</main></body></html>"""
    REPORT.write_text(html, encoding="utf-8")


def main() -> None:
    make_raw_data()
    raw_rows = read_rows(RAW)
    before = profile(raw_rows)
    clean_rows_list, actions, bounds = clean_rows(raw_rows)
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    with CLEAN.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(clean_rows_list)
    after = profile(clean_rows_list)
    package = {"before": before, "after": after, "actions": dict(actions), "iqr_bounds": bounds}
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(package, indent=2), encoding="utf-8")
    write_audit(before, after, actions, bounds)
    write_html(before, after, actions)
    print(f"Cleaned {before['row_count']} raw rows into {after['row_count']} analysis-ready rows.")


if __name__ == "__main__":
    main()

