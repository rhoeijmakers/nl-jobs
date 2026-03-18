# NL Job Market & AI Exposure Visualizer

An interactive treemap visualizing how exposed Dutch occupations are to AI — adapted from [mariodian/jobs](https://github.com/mariodian/jobs) (originally by Andrej Karpathy) for the Netherlands using [ESCO](https://esco.ec.europa.eu/) occupation data.

**Live demo:** [nljobs.hoeijmakers.net](https://nljobs.hoeijmakers.net/)

## What's here

The [ESCO classification](https://esco.ec.europa.eu/en/classification/occupation_main) covers **114 Dutch occupational groups** across all sectors. Each rectangle in the treemap is sized by total employment and coloured by AI exposure score (1–10), scored by Claude (Anthropic).

## Pipeline

```
fetch_data.py          # Pull occupation list + employment from CBS/ESCO
fetch_descriptions.py  # Scrape full ESCO occupation descriptions
score.py               # Score each occupation with Claude (ANTHROPIC_API_KEY required)
build_site_data.py     # Build site/data.json from scores + employment data
```

## Run it yourself

```bash
python3 -m venv venv && source venv/bin/activate
pip install anthropic requests beautifulsoup4

export ANTHROPIC_API_KEY=your-key-here

python fetch_data.py
python fetch_descriptions.py
python score.py
python build_site_data.py
```

Then open `site/index.html` in your browser.

## Why ESCO and not ISCO?

A common question when adapting this for a new country. The short answer: **ESCO has rich occupation descriptions; ISCO doesn't.**

[ISCO-08](https://www.ilo.org/public/english/bureau/stat/isco/isco08/) is the international standard classification — it provides short titles and one-line definitions per occupation. That's too thin for LLM-based scoring to produce meaningful results.

[ESCO v1.2](https://esco.ec.europa.eu/) (European Skills, Competences, Qualifications and Occupations) is built on top of ISCO-08 but adds detailed descriptions per occupation: tasks performed, required knowledge, skills, and competences. That's exactly what Claude needs as input to score AI exposure reliably.

Additional reasons:
- ESCO descriptions are available in **27 EU languages**, including Dutch
- CBS StatLine (Dutch employment data) uses an ISCO-based national classification that maps cleanly to ESCO

In practice: CBS codes provide the employment numbers; ESCO descriptions provide the scoring input. If you're adapting this for a non-EU country without good ESCO coverage, you could substitute BLS Occupational Outlook Handbook descriptions (as Karpathy does for the US) or any other source with detailed per-occupation text.

## Credits

- Original concept & visualisation: [Andrej Karpathy](https://karpathy.ai/jobs/)
- Fork base: [mariodian/jobs](https://github.com/mariodian/jobs)
- Data: [ESCO v1.2](https://esco.ec.europa.eu/) · [CBS StatLine](https://opendata.cbs.nl/)
- AI scoring: [Claude](https://anthropic.com) (Anthropic)
