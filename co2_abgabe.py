# co2_abgabe.py
# Erstellt und aktualisiert eine tägliche CO2-Abgabe-Zeitreihe seit 01.01.2014.
#
# Quelle: Brennstoffemissionshandelsgesetz (BEHG), DEHSt, EEX
# Kostenlos, kein API-Key nötig.
#
# Hintergrund — warum CO2-Abgabe als Feature?
#   Die CO2-Abgabe (national: BEHG / nEHS) ist ein direkt auf den Kraftstoffpreis
#   aufgeschlagener Fixbetrag. Sie ist kein Marktpreis, sondern eine staatlich
#   geregelte Steuerkomponente, die sich jährlich ändert. Als Feature im ML-Modell
#   erklärt sie einen Teil der absoluten Preisniveauverschiebungen seit 2021
#   — insbesondere den Sprung von 2020 auf 2021 (+7 ct/L Benzin) und die
#   jährlichen Erhöhungen bis 2025.
#
# Phasen:
#   2014–2020  Keine CO2-Abgabe auf Kraftstoffe (0 €/t)
#   2021–2025  BEHG Festpreisphase (gesetzlich fixiert, jährlich steigend)
#   2026       Preiskorridor 55–65 €/t, gesetzlicher Mittelwert = 60 €/t
#              (DEHSt: "maßgeblicher Preis 2026 = 60 Euro", CO2KostAufG §4)
#              Versteigerungen an der EEX starten erst Juli 2026 —
#              bis dahin gilt der gesetzliche Mittelwert als Planungsgröße.
#              Nach jeder wöchentlichen Auktion (montags, EEX Leipzig) wird
#              der tatsächliche Auktionspreis von der DEHSt veröffentlicht.
#              Das Skript scrapt diese Ergebnisse und überschreibt den Planwert.
#   2027+      Übergang zu EU-ETS 2, marktbasiert — wird ergänzt wenn bekannt.
#
# Umrechnungsformel (netto, ohne MwSt):
#   Benzin: CO2_preis_eur_t × 2.3722 kg_CO2/L ÷ 1000 = ct/L
#   Diesel: CO2_preis_eur_t × 2.6440 kg_CO2/L ÷ 1000 = ct/L
#   (Emissionsfaktoren nach EBeV 2030, Anlage 2)
#   Brutto (+19% MwSt): ct/L × 1.19
#
# Spalten im Output (data/co2_abgabe.csv):
#   date                    — Datum
#   co2_preis_eur_t         — CO2-Preis in €/t (Basis für Umrechnung)
#   co2_benzin_ct_netto     — Aufschlag Benzin in ct/L (ohne MwSt)
#   co2_diesel_ct_netto     — Aufschlag Diesel in ct/L (ohne MwSt)
#   co2_benzin_ct_brutto    — Aufschlag Benzin in ct/L (inkl. 19% MwSt)
#   co2_diesel_ct_brutto    — Aufschlag Diesel in ct/L (inkl. 19% MwSt)
#   quelle                  — Datenquelle (BEHG/DEHSt/EEX)
#   ist_schaetzwert         — True wenn Planwert, False wenn Festpreis oder Auktionspreis

import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, date
import os
import re

CSV_PATH = "data/co2_abgabe.csv"

# Emissionsfaktoren nach EBeV 2030 Anlage 2 (kg CO2 pro Liter)
EF_BENZIN = 2.3722
EF_DIESEL = 2.6440
MWST      = 1.19


# =============================================================================
# Festpreise 2014–2025 (statisch, gesetzlich fixiert)
# Quelle: BEHG §10 Abs.2, Stand 14.01.2026
# =============================================================================

FESTPREISE = [
    # (datum_start, datum_ende_inkl, preis_eur_t, quelle, ist_schaetzwert)
    ("2014-01-01", "2020-12-31",  0.00, "vor BEHG",                         False),
    ("2021-01-01", "2021-12-31", 25.00, "BEHG §10 Abs.2 Festpreis",         False),
    ("2022-01-01", "2022-12-31", 30.00, "BEHG §10 Abs.2 Festpreis",         False),
    ("2023-01-01", "2023-12-31", 30.00, "BEHG §10 Abs.2 Festpreis",         False),
    ("2024-01-01", "2024-12-31", 45.00, "BEHG §10 Abs.2 Festpreis",         False),
    ("2025-01-01", "2025-12-31", 55.00, "BEHG §10 Abs.2 Festpreis",         False),
    # 2026: gesetzlicher Mittelwert des Korridors (55–65€), DEHSt CO2KostAufG §4
    # Wird durch tatsächliche Auktionspreise überschrieben sobald verfügbar
    ("2026-01-01", "2026-12-31", 60.00, "DEHSt Planwert (Korridor 55–65€)", True),
]


