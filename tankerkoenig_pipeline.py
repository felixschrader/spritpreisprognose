# =============================================================================
# tankerkoenig_pipeline.py
#
# Verwaltet Tankerkönig-Preisdaten für beliebige Städte in einem
# einzigen Parquet — stadtübergreifend, UUID-basiert.
#
# Logik:
#   - data/tankstellen_preise.parquet    — alle Preise aller Städte
#   - data/tankstellen_stationen.parquet — Stammdaten aller enthaltenen Stationen
#
# Neue Stadt hinzufügen (lokal):
#   python3 tankerkoenig_pipeline.py --add-stadt berlin
#   → lädt History, fügt ins Parquet ein, pushen → Workflow updated automatisch
#
# Fortschreibung (lokal oder GitHub Actions):
#   python3 tankerkoenig_pipeline.py --update
#   → liest UUIDs aus bestehendem Parquet, lädt nur neue Daten nach
#
# Test:
#   python3 tankerkoenig_pipeline.py --add-stadt koeln --test
#
# Weitere Optionen:
#   --no-pull   kein git pull (Daten schon aktuell)
#   --workers N Anzahl CPU-Kerne
# =============================================================================

from pathlib import Path
from multiprocessing import Pool, cpu_count
from datetime import datetime
import argparse
import subprocess
import os
import gc

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Stadtdefinitionen — Referenzpunkt (lat/lon) + Radius in km
# Neue Stadt einfach hier eintragen, dann mit --add-stadt laden
# =============================================================================

STADT_CONFIGS: dict[str, dict] = {
    "koeln":      {"lat": 50.919537, "lon": 6.852624,  "radius_km": 5,  "label": "Köln (Aral Dürener Str. 407)"},
    "berlin":     {"lat": 52.520008, "lon": 13.404954, "radius_km": 15, "label": "Berlin"},
    "hamburg":    {"lat": 53.550341, "lon": 10.000654, "radius_km": 15, "label": "Hamburg"},
    "muenchen":   {"lat": 48.137154, "lon": 11.576124, "radius_km": 15, "label": "München"},
    "frankfurt":  {"lat": 50.110924, "lon": 8.682127,  "radius_km": 10, "label": "Frankfurt"},
    "stuttgart":  {"lat": 48.775846, "lon": 9.182932,  "radius_km": 10, "label": "Stuttgart"},
    "dusseldorf": {"lat": 51.227741, "lon": 6.773456,  "radius_km": 10, "label": "Düsseldorf"},
    "dortmund":   {"lat": 51.513587, "lon": 7.465298,  "radius_km": 10, "label": "Dortmund"},
    "essen":      {"lat": 51.455643, "lon": 7.011555,  "radius_km": 10, "label": "Essen"},
    "bremen":     {"lat": 53.079296, "lon": 8.801694,  "radius_km": 10, "label": "Bremen"},
    "leipzig":    {"lat": 51.339695, "lon": 12.373075, "radius_km": 10, "label": "Leipzig"},
    "nuernberg":  {"lat": 49.452030, "lon": 11.076750, "radius_km": 10, "label": "Nürnberg"},
}


# =============================================================================
# Konfiguration
# =============================================================================

DATA_ROOT    = Path(os.environ.get("TANKERKOENIG_DATA_ROOT", "/media/rex/6DFF-26FE/Tankerkoenig"))
STATIONS_CSV = DATA_ROOT / "stations" / "stations.csv"
PRICES_DIR   = DATA_ROOT / "prices"
OUTPUT_DIR   = Path("data")

OUT_PREISE    = OUTPUT_DIR / "tankstellen_preise.parquet"
OUT_STATIONEN = OUTPUT_DIR / "tankstellen_stationen.parquet"

TANKERKOENIG_USER = os.environ.get("TANKERKOENIG_USER", "")
TANKERKOENIG_KEY  = os.environ.get("TANKERKOENIG_KEY", "")
TANKERKOENIG_URL  = (
    f"https://{TANKERKOENIG_USER}:{TANKERKOENIG_KEY}"
    f"@data.tankerkoenig.de/tankerkoenig-organization/tankerkoenig-data.git"
)

