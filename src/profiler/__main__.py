import argparse
import json
from pathlib import Path

import pandas as pd

from .drift import compare
from .profile import profile
from .report import to_html


def main() -> None:
    p = argparse.ArgumentParser(description="Profile a CSV or Parquet file")
    p.add_argument("path")
    p.add_argument("--out", default="reports")
    p.add_argument("--compare", help="earlier profile JSON to diff against")
    a = p.parse_args()
    df = pd.read_parquet(a.path) if a.path.endswith(".parquet") else pd.read_csv(a.path, dtype=str, keep_default_na=False, na_values=[""])
    prof = profile(df, Path(a.path).name, text_source=not a.path.endswith(".parquet"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.path).stem
    (out / f"{stem}.json").write_text(json.dumps(prof, indent=2))
    (out / f"{stem}.html").write_text(to_html(prof))
    print(f"{prof['rows']:,} rows, {prof['columns']} columns -> {out / stem}.html / .json")
    for w in prof["warnings"]:
        print(f"  ! {w}")
    if a.compare:
        changes = compare(json.loads(Path(a.compare).read_text()), prof)
        print(f"\nchanges since {a.compare}:" if changes else "\nno drift since " + a.compare)
        for c in changes:
            print(f"  ~ {c}")


if __name__ == "__main__":
    main()
