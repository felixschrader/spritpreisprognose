# wetter_koeln.py
# Lädt tägliche Wetterdaten der Station Köln/Bonn Flughafen (DWD ID 02667)
# vom DWD CDC OpenData Server — kostenlos, kein API-Key nötig.
#
# Quelle: Deutscher Wetterdienst (DWD) CDC OpenData
# Station: Köln/Bonn Flughafen, Stations-ID 02667, 91m ü.NN
# Koordinaten: 50.8645°N, 7.1575°E
#
# Warum nur eine Station statt Deutschlanddurchschnitt?
#   Das Projekt fokussiert auf Tankstellen im Kölner Umkreis (5km-Radius).
#   Lokale Wetterdaten sind für die Modellierung ausreichend — die Temperatur-
#   unterschiede innerhalb Deutschlands sind für die Saisonalität irrelevant.
#   Köln/Bonn Flughafen ist die nächstgelegene offizielle DWD-Klimastation
#   und damit ein valider Proxy für das Kölner Stadtgebiet.
#
# Warum Temperatur als Feature?
#   Temperatur ist ein Proxy für saisonale Nachfrageschwankungen:
#   - Kälte → erhöhter Dieselverbrauch (Heizöl-Effekt, Kurzstrecken statt Fahrrad)
#   - Sommerhitze → erhöhter Ferienreiseverkehr → höhere Benzinnachfrage
#   - Niederschlag → kurzfristig mehr PKW-Nutzung statt ÖPNV/Fahrrad
#   Die Werte können für das ML-Modell normalisiert werden (z.B. z-score
#   oder Min-Max-Skalierung), um sie mit anderen Features vergleichbar zu machen.
#
# Spalten im Output:
#   date             — Datum
#   temp_avg         — Tagesmitteltemperatur (°C)
#   temp_min         — Tagesminimum (°C)
#   temp_max         — Tagesmaximum (°C)
#   niederschlag_mm  — Niederschlagssumme (mm)
#   sonnenstunden    — Sonnenscheindauer (h)
#
# Technische Besonderheit — dynamische URL:
#   Der DWD stellt Daten in zwei Endpunkten bereit:
#   - historical: geprüfte Daten von 1957 bis ca. Jahresende des Vorjahres
#                 Dateiname enthält Enddatum und ändert sich jährlich (_hist.zip)
#   - recent:     vorläufige Daten des laufenden Jahres (_akt.zip)
#   Die historical-URL wird dynamisch aus dem Directory-Listing geparst,
#   damit kein manuelles Update bei jährlichen DWD-Änderungen nötig ist.

import requests
import pandas as pd
import zipfile
import io
import os
import re
from datetime import datetime
import pytz

STATION_ID        = "02667"
STATION_ID_PADDED = STATION_ID.zfill(5)
CSV_PATH          = "data/wetter_koeln.csv"

BASE             = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl"
INDEX_HISTORICAL = f"{BASE}/historical/"
URL_RECENT       = f"{BASE}/recent/tageswerte_KL_{STATION_ID_PADDED}_akt.zip"


def get_historical_url() -> str | None:
    """
    Ermittelt die aktuelle URL der historical-ZIP dynamisch aus dem
    DWD-Directory-Listing. Der Dateiname endet auf _hist.zip und enthält
    das Enddatum — ändert sich jährlich wenn DWD die Datei aktualisiert.
    """
    r = requests.get(INDEX_HISTORICAL, timeout=10)
    r.raise_for_status()

    # Dateiname hat Format: tageswerte_KL_02667_YYYYMMDD_YYYYMMDD_hist.zip
    match = re.search(
        rf'tageswerte_KL_{STATION_ID_PADDED}_\d{{8}}_\d{{8}}_hist\.zip',
        r.text
    )
    if match:
        return f"{INDEX_HISTORICAL}{match.group(0)}"

    print("⚠️  Konnte historical-URL nicht aus DWD-Index ermitteln.")
    return None


def lade_dwd_zip(url: str) -> pd.DataFrame | None:
    """
    Lädt eine DWD-ZIP-Datei, extrahiert die Messdaten-CSV und gibt
    einen DataFrame zurück.
    DWD-ZIPs enthalten immer eine Datei die mit 'produkt_' beginnt.
    """
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️  Konnte {url} nicht laden: {e}")
        return None

    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        datendatei = next(
            (name for name in z.namelist() if name.startswith("produkt_")),
            None
        )
        if not datendatei:
            print(f"⚠️  Keine Datendatei in ZIP gefunden: {url}")
            return None

        with z.open(datendatei) as f:
            df = pd.read_csv(f, sep=";", encoding="latin1")

    return df


