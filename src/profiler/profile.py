"""Profile a DataFrame into a plain, JSON-serialisable dict.

Per column:  inferred type (what the values ARE, not the pandas dtype), nulls, distinct,
             top values, numeric stats + IQR outliers, string formats, PII hints.
Per table:   rows, duplicate rows, candidate keys, and warnings worth a human look.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

FORMATS = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$"),
    "us_phone": re.compile(r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"),
    "zip5": re.compile(r"^\d{5}$"),
    "iso_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "us_date": re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    "integer": re.compile(r"^-?\d+$"),
    "decimal": re.compile(r"^-?\d+\.\d+$"),
}
PII = {"email", "us_phone"}


def _formats(s: pd.Series) -> dict[str, float]:
    sample = s.dropna().astype(str).head(5000)
    if sample.empty:
        return {}
    out = {}
    for name, rx in FORMATS.items():
        share = sample.str.match(rx).mean()
        if share > 0.005:
            out[name] = round(float(share), 4)
    return out


def _infer(s: pd.Series, formats: dict) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_numeric_dtype(s):
        return "integer" if (s.dropna() % 1 == 0).all() else "number"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    numeric = pd.to_numeric(s, errors="coerce")
    if s.notna().sum() and numeric.notna().sum() / s.notna().sum() > 0.95:
        text = s.dropna().astype(str)
        # digits with leading zeros (zip codes, account numbers) are identifiers, not numbers:
        # converting them would turn "02139" into 2139
        if text.str.match(r"^0\d").mean() > 0.01 or formats.get("zip5", 0) > 0.95:
            return "identifier (digits as text)"
        return "number (stored as text)"
    if formats.get("iso_date", 0) + formats.get("us_date", 0) > 0.95:
        return "date (stored as text)"
    return "string"


def profile_column(s: pd.Series) -> dict:
    n = len(s)
    nn = s.notna()
    fmts = _formats(s) if not pd.api.types.is_numeric_dtype(s) else {}
    col = {
        "pandas_dtype": str(s.dtype),
        "inferred_type": _infer(s, fmts),
        "null_share": round(float(1 - nn.mean()), 4),
        "distinct": int(s.nunique(dropna=True)),
        "distinct_share": round(float(s.nunique(dropna=True) / max(nn.sum(), 1)), 4),
        "top_values": {str(k): int(v) for k, v in s.value_counts().head(5).items()},
        "formats": fmts,
        "pii_hint": sorted(k for k in fmts if k in PII and fmts[k] > 0.5),
    }
    num = s if pd.api.types.is_numeric_dtype(s) else pd.to_numeric(s, errors="coerce")
    if num.notna().sum() > 0 and col["inferred_type"] in ("integer", "number", "number (stored as text)"):
        q1, q3 = num.quantile([0.25, 0.75])
        iqr = q3 - q1
        outliers = ((num < q1 - 3 * iqr) | (num > q3 + 3 * iqr)).sum()
        col["numeric"] = {
            "min": float(num.min()), "p25": float(q1), "median": float(num.median()), "p75": float(q3),
            "max": float(num.max()), "mean": round(float(num.mean()), 4), "std": round(float(num.std()), 4),
            "extreme_outliers": int(outliers),
            "non_numeric_values": int((s.notna() & num.isna()).sum()),
            "histogram": [int(c) for c in np.histogram(num.dropna(), bins=20)[0]],
        }
    return col


def warnings_for(name: str, c: dict, rows: int) -> list[str]:
    w = []
    if c["null_share"] > 0.5:
        w.append(f"{name}: {c['null_share']:.0%} null")
    if c["inferred_type"].endswith("(stored as text)"):
        w.append(f"{name}: {c['inferred_type']}")
    nm = c.get("numeric", {})
    if nm.get("non_numeric_values"):
        bad = [v for v in c["top_values"] if pd.isna(pd.to_numeric(v, errors="coerce"))]
        w.append(f"{name}: {nm['non_numeric_values']} non-numeric values" + (f" (e.g. {bad[0]!r})" if bad else ""))
    if nm.get("extreme_outliers"):
        w.append(f"{name}: {nm['extreme_outliers']} extreme outliers (range {nm['min']:g} to {nm['max']:g})")
    f = c["formats"]
    if f.get("iso_date") and f.get("us_date"):
        w.append(f"{name}: mixed date formats (ISO {f['iso_date']:.1%}, US {f['us_date']:.1%})")
    if c["pii_hint"]:
        w.append(f"{name}: looks like personal data ({', '.join(c['pii_hint'])})")
    if c["distinct"] == 1:
        w.append(f"{name}: constant column")
    return w


def profile(df: pd.DataFrame, name: str = "dataset") -> dict:
    cols = {c: profile_column(df[c]) for c in df.columns}
    keys = [c for c, p in cols.items() if p["null_share"] == 0 and p["distinct"] == len(df)]
    warns = [w for c, p in cols.items() for w in warnings_for(c, p, len(df))]
    dups = int(df.astype(str).duplicated().sum())
    if dups:
        warns.insert(0, f"{dups} fully duplicated rows")
    return {
        "name": name, "profiled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": len(df), "columns": len(df.columns), "duplicate_rows": dups,
        "candidate_keys": keys, "warnings": warns, "column_profiles": cols,
    }
