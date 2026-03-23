# externe_effekte.py

import pandas as pd
import os

### Zeitraum für Machine-Learning
### 08.06.2014 - 31.12.2025

EREIGNISSE = [
    {
        "datum_start":   "2020-03-16",
        "datum_ende":    "2020-06-15",
        "ereignis":      "COVID-19 Lockdown",
        "typ":           "Nachfrageeinbruch",
        "effekt_benzin": "stark negativ",
        "effekt_diesel": "stark negativ",
        "quelle":        "Bundesregierung / RKI",
        "feature":       "ist_lockdown",
    },
    {
        "datum_start":   "2022-07-15",
        "datum_ende":    "2022-10-15",
        "ereignis":      "Rhein-Niedrigwasser",
        "typ":           "Logistik/Infrastruktur",
        "effekt_benzin": "neutral",
        "effekt_diesel": "+5 bis +8 ct/L",
        "quelle":        "RWI / ADAC",
        "feature":       "ist_niedrigwasser",
    },
]


def generiere_externe_effekte() -> pd.DataFrame:
    """
    Erzeugt eine tägliche Zeitreihe externer Ereignisse als binäre Features.

    Jedes Ereignis wird als eigene Spalte (0/1) kodiert.

    Returns:
        DataFrame mit date + einem binären Feature pro Ereignis
    """
    tage = pd.date_range(start="2014-06-08", end="2025-12-31", freq="D")
    df = pd.DataFrame({"date": tage})

    for e in EREIGNISSE:
        df[e["feature"]] = 0

    for e in EREIGNISSE:
        mask = (df["date"] >= e["datum_start"]) & (df["date"] <= e["datum_ende"])
        df.loc[mask, e["feature"]] = 1

    return df


if __name__ == "__main__":
    df = generiere_externe_effekte()
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/externe_effekte.csv", index=False)
    print(f"✅ {len(df)} Tage gespeichert → data/externe_effekte.csv")
    for e in EREIGNISSE:
        n = df[e["feature"]].sum()
        print(f"   {e['feature']}: {n} Tage ({e['datum_start']} – {e['datum_ende']})")