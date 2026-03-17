"""
Merge occupations.csv + scores.json → site/data.json
Only includes leaf-level occupations (4-digit codes) for the treemap,
plus top-level categories for grouping.
"""

import csv
import json
import os

os.makedirs("site", exist_ok=True)

# Load
with open("occupations.csv", encoding="utf-8") as f:
    occupations = {r["code"]: r for r in csv.DictReader(f)}

with open("scores.json", encoding="utf-8") as f:
    scores = json.load(f)

# BRC category names (2-digit) for treemap grouping
categories = {code: occ["title"] for code, occ in occupations.items() if len(code) == 2}

output = []

for code, occ in occupations.items():
    # Include all levels for reference, but flag leaf nodes
    score_data = scores.get(code, {})
    jobs = occ["jobs_x1000"]
    annual = occ["annual_wage_est"]

    try:
        jobs_val = float(jobs) if jobs else 0
    except ValueError:
        jobs_val = 0

    try:
        wage_val = int(annual) if annual else None
    except ValueError:
        wage_val = None

    cat_code = code[:2]
    entry = {
        "code": code,
        "title": occ["title"],
        "level": int(occ["level"]),
        "category": occ["category"],
        "cat_code": cat_code,
        "jobs": jobs_val,           # thousands
        "median_hourly_wage": float(occ["median_hourly_wage"]) if occ["median_hourly_wage"] else None,
        "annual_wage": wage_val,
        "exposure": score_data.get("score"),
        "exposure_rationale": score_data.get("rationale", ""),
    }
    output.append(entry)

with open("site/data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# Stats
leaf = [e for e in output if e["level"] == 4]
scored = [e for e in leaf if e["exposure"] is not None]
total_jobs = sum(e["jobs"] for e in leaf)
print(f"Total entries: {len(output)}")
print(f"Leaf occupations (4-digit): {len(leaf)}")
print(f"  Scored: {len(scored)}")
print(f"  Total employment: {total_jobs:.0f}k ({total_jobs/1000:.1f}M people)")
if scored:
    avg = sum(e["exposure"] for e in scored) / len(scored)
    print(f"  Average AI exposure: {avg:.1f}/10")
print(f"\nWrote site/data.json")
