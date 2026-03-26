# nl-jobs — Project Context

An interactive treemap visualising AI exposure and labour market data across Dutch occupations. Static site, no build step.

**Live repo:** https://github.com/rhoeijmakers/nl-jobs

---

## Stack

- **Frontend:** Single-file `site/index.html` — vanilla JS + D3.js (CDN). No framework, no bundler.
- **Data pipeline:** Python scripts producing `site/data.json`, consumed by the frontend.
- **Data sources:** CBS StatLine (employment + wages), ESCO v1.2 (occupation descriptions), Claude API (AI exposure scoring).

---

## Data pipeline

Run in sequence when source data needs refreshing:

```
fetch_data.py          → occupations.csv        (CBS employment + wage data)
fetch_descriptions.py  → esco_cache.json        (ESCO occupation descriptions, cached)
score.py               → scores.json            (AI exposure scores via Claude API)
build_site_data.py     → site/data.json         (merged output, consumed by frontend)
```

**Do not manually edit** `occupations.csv`, `scores.json`, or `site/data.json` — they are generated files.

To preview the site locally:
```bash
cd site && python3 -m http.server 8080
```

---

## Frontend architecture

`site/index.html` is self-contained. Key sections:

- **Colour layers:** AI Exposure, Wage (median hourly), Education Level (ISCO skill level 1–4). Toggled via `#controls` buttons.
- **Treemap:** D3 treemap, rendered into `#treemap-container`. Re-rendered on layer switch or resize. Width/height read from `container.clientWidth` / `container.clientHeight`.
- **Dashboard:** KPI cards + mini charts rendered above the treemap, also D3.
- **Tooltip:** Shown on hover/tap, positioned with viewport edge detection.

Version string is in the footer (`v2.x`). Update it when shipping visible changes.

---

## Data shape (`site/data.json`)

Each entry is an occupation at one of four BRC hierarchy levels (field: `level`). The treemap uses only leaf nodes (`level === 4`) grouped by their 2-digit `cat_code`.

Key fields:
| Field | Type | Notes |
|---|---|---|
| `code` | string | BRC code (2–4 digits) |
| `title` | string | Dutch occupation name |
| `level` | int | 2 = category, 4 = leaf |
| `jobs` | float | Employment in thousands |
| `median_hourly_wage` | float\|null | € per hour |
| `exposure` | float\|null | AI exposure score 0–10 |
| `isco_skill_level` | int\|null | ISCO skill level 1–4 |

---

## Conventions

- No TypeScript, no npm, no build step. Keep it a single HTML file.
- CSS lives in the `<style>` block at the top of `index.html`.
- JS lives in the `<script>` block at the bottom of `index.html`.
- Horizontal padding on page sections is consistently **20px** left and right (header, stats, dashboard). Match this for any new sections.
- Null values (unscored occupations, missing wages) must render gracefully — use grey/neutral, never crash.
- The version number in the footer follows `vMAJOR.MINOR`. Increment MINOR for new features, keep it as-is for bug fixes.
- Branch from `master`. Open PRs against `master`. Do not commit directly to `master`.