COLS      = ["date", "station_uuid", "diesel", "e5", "e10"]
PREIS_MIN = 0.50
PREIS_MAX = 3.50
TEST_CSV_ANZAHL = 5

_station_uuids: set = set()


# =============================================================================
# Schritt 0: git pull
# =============================================================================

def pull_tankerkoenig():
    """Aktualisiert lokale Tankerkönig-Daten per git pull."""
    if not TANKERKOENIG_USER or not TANKERKOENIG_KEY:
        raise EnvironmentError(
            "TANKERKOENIG_USER oder TANKERKOENIG_KEY nicht gesetzt.\n"
            "Lokal: in .env eintragen.\n"
            "GitHub Actions: als Repository Secret hinterlegen."
        )

    print("🔄 Tankerkönig-Daten aktualisieren (git pull)...")
    result = subprocess.run(
        ["git", "pull", TANKERKOENIG_URL],
        cwd=str(DATA_ROOT),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"git pull fehlgeschlagen:\n{result.stderr}")

    output = result.stdout.replace(TANKERKOENIG_KEY, "***").replace(TANKERKOENIG_USER, "***")
    print(f"✅ {output.strip()}")


# =============================================================================
# Schritt 1: Stationen laden
# =============================================================================

def haversine(lat1: float, lon1: float, lat2, lon2) -> "pd.Series":
    """
    Berechnet die Entfernung in km zwischen zwei GPS-Koordinaten.
    Haversine-Formel: berücksichtigt die Erdkrümmung.
    lat2/lon2 können pandas Series sein (vektorisiert).
    """
    import numpy as np
    R = 6371  # Erdradius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def lade_stationen_fuer_stadt(stadtname: str) -> pd.DataFrame:
    """
    Lädt alle Tankstellen im Umkreis des Referenzpunkts der Stadt.
    Filter: Haversine-Distanz <= radius_km.
    """
    config = STADT_CONFIGS[stadtname]
    ref_lat, ref_lon, radius_km = config["lat"], config["lon"], config["radius_km"]

    stationen = pd.read_csv(STATIONS_CSV, dtype={"post_code": str, "uuid": str})

    stationen["distanz_km"] = haversine(
        ref_lat, ref_lon,
        stationen["latitude"], stationen["longitude"]
    )

    result = stationen[stationen["distanz_km"] <= radius_km].copy()
    result["stadt"] = stadtname

    print(f"   Referenzpunkt: {config['label']} ({ref_lat}, {ref_lon}), Radius: {radius_km} km")
    print(f"   {len(result)} Stationen im Umkreis gefunden")

    return result


# =============================================================================
# Schritt 2: Einzelne CSV verarbeiten (parallel)
# =============================================================================

def init_worker(uuids: set):
    """Setzt Stations-UUIDs als globale Variable in jedem Worker-Prozess."""
    global _station_uuids
    _station_uuids = uuids


def verarbeite_csv(csv_pfad: str) -> pd.DataFrame | None:
    """
    Lädt eine einzelne Tages-CSV, filtert sofort auf relevante Stationen.
    Wird parallel von mehreren Worker-Prozessen aufgerufen.
    """
    try:
        df = pd.read_csv(
            csv_pfad,
            usecols=COLS,
            dtype={
                "station_uuid": str,
                "diesel": "float32",
                "e5": "float32",
                "e10": "float32",
            },
        )
        df = df[df["station_uuid"].isin(_station_uuids)]
        return df if not df.empty else None
    except Exception:
        return None


# =============================================================================
# Schritt 3: CSVs parallel verarbeiten
# =============================================================================

