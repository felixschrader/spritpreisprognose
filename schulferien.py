# schulferien.py
# Lädt alle deutschen Schulferien (2014 bis aktuelles Jahr + 2) nach Bundesland
# via OpenHolidays API (openholidaysapi.org) — kein API-Key nötig
#
# Wichtiger Hinweis zur API-Limitierung:
# Die API erlaubt maximal 3 Jahre pro Anfrage. Wir fragen daher
# jahresweise ab, um das Limit sicher einzuhalten.

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

# Alle 16 Bundesländer — nur Bundesland-Ebene, keine Städte (z.B. kein DE-BY-AU für Augsburg)
BUNDESLAENDER = {
    "DE-BB": "Brandenburg",
    "DE-BE": "Berlin",
    "DE-BW": "Baden-Württemberg",
    "DE-BY": "Bayern",
    "DE-HB": "Bremen",
    "DE-HE": "Hessen",
    "DE-HH": "Hamburg",
    "DE-MV": "Mecklenburg-Vorpommern",
    "DE-NI": "Niedersachsen",
    "DE-NW": "Nordrhein-Westfalen",
    "DE-RP": "Rheinland-Pfalz",
    "DE-SH": "Schleswig-Holstein",
    "DE-SL": "Saarland",
    "DE-SN": "Sachsen",
    "DE-ST": "Sachsen-Anhalt",
    "DE-TH": "Thüringen",
}

# Dynamischer Zeitraum: 2014 bis aktuelles Jahr + 2
START_JAHR = 2014
BASE_URL = "https://openholidaysapi.org/SchoolHolidays"


def main():
    end_jahr = datetime.now().year + 2
    rows = []

    for jahr in range(START_JAHR, end_jahr + 1):
        print(f"Lade {jahr}...")
        for code, name in BUNDESLAENDER.items():
            params = {
                "countryIsoCode": "DE",
                "subdivisionCode": code,
                "validFrom": f"{jahr}-01-01",
                "validTo": f"{jahr}-12-31",
                "languageIsoCode": "DE",
            }
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            daten = response.json()

            for eintrag in daten:
                # Ferienname extrahieren (deutschsprachig)
                ferienname = next(
                    (n["text"] for n in eintrag["name"] if n["language"] == "DE"),
                    eintrag["name"][0]["text"] if eintrag["name"] else ""
                )
                rows.append({
                    "datum_start": eintrag["startDate"],
                    "datum_ende": eintrag["endDate"],
                    "name": ferienname,
                    "bundesland_code": code,
                    "bundesland_name": name,
                })

    df = pd.DataFrame(rows)
    df["datum_start"] = pd.to_datetime(df["datum_start"])
    df["datum_ende"] = pd.to_datetime(df["datum_ende"])
    df = df.sort_values(["datum_start", "bundesland_code"]).reset_index(drop=True)

    # Duplikate entfernen — Ferien die über Jahresgrenzen gehen
    # werden durch die jahresweise Abfrage doppelt erfasst
    df = df.drop_duplicates(subset=["datum_start", "datum_ende", "bundesland_code"])
    df = df.reset_index(drop=True)

    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/schulferien.csv", index=False)

    print(f"✅ {len(df)} Einträge gespeichert → data/schulferien.csv")
    print(f"   Zeitraum: {START_JAHR}–{end_jahr}")

    # Outputs für GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"eintraege={len(df)}\n")
            f.write(f"jahre={START_JAHR}-{end_jahr}\n")


# FIX: main() Guard — verhindert dass der API-Abruf beim Import ausgeführt wird
if __name__ == "__main__":
    main()