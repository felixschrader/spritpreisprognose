# energiesteuer.py

import pandas as pd
import os

### Zeitraum für Machine-Learning
### 08.06.2014 - 31.12.2025

# Energiesteuer-Festsätze nach §2 Abs.1 EnergieStG
# Tankrabatt-Periode: abgesenkte Steuersätze nach EnergieStSenkG
STEUERSAETZE = [
    {
        "datum_start":      "2014-06-08",
        "datum_ende":       "2022-05-31",
        "bezeichnung":      "Normalsatz",
        "benzin_ct":        65.45,
        "diesel_ct":        47.04,
        "quelle":           "EnergieStG §2 Abs.1 Nr.1+4",
    },
    {
        "datum_start":      "2022-06-01",
        "datum_ende":       "2022-08-31",
        "bezeichnung":      "Tankrabatt (EnergieStSenkG)",
        "benzin_ct":        35.90,
        "diesel_ct":        33.00,
        "quelle":           "BGBl. I 2022 S.698 / EnergieStSenkG",
    },
    {
        "datum_start":      "2022-09-01",
        "datum_ende":       "2025-12-31",
        "bezeichnung":      "Normalsatz",
        "benzin_ct":        65.45,
        "diesel_ct":        47.04,
        "quelle":           "EnergieStG §2 Abs.1 Nr.1+4",
    },
]


def generiere_energiesteuer() -> pd.DataFrame:
    """
    Erzeugt eine tägliche Zeitreihe der Energiesteuer auf Kraftstoffe.

    Die Energiesteuer ist ein fixer Betrag pro Liter — kein Marktpreis.
    Sie ändert sich nur bei gesetzlichen Eingriffen. Im Projektzeitraum
    gab es genau eine Änderung: den Tankrabatt 2022 (Juni–August).

    Spalten:
        date                  — Datum
        energiesteuer_benzin  — Energiesteuer Benzin in ct/L
        energiesteuer_diesel  — Energiesteuer Diesel in ct/L
        ist_tankrabatt        — 1 während des Tankrabatts, sonst 0
    """
    tage = pd.date_range(start="2014-06-08", end="2025-12-31", freq="D")
    df = pd.DataFrame({"date": tage})
    df["energiesteuer_benzin"] = None
    df["energiesteuer_diesel"] = None
    df["ist_tankrabatt"]       = 0

    for s in STEUERSAETZE:
        mask = (df["date"] >= s["datum_start"]) & (df["date"] <= s["datum_ende"])
        df.loc[mask, "energiesteuer_benzin"] = s["benzin_ct"]
        df.loc[mask, "energiesteuer_diesel"] = s["diesel_ct"]
        if s["bezeichnung"] == "Tankrabatt (EnergieStSenkG)":
            df.loc[mask, "ist_tankrabatt"] = 1

    df["energiesteuer_benzin"] = df["energiesteuer_benzin"].astype(float)
    df["energiesteuer_diesel"] = df["energiesteuer_diesel"].astype(float)

    return df


if __name__ == "__main__":
    df = generiere_energiesteuer()
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/energiesteuer.csv", index=False)
    print(f"✅ {len(df)} Tage gespeichert → data/energiesteuer.csv")
    print(f"   Normalsatz Benzin:   {df[df['ist_tankrabatt']==0]['energiesteuer_benzin'].iloc[0]} ct/L")
    print(f"   Normalsatz Diesel:   {df[df['ist_tankrabatt']==0]['energiesteuer_diesel'].iloc[0]} ct/L")
    print(f"   Tankrabatt-Tage:     {df['ist_tankrabatt'].sum()}")
    print(df[df["ist_tankrabatt"] == 1][["date", "energiesteuer_benzin", "energiesteuer_diesel"]].head(3))