def preis_zu_ct(preis_eur_t: float) -> dict:
    """Rechnet €/t CO2 in ct/L Kraftstoff um — netto und brutto."""
    benzin_netto = round(preis_eur_t * EF_BENZIN / 10, 4)   # ÷1000 × 100 = ÷10
    diesel_netto = round(preis_eur_t * EF_DIESEL / 10, 4)
    return {
        "co2_benzin_ct_netto":  benzin_netto,
        "co2_diesel_ct_netto":  diesel_netto,
        "co2_benzin_ct_brutto": round(benzin_netto * MWST, 4),
        "co2_diesel_ct_brutto": round(diesel_netto * MWST, 4),
    }


def generiere_festpreis_reihe() -> pd.DataFrame:
    """
    Erzeugt eine tägliche Zeitreihe der Festpreise von 2014 bis Ende 2026.
    Jeder Tag bekommt den für ihn gültigen CO2-Preis.
    """
    rows = []
    for start_str, ende_str, preis, quelle, schaetzwert in FESTPREISE:
        tage = pd.date_range(start=start_str, end=ende_str, freq="D")
        ct = preis_zu_ct(preis)
        for tag in tage:
            rows.append({
                "date":                 tag.date(),
                "co2_preis_eur_t":      preis,
                "quelle":               quelle,
                "ist_schaetzwert":      schaetzwert,
                **ct,
            })
    return pd.DataFrame(rows)


# =============================================================================
# DEHSt-Auktionsergebnisse scrapen (ab Juli 2026)
# =============================================================================

DEHST_URL = "https://www.dehst.de/DE/Themen/nEHS/Verkauf-Versteigerung/verkauf-versteigerung_node.html"