def lade_preise(
    station_uuids: set,
    ab_datum: str | None = None,
    workers: int = cpu_count(),
    test: bool = False,
) -> pd.DataFrame:
    """Sammelt alle Preis-CSVs und verarbeitet sie parallel."""
    alle_csvs = sorted(PRICES_DIR.glob("**/*.csv"))

    if ab_datum:
        alle_csvs = [
            p for p in alle_csvs
            if f"{p.parts[-3]}-{p.parts[-2]}" >= ab_datum
        ]

    if test:
        alle_csvs = alle_csvs[:TEST_CSV_ANZAHL]
        print(f"\n🧪 Testmodus: nur {len(alle_csvs)} CSV-Dateien")
    else:
        print(f"\n💰 {len(alle_csvs):,} CSV-Dateien zu verarbeiten")

    print(f"   CPU-Kerne: {workers}")
    print(f"   Tipp: Abbrechen mit Strg+C\n")

    ergebnisse = []

    with Pool(
        processes=workers,
        initializer=init_worker,
        initargs=(station_uuids,),
    ) as pool:
        for df in tqdm(
            pool.imap_unordered(verarbeite_csv, [str(p) for p in alle_csvs]),
            total=len(alle_csvs),
            desc="Preisdaten laden",
            unit="CSV",
            colour="green",
        ):
            if df is not None:
                ergebnisse.append(df)

    if not ergebnisse:
        raise ValueError("Keine Preisdaten gefunden.")

    print(f"\n🔀 {len(ergebnisse):,} Dateien mit Daten — zusammenführen...")
    df = pd.concat(ergebnisse, ignore_index=True)
    del ergebnisse
    gc.collect()

    print("🕐 Zeitzone konvertieren...")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["date"] = df["date"].dt.tz_convert("Europe/Berlin").dt.tz_localize(None)

    for col in ["diesel", "e5", "e10"]:
        df[col] = df[col].where(df[col].between(PREIS_MIN, PREIS_MAX))

    df = (
        df.drop_duplicates(subset=["date", "station_uuid"])
        .sort_values(["station_uuid", "date"])
        .reset_index(drop=True)
    )

    return df


# =============================================================================
# Modi
# =============================================================================

def add_stadt(stadtname: str, workers: int, test: bool, no_pull: bool):
    """
    Lädt komplette History für eine neue Stadt und fügt sie ins Parquet ein.
    Bereits vorhandene UUIDs werden nicht doppelt gespeichert.
    """
    if stadtname not in STADT_CONFIGS:
        raise ValueError(
            f"'{stadtname}' nicht in STADT_CONFIGS.\n"
            f"Verfügbar: {', '.join(sorted(STADT_CONFIGS.keys()))}"  # FIX: war STADT_PLZ_PREFIXES
        )

    print(f"\n📍 Lade Stationen für {stadtname.capitalize()}...")
    neue_stationen = lade_stationen_fuer_stadt(stadtname)
    print(f"✅ {len(neue_stationen)} Stationen gefunden")

    neue_uuids = set(neue_stationen["uuid"])
    if OUT_PREISE.exists():
        df_existing = pd.read_parquet(OUT_PREISE, columns=["station_uuid"])
        bereits_drin = neue_uuids & set(df_existing["station_uuid"].unique())
        if bereits_drin:
            print(f"ℹ️  {len(bereits_drin)} Stationen bereits im Parquet — werden übersprungen")
            neue_uuids -= bereits_drin
        del df_existing
        gc.collect()

    if not neue_uuids:
        print("ℹ️  Alle Stationen bereits vorhanden — nichts zu tun.")
        return

    if not no_pull and not test:
        pull_tankerkoenig()

    df_neu = lade_preise(neue_uuids, workers=workers, test=test)

    OUTPUT_DIR.mkdir(exist_ok=True)
    if OUT_STATIONEN.exists():
        df_stat_existing = pd.read_parquet(OUT_STATIONEN)
        neue_stationen_gefiltert = neue_stationen[
            neue_stationen["uuid"].isin(neue_uuids)
        ]
        df_stationen = pd.concat([df_stat_existing, neue_stationen_gefiltert], ignore_index=True)
        df_stationen = df_stationen.drop_duplicates(subset=["uuid"])
    else:
        df_stationen = neue_stationen

    df_stationen.to_parquet(OUT_STATIONEN, index=False)
    print(f"📄 Stationen gespeichert: {OUT_STATIONEN} ({len(df_stationen)} gesamt)")

    if OUT_PREISE.exists() and not test:
        df_existing = pd.read_parquet(OUT_PREISE)
        df_gesamt = pd.concat([df_existing, df_neu], ignore_index=True)
        df_gesamt = (
            df_gesamt.drop_duplicates(subset=["date", "station_uuid"])
            .sort_values(["station_uuid", "date"])
            .reset_index(drop=True)
        )
        del df_existing
        gc.collect()
    else:
        df_gesamt = df_neu

    out_pfad = OUTPUT_DIR / "tankstellen_preise_test.parquet" if test else OUT_PREISE
    df_gesamt.to_parquet(out_pfad, index=False)

    _print_summary(df_gesamt, out_pfad)


