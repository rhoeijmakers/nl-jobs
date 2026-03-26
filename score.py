"""
Score each occupation for AI exposure using Claude (Anthropic API).
Reads pages/*.md and outputs scores.json.

Usage:
  export ANTHROPIC_API_KEY=...
  python3 score.py
"""

import csv
import json
import os
import re
import sys
import time
import glob

import anthropic

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    sys.exit("Error: ANTHROPIC_API_KEY is not set.")

client = anthropic.Anthropic(api_key=API_KEY)

MODEL = "claude-haiku-4-5"   # fast + cheap for bulk scoring; swap for opus if you want deeper analysis
PAGES_DIR = "pages"
SCORES_FILE = "scores.json"

SYSTEM_PROMPT = (
    "Je bent een expert arbeidsmarkteconomist die analyseert in hoeverre huidige AI-technologie "
    "(grote taalmodellen, computervisie, robotica, etc.) beroepen zal transformeren. "
    "Reageer altijd met geldige JSON — geen markdown, geen codeblokken, geen extra tekst."
)

PROMPT_TEMPLATE = """Beoordeel het volgende Nederlandse beroep op AI-invloed op een schaal van 0 tot 10:
- 0-1: Minimale invloed. Sterk fysiek, manueel, of vereist constante aanwezigheid in de echte wereld (bijv. dakdekker, vuilnisophaler).
- 2-3: Lage invloed. Sommige routinetaken zijn automatiseerbaar, maar het kernwerk vereist menselijk oordeel of handigheid.
- 4-5: Matige invloed. Mix van automatiseerbare en niet-automatiseerbare taken.
- 6-7: Hoge invloed. Veel taken zijn digitaal, routinematig of kennisgebaseerd en worden al getransformeerd door AI-tools.
- 8-9: Zeer hoge invloed. De meeste werkproducten zijn digitaal; AI kan de meeste taken uitvoeren met minimale menselijke supervisie.
- 10: Maximale invloed. Het werk is bijna volledig digitaal en repetitief (bijv. medische transcriptie).

Belangrijke factoren om te overwegen:
- Zijn de werkproducten fundamenteel digitaal?
- Kan het werk op afstand/online worden gedaan?
- Betreft het beroep het creëren van creatieve of originele inhoud?
- Betreft het patroonherkenning, data-analyse of tekstverwerking?
- Vereist het fysieke aanwezigheid, manuele behendigheid of zintuiglijk oordeel?

--- BEROEP ---
{content}

Reageer met geldige JSON, in dit exacte formaat:
{{"score": <getal 0-10>, "rationale": "<2-3 zinnen toelichting in het Nederlands>"}}"""


def score_occupation(title: str, content: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(content=content[:3000])
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            # Strip markdown code fences (```json ... ``` or ``` ... ```)
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"  JSON parse error, attempt {attempt + 1}: {text[:80]!r}")
            time.sleep(1)
        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            print(f"  API error {e.status_code}: {e.message}")
            time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2)
    return {"score": None, "rationale": "Fout: beoordeling mislukt."}


# Load existing scores
if os.path.exists(SCORES_FILE):
    with open(SCORES_FILE, encoding="utf-8") as f:
        scores = json.load(f)
else:
    scores = {}

# Load occupations list
with open("occupations.csv", encoding="utf-8") as f:
    occupations = list(csv.DictReader(f))

total = len(occupations)
new_scores = 0

for i, occ in enumerate(occupations):
    code = occ["code"]
    title = occ["title"]

    if code in scores and scores[code].get("score") is not None:
        print(f"  [{i+1}/{total}] {code} {title[:40]} — skip (cached)")
        continue

    # Find the markdown file
    pattern = os.path.join(PAGES_DIR, f"{code}_*.md")
    matches = glob.glob(pattern)
    if not matches:
        print(f"  [{i+1}/{total}] {code} {title[:40]} — no page file, skipping")
        scores[code] = {"score": None, "rationale": "Geen beschrijving beschikbaar."}
        continue

    with open(matches[0], encoding="utf-8") as f:
        content = f.read()

    print(f"  [{i+1}/{total}] {code} {title[:40]}", end=" ", flush=True)
    result = score_occupation(title, content)
    scores[code] = result
    new_scores += 1
    print(f"→ {result.get('score')}")

    # Save periodically
    if new_scores % 10 == 0:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

    time.sleep(0.2)  # gentle rate limiting

# Final save
with open(SCORES_FILE, "w", encoding="utf-8") as f:
    json.dump(scores, f, ensure_ascii=False, indent=2)

valid = [v["score"] for v in scores.values() if v.get("score") is not None]
print(f"\nScored {len(valid)}/{total} occupations.")
if valid:
    print(f"Average AI exposure: {sum(valid)/len(valid):.1f}/10")
