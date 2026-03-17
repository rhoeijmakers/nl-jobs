"""
Fetch CBS occupation data: employment counts and hourly wages.
Outputs occupations.csv with columns:
  code, title, level, category, jobs_x1000, median_hourly_wage, annual_wage_est
"""

import csv
import cbsodata

YEAR = "2023JJ00"

# --- Employment counts (85276NED) ---
print("Fetching employment data from CBS 85276NED...")
emp_data = cbsodata.get_data(
    "85276NED",
    filters=f"Perioden eq '{YEAR}'",
)
emp = {
    r["Beroep"]: r["WerkzameBeroepsbevolking_1"]
    for r in emp_data
    if r["Geslacht"] == "Totaal mannen en vrouwen"
    and r["Persoonskenmerken"] == "Totaal personen"
}
print(f"  {len(emp)} occupation entries")

# --- Wages (85517NED) ---
print("Fetching wage data from CBS 85517NED...")
wage_data = cbsodata.get_data(
    "85517NED",
    filters=f"Perioden eq '{YEAR}'",
)
wage = {
    r["Beroep"]: r["k_50ePercentielMediaan_3"]
    for r in wage_data
}
print(f"  {len(wage)} occupation wage entries")

# --- Merge ---
# Parse occupation code and level from the 'Beroep' string
# Format: "01 Pedagogische beroepen" or "011 Docenten" or "0111 Docenten hoger..."
def parse_code_title(beroep: str):
    parts = beroep.strip().split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", beroep

# BRC 2014 top-level categories (2-digit codes)
# We infer category from the first 2 characters of the code
CATEGORIES = {
    "01": "Pedagogische beroepen",
    "02": "Creatieve en taalkundige beroepen",
    "03": "Commerciële beroepen",
    "04": "Bedrijfseconomische en administratieve beroepen",
    "05": "Managers",
    "06": "Openbaar bestuur, veiligheid en juridische beroepen",
    "07": "Technische beroepen",
    "08": "ICT-beroepen",
    "09": "Agrarische beroepen",
    "10": "Transport en logistiek beroepen",
    "11": "Medische en paramedische beroepen",
    "12": "Verzorgende en dienstverlenende beroepen",
    "13": "Bouwberoepen",
    "14": "Productie en installatieberoepen",
    "15": "Overige beroepen",
}

rows = []
skipped = set(["Totaal", "Beroepsniveau 1 (ISCO 2008)", "Beroepsniveau 2 (ISCO 2008)",
               "Beroepsniveau 3 (ISCO 2008)", "Beroepsniveau 4 (ISCO 2008)",
               "Beroepsniveau onbekend (ISCO 2008)"])

for beroep, jobs in emp.items():
    if beroep in skipped or beroep.startswith("Beroepsniveau"):
        continue

    code, title = parse_code_title(beroep)
    if not code.isdigit():
        continue

    level = len(code)  # 2 = major group, 3 = sub-major, 4 = unit group
    cat_code = code[:2]
    category = CATEGORIES.get(cat_code, "Overig")

    hourly = wage.get(beroep)
    # Estimate annual salary: hourly * 36 hours/week * 52 weeks (NL average)
    annual = round(float(hourly) * 36 * 52) if hourly else None

    rows.append({
        "code": code,
        "title": title.strip(),
        "level": level,
        "category": category,
        "jobs_x1000": jobs,
        "median_hourly_wage": hourly,
        "annual_wage_est": annual,
    })

rows.sort(key=lambda r: r["code"])

outfile = "occupations.csv"
with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"\nWrote {len(rows)} rows to {outfile}")
print("\nSample:")
for r in rows[:6]:
    print(f"  [{r['code']}] {r['title'][:40]:40s}  jobs={r['jobs_x1000']}k  wage=€{r['annual_wage_est']}")
