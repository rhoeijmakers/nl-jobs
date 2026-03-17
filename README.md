# NL Job Market & AI Exposure Visualizer

An interactive treemap visualizing how exposed Dutch occupations are to AI — adapted from [mariodian/jobs](https://github.com/mariodian/jobs) (originally by Andrej Karpathy) for the Netherlands using [ESCO](https://esco.ec.europa.eu/) occupation data.

**Live demo:** [rhoeijmakers.github.io/nl-jobs](https://rhoeijmakers.github.io/nl-jobs/)

## What's here

The [ESCO classification](https://esco.ec.europa.eu/en/classification/occupation_main) covers **168 Dutch occupational groups** across all sectors. Each rectangle in the treemap is sized by total employment and coloured by AI exposure score (1–10), scored by Claude (Anthropic).

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

## Credits

- Original concept & visualisation: [Andrej Karpathy](https://karpathy.ai/jobs/)
- Fork base: [mariodian/jobs](https://github.com/mariodian/jobs)
- Data: [ESCO v1.2](https://esco.ec.europa.eu/) · [CBS StatLine](https://opendata.cbs.nl/)
- AI scoring: [Claude](https://anthropic.com) (Anthropic)
