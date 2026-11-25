# Data Profiling Reports, with Drift Between Snapshots

A small profiler that answers *"what's actually in this file?"* in under a second. It writes a **JSON profile** (diffable, storable) and a **single-file HTML report**, and compares two profiles of the same table to catch what changed between deliveries.

## What it profiles

**Per column:**
- **inferred type**: what the values *are*, not the pandas dtype. For example *number stored as text*, *date stored as text*, or *identifier* (digits with leading zeros, like ZIP codes)
- null share, distinct count, top values
- numeric stats with a histogram, and extreme outliers (3 × IQR)
- **formats** found in the text: email, US phone, ZIP, ISO date, US date
- **personal-data hints**, when most values look like emails or phone numbers

**Per table:** row count, duplicate rows, **candidate keys** (columns that are fully unique and never null), and a "needs a look" list.

## Output on a messy customer extract (20,000 rows, 0.4 s)

```
! email: looks like personal data (email)
! phone: looks like personal data (us_phone)
! signup_date: mixed date formats (ISO 98.7%, US 1.3%)
! monthly_bill: 40 non-numeric values (e.g. 'N/A')
! monthly_bill: 29 extreme outliers (range 2.67 to 336.72)
! age: 7 extreme outliers (range 0 to 999)
! notes: 90% null
```

## Drift between two deliveries

```
$ python -m profiler customers_week2.csv --compare reports/customers_week1.json
changes since reports/customers_week1.json:
  ~ email: nulls 0.0% -> 20.2%
  ~ monthly_bill: mean 72.05 -> 80.42 (+12%)
  ~ plan: new frequent values ['Unlimited Plus']
```

All three planted changes are reported. Two samples drawn from the same source with a different random seed produce **no** changes, so the comparison isn't noisy.

## Fixes made along the way (see the commit history)

- **ZIP codes were first labeled "number stored as text"**, which is advice that would strip their leading zeros if followed. Digit strings with leading zeros are now recognized as identifiers.
- **CSV input flagged every numeric column** as "stored as text", because in a CSV everything is text. That warning now only applies to typed sources like Parquet.

## What profiling can't catch

15 impossible ages were planted (0, 150 and 999). The outlier rule flags the 999s, but **0 and 150 sit inside the statistically normal range** (3 × IQR around ages 18–85) and pass. Profiling tells you what the data looks like; **domain rules** ("age between 18 and 120") have to say what it *should* look like. That's the job of the expectation suite in the great-expectations-validation project.

## How to run

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m profiler data.csv --out reports
PYTHONPATH=src python -m profiler data_next_week.csv --out reports --compare reports/data.json
pytest
```

## Next steps
- Profile large Parquet datasets with DuckDB instead of pandas
- Store profiles over time and chart each column's null share and mean
