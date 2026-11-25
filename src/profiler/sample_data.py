"""A messy customer extract to profile, with problems planted on purpose."""
import numpy as np
import pandas as pd


def customers(n=20_000, seed=0, drifted=False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "email": [f"user{i}@{rng.choice(['gmail.com', 'yahoo.com', 'comcast.net'])}" for i in range(n)],
        "phone": [f"({rng.integers(200, 999)}) {rng.integers(200, 999)}-{rng.integers(1000, 9999)}" for _ in range(n)],
        "zip": [f"{z:05d}" for z in rng.integers(1000, 99999, n)],
        "signup_date": (pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 1800, n), unit="D")).strftime("%Y-%m-%d"),
        "plan": rng.choice(["Basic", "Unlimited", "Premium"], n, p=[0.4, 0.45, 0.15]),
        "monthly_bill": rng.gamma(4, 18, n).round(2).astype(object),
        "age": rng.integers(18, 85, n).astype(float),
        "lines": rng.choice([1, 2, 3, 4, 5], n, p=[0.45, 0.25, 0.15, 0.1, 0.05]),
        "notes": np.where(rng.random(n) < 0.9, None, "called about bill"),
    })
    # planted problems
    df.loc[rng.choice(n, 40, replace=False), "monthly_bill"] = "N/A"                 # text in a numeric column
    df.loc[rng.choice(n, 15, replace=False), "age"] = rng.choice([0, 150, 999], 15)    # impossible ages
    df.loc[rng.choice(n, 300, replace=False), "signup_date"] = "01/15/2023"          # second date format
    df.loc[rng.random(n) < 0.03, "age"] = np.nan
    if drifted:
        df["plan"] = rng.choice(["Basic", "Unlimited", "Premium", "Unlimited Plus"], n, p=[0.3, 0.35, 0.15, 0.2])
        df["monthly_bill"] = pd.to_numeric(df["monthly_bill"], errors="coerce") * 1.12
        df.loc[rng.random(n) < 0.20, "email"] = None
    return df