def update(workers: int, test: bool, no_pull: bool):
    """
    Fortschreibung: liest alle UUIDs aus dem Parquet und lädt neue Daten nach.
    Funktioniert für alle enthaltenen Städte gleichzeitig.
    """
    if not OUT_PREISE.exists():
        raise FileNotFoundError(
            f"{OUT_PREISE} nicht gefunden.\n"
            "Erst mit --add-stadt eine Stadt laden."
        )

    if not no_pull and not test:
        pull_tankerkoenig()

    df_existing = pd.read_parquet(OUT_PREISE, columns=["date", "station_uuid"])
    alle_uuids = set(df_existing["station_uuid"].unique())
    letzter_ts = df_existing["date"].max()
    ab_datum = (letzter_ts - pd.DateOffset(months=1)).strftime("%Y-%m")

    print(f"\n🔄 Update: {len(alle_uuids)} Stationen, ab {ab_datum}")
    del df_existing
    gc.collect()

    df_neu = lade_preise(alle_uuids, ab_datum=ab_datum, workers=workers, test=test)

    print("\n🔀 Mit bestehenden Daten zusammenführen...")
    df_existing = pd.read_parquet(OUT_PREISE)
    cutoff = pd.Timestamp(ab_datum)
    df_existing = df_existing[df_existing["date"] < cutoff]
    df_gesamt = (
        pd.concat([df_existing, df_neu], ignore_index=True)
        .drop_duplicates(subset=["date", "station_uuid"])
        .sort_values(["station_uuid", "date"])
        .reset_index(drop=True)
    )
    del df_existing, df_neu
    gc.collect()

    out_pfad = OUTPUT_DIR / "tankstellen_preise_test.parquet" if test else OUT_PREISE
    df_gesamt.to_parquet(out_pfad, index=False)

    _print_summary(df_gesamt, out_pfad)

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"zeilen={len(df_gesamt)}\n")
            f.write(f"stationen={df_gesamt['station_uuid'].nunique()}\n")


def _print_summary(df: pd.DataFrame, out_pfad: Path):
    """Gibt eine Zusammenfassung aus."""
    print(f"\n{'='*60}")
    print(f"✅ Fertig: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"📄 {out_pfad} ({out_pfad.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"📊 {len(df):,} Zeilen")
    print(f"🏪 {df['station_uuid'].nunique()} Stationen")
    if not df.empty:
        print(f"📅 {df['date'].min()} – {df['date'].max()}")
    print(f"{'='*60}")


# =============================================================================
# Einstiegspunkt
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tankerkönig-Preisdaten verwalten"
    )

    gruppe = parser.add_mutually_exclusive_group(required=True)
    gruppe.add_argument(
        "--add-stadt",
        metavar="STADT",
        choices=sorted(STADT_CONFIGS.keys()),
        help=f"Neue Stadt laden: {', '.join(sorted(STADT_CONFIGS.keys()))}"
    )
    gruppe.add_argument(
        "--update",
        action="store_true",
        help="Alle vorhandenen Stationen fortschreiben"
    )

    parser.add_argument("--test",    action="store_true", help=f"Nur {TEST_CSV_ANZAHL} CSVs, kein git pull")
    parser.add_argument("--no-pull", action="store_true", help="Kein git pull")
    parser.add_argument("--workers", type=int, default=cpu_count(),
                        help=f"CPU-Kerne (default: {cpu_count()})")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    if args.add_stadt:
        add_stadt(
            stadtname=args.add_stadt,
            workers=args.workers,
            test=args.test,
            no_pull=args.no_pull,
        )
    elif args.update:
        update(
            workers=args.workers,
            test=args.test,
            no_pull=args.no_pull,
        )