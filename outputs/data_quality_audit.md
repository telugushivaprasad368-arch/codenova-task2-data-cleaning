# Data Quality Audit Report - CodeNova Task 2

## Scope and reproducibility

This audit evaluates a deliberately imperfect **synthetic retail sales** dataset. The source file at `data/raw/synthetic_dirty_sales.csv` is retained unchanged. Run `python data_cleaning.py` to reproduce every transformation and report.

## Diagnostic findings

| Metric | Before cleaning | After cleaning |
| --- | ---: | ---: |
| Rows | 562 | 541 |
| Exact duplicate rows | 2 | 0 |
| Missing values | 3 | 0 |
| Invalid typed/value fields | 3 | 0 |
| Revenue median | $326.94 | $309.82 |
| Revenue maximum | $999,999.00 | $1,422.12 |

## Cleaning log and rationale

| Action | Records affected | Rationale |
| --- | ---: | --- |
| Exact duplicates removed | 2 | Prevents double-counting the same transaction. |
| Text/date values standardized | 3 | Makes category and date grouping consistent. |
| Invalid ID/category/date rows removed | 2 | These rows cannot be reliably assigned to a valid business dimension. |
| Invalid numeric values removed | 2 | Negative or zero commercial values are outside this dataset's valid domain. |
| Invalid numeric types removed | 1 | Text in numerical fields cannot be inferred with confidence. |
| Units imputed with category median | 1 | Preserves an otherwise valid transaction using a robust category-specific estimate. |
| Unit prices imputed with category median | 1 | Uses a robust, product-family-aligned estimate rather than a global average. |
| IQR revenue outliers removed | 14 | Removes values outside $-649.22 to $1,443.90; the high value is not credible relative to the synthetic order range. |

## Outcome

The clean dataset contains no null fields, exact duplicates, invalid numeric values, or IQR revenue outliers. It is saved separately at `data/clean/clean_sales.csv`; the raw data remains intact for traceability.

## Limitations

This is a synthetic demonstration. In production, questionable rows should be checked against source systems before deletion, and business owners should approve outlier thresholds.