def verarbeite_dwd_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereinigt einen rohen DWD-DataFrame:
    - Spaltenname-Leerzeichen entfernen (DWD-Eigenheit)
    - Relevante Spalten umbenennen und behalten
    - Datum parsen (DWD-Format: YYYYMMDD als Integer)
    - DWD-Fehlwert -999 durch NaN ersetzen
    """
    df.columns = [c.strip() for c in df.columns]

    rename = {
        "MESS_DATUM": "date",
        "TMK":        "temp_avg",
        "TNK":        "temp_min",
        "TXK":        "temp_max",
        "RSK":        "niederschlag_mm",
        "SDK":        "sonnenstunden",
    }

    verfuegbare = {k: v for k, v in rename.items() if k in df.columns}
    df = df[list(verfuegbare.keys())].rename(columns=verfuegbare)

    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")

    # DWD verwendet -999 als Fehlwert → NaN
    for col in ["temp_avg", "temp_min", "temp_max", "niederschlag_mm", "sonnenstunden"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(df[col] != -999.0)

    return df.sort_values("date").reset_index(drop=True)


def update_wetter() -> dict:
    """
    Aktualisiert die Wetter-CSV.

    Lädt historical (1957–Vorjahr) + recent (laufendes Jahr), merged beides
    und hängt nur neue Tage an die bestehende CSV an.
    """
    os.makedirs("data", exist_ok=True)

    print("🌤️  Ermittle DWD historical-URL...")
    url_hist = get_historical_url()
    if url_hist:
        print(f"   → {url_hist.split('/')[-1]}")

    df_hist = lade_dwd_zip(url_hist) if url_hist else None
    print("🌤️  Lade DWD recent...")
    df_rec = lade_dwd_zip(URL_RECENT)

    if df_hist is None and df_rec is None:
        print("❌ Keine DWD-Daten verfügbar.")
        return {}

    teile = []
    if df_hist is not None:
        teile.append(verarbeite_dwd_df(df_hist))
    if df_rec is not None:
        teile.append(verarbeite_dwd_df(df_rec))

    df_neu = (
        pd.concat(teile, ignore_index=True)
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Auf Projektzeitraum ab 2014 filtern — ältere Daten nicht nötig
    df_neu = df_neu[df_neu["date"] >= "2014-01-01"]

    if os.path.exists(CSV_PATH):
        df_existing = pd.read_csv(CSV_PATH, parse_dates=["date"])
        last_ts = df_existing["date"].max()
        df_append = df_neu[df_neu["date"] > last_ts]

        if df_append.empty:
            print("ℹ️  Wetter: keine neuen Daten.")
            df = df_existing
        else:
            df = (
                pd.concat([df_existing, df_append], ignore_index=True)
                .drop_duplicates(subset=["date"])
                .sort_values("date")
                .reset_index(drop=True)
            )
            print(f"✅ DWD Köln/Bonn: {len(df_append)} neue Tage (gesamt: {len(df)})")
    else:
        df = df_neu
        print(f"✅ DWD Köln/Bonn: {len(df)} Tage "
              f"({df['date'].iloc[0].date()} – {df['date'].iloc[-1].date()})")

    df.to_csv(CSV_PATH, index=False)
    print(f"📄 CSV gespeichert: {CSV_PATH}")

    last_temp = float(df["temp_avg"].dropna().iloc[-1])
    berlin = pytz.timezone("Europe/Berlin")

    stats = {
        "last_temp": last_temp,
        "last_date": df["date"].iloc[-1].strftime("%d.%m.%Y"),
        "updated":   datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows":      len(df),
    }

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_temp={stats['last_temp']}\n")
            f.write(f"updated={stats['updated']}\n")
            f.write(f"rows={stats['rows']}\n")

    return stats


if __name__ == "__main__":
    stats = update_wetter()
    if stats:
        print(f"🌡️  Köln/Bonn: {stats['last_temp']:.1f}°C "
              f"(Stand: {stats['last_date']}) | {stats['rows']} Tage")