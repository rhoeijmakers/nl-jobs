# Claude Code Briefing — nl-jobs: Add Education Layer

**Repo:** https://github.com/rhoeijmakers/nl-jobs  
**Branch:** `feature/education-layer` (create from `master`, do not commit to `master`)  
**Goal:** Add education level as a fourth colour layer in the treemap, analogous to what Karpathy did for the US with BLS data — but sourced from ISCO skill levels already embedded in the Dutch data pipeline.

---

## Project overview

An interactive treemap visualising AI exposure across Dutch occupations. Built on:
- **CBS StatLine** for employment counts and wages (via `cbsodata` Python library)
- **ESCO v1.2** occupation descriptions for LLM scoring
- **BRC 2014** occupation classification (Dutch national, derived from ISCO-08)
- Static `site/index.html` frontend consuming `site/data.json`

The pipeline runs in sequence:

```
fetch_data.py          → occupations.csv   (CBS employment + wage data)
fetch_descriptions.py  → esco_cache.json   (ESCO occupation descriptions)
score.py               → scores.json       (AI exposure scores via Claude API)
build_site_data.py     → site/data.json    (merged, consumed by frontend)
```

Current treemap colour layers: **AI Exposure** and **Wage** (median hourly). The task is to add **Education Level** as a third selectable layer.

---

## What education data is available

The ISCO-08 classification already assigns every occupation a **skill level** (1–4), which maps directly to required education:

| ISCO Skill Level | Required education (NL) |
|---|---|
| 1 | Basisonderwijs / elementair |
| 2 | VMBO / MBO niveau 1–2 |
| 3 | MBO niveau 3–4 / HAVO / HBO-ad |
| 4 | HBO-bachelor of hoger / WO |

This is a **structural, normative** measure (what education the job formally requires). It is already implicit in the BRC codes used in `fetch_data.py` — the 2-digit BRC category maps to ISCO major groups, which carry skill levels.

**The ISCO skill level is derivable from the BRC code prefix without any external API call.** It is a deterministic mapping, not an estimate.

---

## Implementation plan

### Step 1 — Add ISCO skill level mapping to `fetch_data.py`

Add a lookup dict mapping BRC 2-digit category codes to ISCO skill levels. The mapping is:

```python
ISCO_SKILL_LEVEL = {
    "01": 4,  # Pedagogische beroepen (HBO/WO)
    "02": 3,  # Creatieve en taalkundige beroepen (MBO/HBO)
    "03": 3,  # Commerciële beroepen
    "04": 3,  # Bedrijfseconomische en administratieve beroepen
    "05": 4,  # Managers (HBO/WO)
    "06": 4,  # Openbaar bestuur, veiligheid en juridische beroepen
    "07": 3,  # Technische beroepen
    "08": 4,  # ICT-beroepen (HBO/WO)
    "09": 2,  # Agrarische beroepen (MBO)
    "10": 4,  # Medische en paramedische beroepen
    "11": 2,  # Verzorgende en dienstverlenende beroepen
    "12": 2,  # Transport en logistiek beroepen
    "13": 2,  # Bouwberoepen
    "14": 2,  # Productie en installatieberoepen
    "15": 2,  # Overige beroepen
}
```

Add `isco_skill_level` as a column in the output CSV rows. Include it in the `fieldnames` list passed to `csv.DictWriter`.

### Step 2 — Pass it through `build_site_data.py`

In `build_site_data.py`, the `entry` dict is built from `occupations.csv`. Add:

```python
"isco_skill_level": int(occ["isco_skill_level"]) if occ["isco_skill_level"] else None,
```

No other changes to this file.

### Step 3 — Add the colour layer to `site/index.html`

The frontend already has layer toggle logic for AI Exposure and Wage. Add a third option:

**In the layer selector UI** — add a button/tab for "Opleidingsniveau".

**In the colour scale logic** — the education layer uses a 4-step sequential scale (1–4), not a continuous gradient. Suggested colours (deuteranopia-safe):

```
1 → #d4e6f1  (lichtblauw — elementair)
2 → #5dade2  (blauw — MBO)
3 → #1a5276  (donkerblauw — HBO)
4 → #0b3d91  (diepblauw — WO)
```

Or use the same green→red scheme as AI exposure, with 4 discrete steps. Match whatever the existing colour system uses — do not introduce a second colour library.

**In the tooltip/detail panel** — when education layer is active, show the skill level as human-readable Dutch text:

```
1 → "Elementair / basisonderwijs"
2 → "MBO niveau 1–2 / VMBO"
3 → "MBO niveau 3–4 / HBO-ad"
4 → "HBO-bachelor of hoger"
```

**Key constraint:** The `isco_skill_level` values are integers 1–4. The frontend should handle `null` values gracefully (some entries may have no level assigned) — show them as grey/neutral, same as unscored occupations in the AI exposure layer.

---

## Files to modify

| File | Change |
|---|---|
| `fetch_data.py` | Add `ISCO_SKILL_LEVEL` dict; add `isco_skill_level` field to each row |
| `build_site_data.py` | Pass `isco_skill_level` through to `site/data.json` |
| `site/index.html` | Add education layer toggle + colour rendering + tooltip text |

**Do not modify:** `fetch_descriptions.py`, `score.py`, `esco_cache.json`, `scores.json`, `occupations.csv`, `README.md`

After changes to `fetch_data.py` or `build_site_data.py`, the pipeline must be re-run to regenerate `occupations.csv` and `site/data.json`. Do not manually edit those generated files.

---

## Branch and PR instructions

```bash
git checkout master
git pull
git checkout -b feature/education-layer
```

Work on this branch only. When complete, open a pull request against `master` with:
- A brief description of what was added
- Confirmation that the pipeline was re-run and `site/data.json` contains `isco_skill_level` for all entries
- A note on any edge cases found (nulls, missing mappings, etc.)

Do not merge — leave for review.

---

## Verify your work

After re-running the pipeline, check:

```bash
python -c "
import json
data = json.load(open('site/data.json'))
leaf = [e for e in data if e['level'] == 4]
with_edu = [e for e in leaf if e['isco_skill_level'] is not None]
print(f'Leaf occupations: {len(leaf)}')
print(f'With education level: {len(with_edu)}')
from collections import Counter
print(Counter(e['isco_skill_level'] for e in with_edu))
"
```

Expected: all or nearly all leaf occupations have a non-null `isco_skill_level`. The Counter should show a distribution across levels 2, 3, and 4 (level 1 occupations are rare in Dutch BRC data).

Open `site/index.html` in a browser and confirm the education toggle is visible and colours render correctly across the treemap.

---

## Context and intent

This feature mirrors what Karpathy included in his US visualisation — education as a government-data layer, not an LLM estimate. The ISCO skill level is the closest equivalent for the Dutch/ESCO context, and it is structurally clean: a deterministic mapping from BRC category to skill level, requiring no additional API calls or scoring runs.

The interesting analytical question this unlocks: does the correlation between education level and AI exposure hold in the Dutch data as it does in the US? That comparison becomes visible once both layers exist in the same frontend.
