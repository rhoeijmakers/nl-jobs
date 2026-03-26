"""
Fetch ESCO occupation descriptions for each occupation in occupations.csv.
Uses the CBS BRC→ISCO-08 concordance (Bijlage 2 of BRC 2014) to filter ESCO
queries by iscoGroup, avoiding wrong matches like "architect" → "IT architect".
Falls back to free-text search for codes not in the concordance.
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
ESCO_CONCEPT = "https://ec.europa.eu/esco/api/resource/concept"
PAGES_DIR = "pages"
CACHE_FILE = "esco_cache.json"
LANGUAGE = "nl"
ESCO_VERSION = "v1.2.0"

# BRC 2014 (4-digit) → primary ISCO-08 unit group
# Source: Bijlage 2, "Beroepenindeling ROA-CBS 2014" (CBS/ROA, 2022)
# Primary = ISCO group with the highest percentage share for that BRC code.
BRC_TO_ISCO = {
    "0111": "2310",  # Docenten hoger onderwijs en hoogleraren
    "0112": "2320",  # Docenten beroepsgerichte vakken secundair onderwijs
    "0113": "2330",  # Docenten algemene vakken secundair onderwijs
    "0114": "2341",  # Leerkrachten basisonderwijs
    "0115": "2359",  # Onderwijskundigen en overige docenten
    "0121": "3422",  # Sportinstructeurs
    "0131": "5311",  # Leidsters kinderopvang en onderwijsassistenten
    "0211": "2622",  # Bibliothecarissen en conservatoren
    "0212": "2641",  # Auteurs en taalkundigen
    "0213": "2642",  # Journalisten
    "0214": "2651",  # Beeldend kunstenaars
    "0215": "2652",  # Uitvoerend kunstenaars
    "0221": "2166",  # Grafisch vormgevers en productontwerpers
    "0222": "3431",  # Fotografen en interieurontwerpers
    "0311": "2431",  # Adviseurs marketing, public relations en sales
    "0321": "3322",  # Vertegenwoordigers en inkopers
    "0331": "5221",  # Winkeliers en teamleiders detailhandel
    "0332": "5223",  # Verkoopmedewerkers detailhandel
    "0333": "5230",  # Kassamedewerkers
    "0334": "5244",  # Callcentermedewerkers outbound en overige verkopers
    "0411": "2411",  # Accountants
    "0412": "2412",  # Financieel specialisten en economen
    "0413": "2421",  # Bedrijfskundigen en organisatieadviseurs
    "0414": "2422",  # Beleidsadviseurs
    "0415": "2423",  # Specialisten personeels- en loopbaanontwikkeling
    "0421": "3313",  # Boekhouders
    "0422": "3339",  # Zakelijke dienstverleners
    "0423": "3343",  # Directiesecretaresses
    "0431": "4110",  # Administratief medewerkers
    "0432": "4120",  # Secretaresses
    "0433": "4225",  # Receptionisten en telefonisten
    "0434": "4312",  # Boekhoudkundig medewerkers
    "0435": "4321",  # Transportplanners en logistiek medewerkers
    "0511": "1120",  # Algemeen directeuren
    "0521": "1211",  # Managers zakelijke en administratieve dienstverlening
    "0522": "1221",  # Managers verkoop en marketing
    "0531": "1321",  # Managers productie
    "0532": "1324",  # Managers logistiek
    "0533": "1330",  # Managers ICT
    "0534": "1342",  # Managers zorginstellingen
    "0535": "1345",  # Managers onderwijs
    "0536": "1349",  # Managers gespecialiseerde dienstverlening n.e.g.
    "0541": "1412",  # Managers horeca
    "0542": "1420",  # Managers detail- en groothandel
    "0543": "1439",  # Managers commerciële en persoonlijke dienstverlening n.e.g.
    "0551": "1000",  # Managers z.n.d.
    "0611": "1112",  # Overheidsbestuurders
    "0612": "3353",  # Overheidsambtenaren
    "0621": "2619",  # Juristen
    "0631": "3355",  # Politie-inspecteurs
    "0632": "5412",  # Politie en brandweer
    "0633": "5414",  # Beveiligingspersoneel
    "0634": "0310",  # Militaire beroepen
    "0711": "2131",  # Biologen en natuurwetenschappers
    "0712": "2144",  # Ingenieurs (geen elektrotechniek)
    "0713": "2152",  # Elektrotechnisch ingenieurs
    "0714": "2161",  # Architecten
    "0721": "3118",  # Technici bouwkunde en natuur
    "0722": "3122",  # Productieleiders industrie en bouw
    "0723": "3133",  # Procesoperators
    "0731": "7112",  # Bouwarbeiders ruwbouw
    "0732": "7115",  # Timmerlieden
    "0733": "7122",  # Bouwarbeiders afbouw
    "0734": "7126",  # Loodgieters en pijpfitters
    "0735": "7131",  # Schilders en metaalspuiters
    "0741": "7223",  # Metaalbewerkers en constructiewerkers
    "0742": "7212",  # Lassers en plaatwerkers
    "0743": "7231",  # Automonteurs
    "0744": "7233",  # Machinemonteurs
    "0751": "7511",  # Slagers
    "0752": "7512",  # Bakkers
    "0753": "7543",  # Productcontroleurs
    "0754": "7522",  # Meubelmakers, kleermakers en stoffeerders
    "0755": "7322",  # Medewerkers drukkerij en kunstnijverheid
    "0761": "7412",  # Elektriciens en elektronicamonteurs
    "0771": "8160",  # Productiemachinebedieners
    "0772": "8219",  # Assemblagemedewerkers
    "0781": "9321",  # Hulpkrachten bouw en industrie
    "0811": "2511",  # Software- en applicatieontwikkelaars
    "0812": "2522",  # Databank- en netwerkspecialisten
    "0821": "3512",  # Gebruikersondersteuning ICT
    "0822": "3521",  # Radio- en televisietechnici
    "0911": "6111",  # Land- en bosbouwers
    "0912": "6113",  # Hoveniers, tuinders en kwekers
    "0913": "6121",  # Veetelers
    "0921": "9214",  # Hulpkrachten landbouw
    "1011": "2212",  # Artsen
    "1012": "2221",  # Gespecialiseerd verpleegkundigen
    "1013": "2264",  # Fysiotherapeuten
    "1021": "2635",  # Maatschappelijk werkers
    "1022": "2634",  # Psychologen en sociologen
    "1031": "3212",  # Laboranten
    "1032": "3213",  # Apothekersassistenten
    "1033": "3221",  # Verpleegkundigen (mbo)
    "1034": "3256",  # Medisch praktijkassistenten
    "1035": "3257",  # Medisch vakspecialisten
    "1041": "3412",  # Sociaal werkers, groeps- en woonbegeleiders
    "1051": "5321",  # Verzorgenden
    "1111": "5111",  # Reisbegeleiders
    "1112": "5120",  # Koks
    "1113": "5131",  # Kelners en barpersoneel
    "1114": "5141",  # Kappers en schoonheidsspecialisten
    "1115": "5153",  # Conciërges en teamleiders schoonmaak
    "1116": "5164",  # Verleners van overige persoonlijke diensten
    "1121": "9112",  # Schoonmakers
    "1122": "9412",  # Keukenhulpen
    "1211": "3152",  # Dekofficieren en piloten
    "1212": "8322",  # Chauffeurs auto's, taxi's en bestelwagens
    "1213": "8331",  # Buschauffeurs en trambestuurders
    "1214": "8332",  # Vrachtwagenchauffeurs
    "1215": "8344",  # Bedieners mobiele machines
    "1221": "9334",  # Laders, lossers en vakkenvullers
    "1222": "9621",  # Vuilnisophalers en dagbladenbezorgers
    "1311": "9999",  # Overig
}

os.makedirs(PAGES_DIR, exist_ok=True)

# Load cache to avoid re-fetching
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = json.load(f)
else:
    cache = {}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _word_overlap(a: str, b: str) -> float:
    """Simple word-overlap similarity between two strings (0.0–1.0)."""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def search_esco_by_isco(brc_title: str, isco_code: str) -> dict | None:
    """
    Fetch all ESCO occupations in the given ISCO-08 unit group via the concept
    endpoint's narrowerOccupation links, then return the one whose Dutch title
    best matches brc_title.
    Cache key includes the isco_code so results are reusable.
    """
    cache_key = f"isco:{isco_code}"
    if cache_key in cache:
        candidates = cache[cache_key]
    else:
        try:
            r = requests.get(ESCO_CONCEPT, params={
                "uri": f"http://data.europa.eu/esco/isco/C{isco_code}",
                "language": LANGUAGE,
                "selectedVersion": ESCO_VERSION,
            }, timeout=15)
            r.raise_for_status()
            candidates = r.json().get("_links", {}).get("narrowerOccupation", [])
            cache[cache_key] = candidates
            time.sleep(0.2)
        except Exception as e:
            print(f"  ESCO concept error for ISCO {isco_code}: {e}")
            return None

    if not candidates:
        return None

    # Pick the candidate with the highest word-overlap with the BRC title
    best = max(candidates, key=lambda c: _word_overlap(brc_title, c.get("title", "")))
    return best


def search_esco_freetext(title: str) -> dict | None:
    """Fallback: free-text ESCO search, takes top result."""
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

    print(f"  [{i+1}/{len(occupations)}] {code} {title[:40]}", end=" ", flush=True)

    # Search ESCO: prefer ISCO-bridged lookup for 4-digit BRC codes
    isco_code = BRC_TO_ISCO.get(code)
    if isco_code:
        result = search_esco_by_isco(title, isco_code)
        method = f"isco:{isco_code}"
    else:
        result = search_esco_freetext(title)
        method = "freetext"

    if not result:
        print(f"→ no ESCO match ({method})")
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\nGeen ESCO-beschrijving gevonden.\n")
        continue

    esco_title = result.get("title", title)
    uri = result.get("uri", "")
    print(f"→ {esco_title[:50]} ({method})")

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