def scrape_auktionsergebnisse() -> pd.DataFrame:
    """
    Scrapt die DEHSt-Webseite nach veröffentlichten Auktionsergebnissen.
    Die DEHSt veröffentlicht nach jeder Montagsauktion (EEX Leipzig, 13–15 Uhr)
    den Clearing-Preis. Das Format auf der Webseite ist nicht standardisiert —
    diese Funktion parst Tabellen und sucht nach Datumsangaben mit Preisen.

    Gibt einen DataFrame mit tatsächlichen Auktionspreisen zurück,
    oder einen leeren DataFrame wenn noch keine Ergebnisse vorliegen.
    """
    try:
        r = requests.get(DEHST_URL, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️  DEHSt nicht erreichbar: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(r.text, "html.parser")
    rows = []

    # Tabellen auf der Seite durchsuchen
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            zellen = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(zellen) < 2:
                continue

            # Datumsformat suchen: z.B. "07.07.2026" oder "2026-07-07"
            datum_match = re.search(r'(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})', zellen[0])
            # Preis suchen: z.B. "62,50" oder "62.50"
            preis_match = re.search(r'(\d{2,3}[.,]\d{1,2})', " ".join(zellen[1:]))

            if datum_match and preis_match:
                try:
                    datum_str = datum_match.group(1)
                    if "." in datum_str:
                        tag = datetime.strptime(datum_str, "%d.%m.%Y").date()
                    else:
                        tag = datetime.strptime(datum_str, "%Y-%m-%d").date()

                    preis = float(preis_match.group(1).replace(",", "."))

                    # Plausibilitätscheck: nur 2026+ und innerhalb des Korridors
                    if tag.year >= 2026 and 50 <= preis <= 70:
                        ct = preis_zu_ct(preis)
                        rows.append({
                            "date":            tag,
                            "co2_preis_eur_t": preis,
                            "quelle":          "EEX Auktionsergebnis (DEHSt)",
                            "ist_schaetzwert": False,
                            **ct,
                        })
                except (ValueError, AttributeError):
                    continue

    if rows:
        print(f"✅ {len(rows)} Auktionsergebnisse von DEHSt geparst")
    else:
        print("ℹ️  Noch keine Auktionsergebnisse auf DEHSt-Seite (Versteigerungen starten Juli 2026)")

    return pd.DataFrame(rows)


# =============================================================================
# Hauptfunktion
# =============================================================================

def update_co2_abgabe() -> dict:
    """
    Erstellt oder aktualisiert die tägliche CO2-Abgabe-CSV.

    Logik:
    1. Festpreis-Zeitreihe 2014–2026 generieren (statisch)
    2. Auktionsergebnisse von DEHSt scrapen (ab Juli 2026)
    3. Auktionsergebnisse überschreiben die Schätzwerte für die jeweiligen Tage
    4. Nur neue Tage an bestehende CSV anhängen
    """
    Path("data").mkdir(exist_ok=True)

    # Festpreis-Basis generieren
    df_basis = generiere_festpreis_reihe()

    # Auktionsergebnisse holen und Schätzwerte überschreiben
    df_auktion = scrape_auktionsergebnisse()
    if not df_auktion.empty:
        # Auktionspreise gelten für die ganze Woche bis zur nächsten Auktion
        # (Wochenweise Fortschreibung des letzten bekannten Auktionspreises)
        auktion_dict = {row["date"]: row for _, row in df_auktion.iterrows()}
        letzter_preis = None

        for idx, row in df_basis.iterrows():
            tag = row["date"]
            if tag in auktion_dict:
                letzter_preis = auktion_dict[tag]
            if letzter_preis is not None and row["ist_schaetzwert"]:
                df_basis.at[idx, "co2_preis_eur_t"]     = letzter_preis["co2_preis_eur_t"]
                df_basis.at[idx, "co2_benzin_ct_netto"]  = letzter_preis["co2_benzin_ct_netto"]
                df_basis.at[idx, "co2_diesel_ct_netto"]  = letzter_preis["co2_diesel_ct_netto"]
                df_basis.at[idx, "co2_benzin_ct_brutto"] = letzter_preis["co2_benzin_ct_brutto"]
                df_basis.at[idx, "co2_diesel_ct_brutto"] = letzter_preis["co2_diesel_ct_brutto"]
                df_basis.at[idx, "quelle"]               = letzter_preis["quelle"]
                df_basis.at[idx, "ist_schaetzwert"]      = False

    df_basis["date"] = pd.to_datetime(df_basis["date"])

    # An bestehende CSV anhängen oder neu erstellen
    if os.path.exists(CSV_PATH):
        df_existing = pd.read_csv(CSV_PATH, parse_dates=["date"])
        last_ts = df_existing["date"].max()
        df_append = df_basis[df_basis["date"] > last_ts]

        if df_append.empty:
            print("ℹ️  CO2-Abgabe: keine neuen Tage.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append], ignore_index=True)
            df = df.sort_values("date").reset_index(drop=True)
            print(f"✅ CO2-Abgabe: {len(df_append)} neue Tage angehängt (gesamt: {len(df)})")
    else:
        df = df_basis.sort_values("date").reset_index(drop=True)
        print(f"✅ CO2-Abgabe: {len(df)} Tage erstellt "
              f"({df['date'].iloc[0].date()} – {df['date'].iloc[-1].date()})")

    df.to_csv(CSV_PATH, index=False)
    print(f"📄 CSV gespeichert: {CSV_PATH}")

    last_preis = float(df["co2_preis_eur_t"].iloc[-1])
    last_ct    = float(df["co2_benzin_ct_brutto"].iloc[-1])

    stats = {
        "last_preis_eur_t":      last_preis,
        "last_benzin_ct_brutto": last_ct,
        "rows":                  len(df),
    }

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_preis={last_preis}\n")
            f.write(f"last_ct={last_ct}\n")
            f.write(f"rows={stats['rows']}\n")

    return stats


if __name__ == "__main__":
    stats = update_co2_abgabe()
    if stats:
        print(f"🌿 CO2-Abgabe: {stats['last_preis_eur_t']:.2f} €/t "
              f"= {stats['last_benzin_ct_brutto']:.2f} ct/L Benzin brutto "
              f"| {stats['rows']} Tage")