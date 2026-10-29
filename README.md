# Data Cleaning Report

### CodeNova Data Science Internship - Task 2

**A reproducible data-quality workflow that diagnoses, cleans, and documents retail-sales data without modifying the original raw source.**

## What this project delivers

- A preserved raw dataset containing realistic quality issues for demonstration.
- Automated checks for missing values, exact duplicates, invalid data types, invalid values, and IQR outliers.
- Category-specific median imputation for isolated missing numerical values.
- A dedicated clean-data output, before/after JSON summary, detailed Markdown audit report, and browser-ready quality report.

> **Data note:** The assignment did not include a dataset. This project uses a deterministic synthetic dataset with intentional issues solely to demonstrate the required cleaning workflow.

## Run it

No external packages are required.

```powershell
python data_cleaning.py
```

The first run creates `data/raw/synthetic_dirty_sales.csv`. Later runs preserve that raw file and regenerate only derived outputs.

## Outputs

| File | Purpose |
| --- | --- |
| `data/raw/synthetic_dirty_sales.csv` | Untouched source dataset |
| `data/clean/clean_sales.csv` | Standardized, validated clean dataset |
| `outputs/before_after_summary.json` | Reproducible quality metrics and cleaning counts |
| `outputs/data_quality_audit.md` | Transformation rationale and audit findings |
| `quality_report.html` | Executive-friendly before/after report |

## Cleaning principles

1. **Preserve raw data.** The raw CSV is never rewritten.
2. **Remove only irrecoverable records.** Invalid identifiers, dimensions, and non-interpretable numerical text are removed.
3. **Impute selectively.** Isolated missing numeric values receive category-median estimates, which are less distorted by skew than means.
4. **Detect outliers transparently.** Revenue outliers are evaluated by the IQR method, with bounds included in the summary and report.
5. **Keep every decision auditable.** The cleaning script, row counts, and affected-record totals are all available in the repository.

## Limitations

The dataset is synthetic. In a real organisation, questionable transactions should be reconciled against source systems before removal, and data owners should approve business rules and outlier thresholds.

