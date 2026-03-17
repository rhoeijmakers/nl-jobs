"""
Fetch ESCO occupation descriptions for each occupation in occupations.csv.
Uses Dutch titles to search ESCO, then fetches the full description + skills.
Outputs pages/ directory with one Markdown file per occupation.
"""

import csv
import json
import time
import os
import re
import requests

ESCO_SEARCH = "https://ec.europa.eu/esco/api/search"
ESCO_OCC = "https://ec.europa.eu/esco/api/resource/occupation"
PAGES_DIR = "pages"
CACHE_FILE = "esco_cache.json"
LANGUAGE = "nl"
ESCO_VERSION = "v1.2.0"

os.makedirs(PAGES_DIR, exist_ok=True)

# Load cache to avoid re-fetching
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = json.load(f)
else:
    cache = {}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def search_esco(title: str) -> dict | None:
    if title in cache:
        return cache[title]
    try:
        r = requests.get(ESCO_SEARCH, params={
            "text": title,
            "language": LANGUAGE,
            "type": "occupation",
            "limit": 1,
            "selectedVersion": ESCO_VERSION,
        }, timeout=15)
        r.raise_for_status()
        results = r.json().get("_embedded", {}).get("results", [])
        result = results[0] if results else None
        cache[title] = result
        time.sleep(0.2)
        return result
    except Exception as e:
        print(f"  ESCO search error for '{title}': {e}")
        return None


def fetch_esco_concept(uri: str) -> dict | None:
    cache_key = f"uri:{uri}"
    if cache_key in cache:
        return cache[cache_key]
    try:
        r = requests.get(ESCO_OCC, params={
            "uri": uri,
            "language": LANGUAGE,
            "selectedVersion": ESCO_VERSION,
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        cache[cache_key] = data
        time.sleep(0.2)
        return data
    except Exception as e:
        print(f"  ESCO concept error for '{uri}': {e}")
        return None


def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# Load occupations
with open("occupations.csv", encoding="utf-8") as f:
    occupations = list(csv.DictReader(f))

print(f"Processing {len(occupations)} occupations...")

for i, occ in enumerate(occupations):
    code = occ["code"]
    title = occ["title"]
    slug = f"{code}_{slugify(title)}"
    outfile = os.path.join(PAGES_DIR, f"{slug}.md")

    if os.path.exists(outfile):
        print(f"  [{i+1}/{len(occupations)}] {code} {title[:40]} — cached")
        continue

    print(f"  [{i+1}/{len(occupations)}] {code} {title[:40]}")

    # Search ESCO
    result = search_esco(title)
    if not result:
        # Write a minimal page with just the title
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\nGeen ESCO-beschrijving gevonden.\n")
        continue

    esco_title = result.get("title", title)
    uri = result.get("uri", "")

    concept = fetch_esco_concept(uri) if uri else None

    # Build markdown
    lines = [f"# {title}"]
    lines.append(f"\n**ESCO titel:** {esco_title}")
    if uri:
        lines.append(f"**ESCO URI:** {uri}")
    lines.append("")

    if concept:
        desc = (concept.get("description") or {}).get(LANGUAGE, {})
        desc_text = desc.get("literal") if isinstance(desc, dict) else None
        if desc_text:
            lines.append("## Beschrijving")
            lines.append(desc_text)
            lines.append("")

        links = concept.get("_links", {})

        essential_skills = links.get("hasEssentialSkill", [])
        if essential_skills:
            lines.append("## Kernvaardigheden")
            for s in essential_skills[:15]:
                lines.append(f"- {s.get('title', '')}")
            lines.append("")

        optional_skills = links.get("hasOptionalSkill", [])
        if optional_skills:
            lines.append("## Optionele vaardigheden")
            for s in optional_skills[:10]:
                lines.append(f"- {s.get('title', '')}")
            lines.append("")

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Save cache periodically
    if (i + 1) % 20 == 0:
        save_cache()

save_cache()
print(f"\nDone. Pages written to {PAGES_DIR}/")
