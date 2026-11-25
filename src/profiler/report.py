"""Render a profile as one self-contained HTML file (no JavaScript, no external assets)."""
from __future__ import annotations

import html

CSS = """
body{font:14px/1.45 system-ui,sans-serif;margin:2rem auto;max-width:1100px;color:#1f2328;padding:0 1rem}
h1{font-size:1.5rem}h2{font-size:1.1rem;margin-top:2rem}.muted{color:#656d76}
.warn{background:#fff8c5;border:1px solid #d4a72c55;border-radius:6px;padding:.6rem 1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.card{border:1px solid #d0d7de;border-radius:8px;padding:.8rem 1rem}
.card h3{margin:0 0 .3rem;font-size:1rem}table{border-collapse:collapse;width:100%}
td{padding:2px 4px;border-bottom:1px solid #eaeef2;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:12px;padding:0 6px;border-radius:10px;background:#ddf4ff;margin-right:4px}
.pii{background:#ffebe9}
"""


def _hist(counts, w=280, h=44):
    if not counts:
        return ""
    m = max(counts) or 1
    bw = w / len(counts)
    bars = "".join(
        f'<rect x="{i * bw:.1f}" y="{h - c / m * h:.1f}" width="{bw - 1:.1f}" height="{c / m * h:.1f}" fill="#54aeff"/>'
        for i, c in enumerate(counts))
    return f'<svg width="{w}" height="{h}" role="img" aria-label="histogram">{bars}</svg>'


def to_html(p: dict) -> str:
    e = html.escape
    warns = "".join(f"<li>{e(w)}</li>" for w in p["warnings"]) or "<li>none</li>"
    cards = []
    for name, c in p["column_profiles"].items():
        tags = f'<span class="tag">{e(c["inferred_type"])}</span>' + "".join(
            f'<span class="tag pii">PII: {e(x)}</span>' for x in c["pii_hint"])
        rows = [("nulls", f'{c["null_share"]:.1%}'), ("distinct", f'{c["distinct"]:,}')]
        nm = c.get("numeric")
        if nm:
            rows += [("min / median / max", f'{nm["min"]:g} / {nm["median"]:g} / {nm["max"]:g}'),
                     ("mean ± std", f'{nm["mean"]:g} ± {nm["std"]:g}'), ("extreme outliers", nm["extreme_outliers"])]
        if c["formats"]:
            rows.append(("formats", ", ".join(f"{k} {v:.0%}" for k, v in c["formats"].items())))
        top = ", ".join(f"{e(k)} ({v:,})" for k, v in list(c["top_values"].items())[:3])
        table = "".join(f"<tr><td class=muted>{k}</td><td>{e(str(v))}</td></tr>" for k, v in rows)
        cards.append(f'<div class="card"><h3>{e(name)}</h3>{tags}<table>{table}</table>'
                     f'{_hist(nm["histogram"]) if nm else ""}<div class="muted">top: {top}</div></div>')
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Profile: {e(p['name'])}</title>
<style>{CSS}</style></head><body>
<h1>Data profile: {e(p['name'])}</h1>
<p class="muted">{p['rows']:,} rows · {p['columns']} columns · {p['duplicate_rows']:,} duplicate rows ·
candidate keys: {e(', '.join(p['candidate_keys']) or 'none')} · profiled {e(p['profiled_at'])}</p>
<h2>Needs a look</h2><div class="warn"><ul>{warns}</ul></div>
<h2>Columns</h2><div class="grid">{''.join(cards)}</div></body></html>"""
