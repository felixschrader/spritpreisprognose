# feiertage.py
# Lädt alle deutschen Feiertage (2014 bis aktuelles Jahr + 2) nach Bundesland
# via feiertage-api.de (bundesAPI) — kein API-Key nötig

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

# Alle 16 Bundesländer + national
BUNDESLAENDER = {
    "NATIONAL": "Bundesweit",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}

# Dynamischer Zeitraum: 2014 bis aktuelles Jahr + 2
START_JAHR = 2014
BASE_URL = "https://feiertage-api.de/api/"


def main():
    end_jahr = datetime.now().year + 2
    jahre = range(START_JAHR, end_jahr + 1)
    rows = []

    for jahr in jahre:
        print(f"Lade {jahr}...")
        for kuerzel, name in BUNDESLAENDER.items():
            params = {"jahr": jahr, "nur_land": kuerzel}
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            daten = response.json()

            for feiertag_name, info in daten.items():
                rows.append({
                    "datum": info["datum"],
                    "name": feiertag_name,
                    "bundesland_kuerzel": kuerzel,
                    "bundesland_name": name,
                    "hinweis": info.get("hinweis", ""),
                })

    df = pd.DataFrame(rows)
    df["datum"] = pd.to_datetime(df["datum"])
    df = df.sort_values(["datum", "bundesland_kuerzel"]).reset_index(drop=True)

    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/feiertage.csv", index=False)

    print(f"✅ {len(df)} Einträge gespeichert → data/feiertage.csv")
    print(f"   Zeitraum: {START_JAHR}–{end_jahr}")

    # Outputs für GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"eintraege={len(df)}\n")
            f.write(f"jahre={START_JAHR}-{end_jahr}\n")


# FIX: main() Guard — verhindert dass der API-Abruf beim Import ausgeführt wird
if __name__ == "__main__":
    main()