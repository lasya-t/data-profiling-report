"""Compare two profiles of the same table (e.g. last week vs this week) and report what moved."""
from __future__ import annotations


def compare(old: dict, new: dict, null_jump: float = 0.05, mean_shift: float = 0.10) -> list[str]:
    out = []
    oc, nc = old["column_profiles"], new["column_profiles"]
    for c in sorted(set(oc) - set(nc)):
        out.append(f"column removed: {c}")
    for c in sorted(set(nc) - set(oc)):
        out.append(f"column added: {c}")
    if abs(new["rows"] - old["rows"]) / max(old["rows"], 1) > 0.2:
        out.append(f"row count {old['rows']:,} -> {new['rows']:,}")
    for c in sorted(set(oc) & set(nc)):
        a, b = oc[c], nc[c]
        if a["inferred_type"] != b["inferred_type"]:
            out.append(f"{c}: type {a['inferred_type']} -> {b['inferred_type']}")
        if b["null_share"] - a["null_share"] > null_jump:
            out.append(f"{c}: nulls {a['null_share']:.1%} -> {b['null_share']:.1%}")
        new_vals = set(b["top_values"]) - set(a["top_values"])
        if a["distinct"] <= 20 and new_vals:
            out.append(f"{c}: new frequent values {sorted(new_vals)}")
        am, bm = a.get("numeric", {}).get("mean"), b.get("numeric", {}).get("mean")
        if am and bm and abs(bm - am) / abs(am) > mean_shift:
            out.append(f"{c}: mean {am:.2f} -> {bm:.2f} ({(bm - am) / am:+.0%})")
    return out
