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
    "You are an expert labor economist analyzing how much current AI technology "
    "(large language models, computer vision, robotics, etc.) will reshape occupations. "
    "Always respond with valid JSON only — no markdown, no code blocks, no extra text."
)

PROMPT_TEMPLATE = """Score the following Dutch occupation for AI exposure on a scale from 0 to 10:
- 0-1: Minimal exposure. Highly physical, manual, or requires constant real-world presence (e.g., roofer, garbage collector).
- 2-3: Low exposure. Some routine tasks automatable, but core work requires human judgment or dexterity.
- 4-5: Moderate exposure. Mix of automatable and non-automatable tasks.
- 6-7: High exposure. Many tasks are digital, routine, or knowledge-based and are already being transformed by AI tools.
- 8-9: Very high exposure. Most work products are digital; AI can do most tasks with minimal human oversight.
- 10: Maximum exposure. Work is almost entirely digital and repetitive (e.g., medical transcription).

Key factors to consider:
- Are the work products fundamentally digital?
- Can the work be done remotely/online?
- Does the occupation involve creative or original content generation?
- Does it involve pattern recognition, data analysis, or text processing?
- Does it require physical presence, manual dexterity, or sensory judgment?

--- OCCUPATION ---
{content}

Respond with valid JSON only, in this exact format:
{{"score": <number 0-10>, "rationale": "<2-3 sentence explanation in English>"}}"""


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
    return {"score": None, "rationale": "Error: failed to score."}


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
        scores[code] = {"score": None, "rationale": "No description available."}
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
