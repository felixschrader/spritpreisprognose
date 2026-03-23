# =============================================================================
# eur_usd_rate.py
# Lädt tägliche EUR/USD Wechselkurse von der Europäischen Zentralbank (EZB)
# und speichert sie als CSV.
#
# Quelle: EZB Statistical Data Warehouse (SDW) API — kostenlos, kein API-Key
# Frequenz: täglich (Handelstage), offizieller EZB-Referenzkurs
# Einheit: USD pro 1 EUR (z.B. 1.15 = 1 Euro kostet 1,15 Dollar)
#
# Warum EUR/USD als Feature?
#   Rohöl wird global in USD gehandelt. Wenn der Euro stärker wird,
#   wird Öl für europäische Käufer günstiger — das beeinflusst Tankstellenpreise.
# =============================================================================

import requests
import pandas as pd
import io
import os
from datetime import datetime
import pytz


# =============================================================================
# Konfiguration
# =============================================================================

CSV_PATH = "data/eur_usd_rate.csv"

# EZB API-Endpunkt:
# D = Daily, USD.EUR = USD zu EUR, SP00 = Spot-Kurs, A = Average
EZB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata"


# =============================================================================
# DATEN HOLEN
# =============================================================================

def fetch_eur_usd() -> pd.DataFrame:
    """
    Lädt alle verfügbaren EUR/USD Tageskurse von der EZB API.
    Die EZB liefert immer den kompletten historischen Datensatz in einem Request.
    """
    r = requests.get(EZB_URL, timeout=10)
    r.raise_for_status()

    df = pd.read_csv(io.StringIO(r.text))
    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()
    df.columns = ["date", "eur_usd"]
    df["date"] = pd.to_datetime(df["date"])
    df["eur_usd"] = pd.to_numeric(df["eur_usd"], errors="coerce")
    df = df.sort_values("date").dropna(subset=["eur_usd"])
    df = df.set_index("date")
    df.index.name = "period"

    return df


# =============================================================================
# CSV AKTUALISIEREN
# =============================================================================

def update_eur_usd() -> dict:
    """
    Aktualisiert die EUR/USD CSV — hängt nur neue Daten an, überschreibt nichts.

    Logik:
    - CSV existiert bereits → nur Zeilen neuer als letzter Datenpunkt anhängen
    - CSV existiert noch nicht → kompletter Datensatz wird gespeichert
    """
    os.makedirs("data", exist_ok=True)

    try:
        df_new = fetch_eur_usd()
    except Exception as e:
        print(f"❌ EZB-Abruf fehlgeschlagen: {e}")
        return {}

    if os.path.exists(CSV_PATH):
        df_existing = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]
        df_append = df_new[df_new.index > last_ts]

        if df_append.empty:
            print("ℹ️  EUR/USD: keine neuen Daten.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            print(f"✅ EZB EUR/USD: {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        df = df_new
        print(f"✅ EZB EUR/USD: {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    df.to_csv(CSV_PATH)
    print(f"📄 CSV gespeichert: {CSV_PATH}")

    last = float(df["eur_usd"].iloc[-1])
    # FIX: Längencheck vor iloc[-2] — schlägt sonst fehl wenn nur 1 Zeile vorhanden
    prev = float(df["eur_usd"].iloc[-2]) if len(df) > 1 else last
    trend = "↑" if last > prev else ("↓" if last < prev else "→")
    berlin = pytz.timezone("Europe/Berlin")

    stats = {
        "last_rate": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_rate={stats['last_rate']}\n")
            f.write(f"trend={stats['trend']}\n")
            f.write(f"updated={stats['updated']}\n")

    return stats


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    stats = update_eur_usd()
    if stats:
        print(f"💱 EUR/USD: {stats['last_rate']:.4f} {stats['trend']} "
              f"(Stand: {stats['last_date']}) | aktualisiert: {stats['updated']} "
              f"| {stats['rows']} Zeilen")