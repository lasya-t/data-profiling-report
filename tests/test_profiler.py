import json

import numpy as np
import pandas as pd

from profiler.drift import compare
from profiler.profile import profile
from profiler.report import to_html
from profiler.sample_data import customers


def warns(p, text):
    return [w for w in p["warnings"] if text in w]


def test_planted_problems_are_found():
    p = profile(customers(5000))
    assert warns(p, "non-numeric values") and warns(p, "mixed date formats")
    assert warns(p, "personal data (email)") and warns(p, "personal data (us_phone)")
    assert "customer_id" in p["candidate_keys"]


def test_zip_codes_are_identifiers_not_numbers():
    p = profile(pd.DataFrame({"zip": ["02139", "10001", "07302", "94105"]}))
    assert p["column_profiles"]["zip"]["inferred_type"] == "identifier (digits as text)"


def test_numbers_in_text_are_flagged_only_for_typed_sources():
    df = pd.DataFrame({"x": ["1.5", "2.0", "3.25"]})
    assert warns(profile(df), "stored as text")
    assert not warns(profile(df, text_source=True), "stored as text")


def test_profile_is_json_serialisable_and_renders():
    p = profile(customers(2000))
    json.dumps(p)
    page = to_html(p)
    assert page.startswith("<!DOCTYPE html>") and "<svg" in page


def test_drift_detects_planted_changes_and_nothing_else():
    a = profile(customers(8000, seed=0))
    assert compare(a, profile(customers(8000, seed=1))) == []
    changes = " | ".join(compare(a, profile(customers(8000, seed=1, drifted=True))))
    assert "email: nulls" in changes and "Unlimited Plus" in changes and "monthly_bill: mean" in changes


def test_schema_changes():
    a = profile(pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    b = profile(pd.DataFrame({"a": [1, 2], "c": [3, 4]}))
    assert compare(a, b) == ["column removed: b", "column added: c"]
