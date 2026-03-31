#!/usr/bin/env python3
# live_inference.py
# Stündlich ausgeführt via GitHub Actions.
# Liest aktuelle Preise (ARAL + Nachbarn), berechnet Features,
# macht 24h Prognose (eine Vorhersage pro Stunde), schreibt JSON + Log.

import pandas as pd
import numpy as np
import joblib
import json
import requests
import os
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

load_dotenv()
TANKERKOENIG_KEY = os.getenv("TANKERKOENIG_KEY")

BERLIN       = pytz.timezone("Europe/Berlin")
JETZT        = datetime.now(BERLIN)
STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"

# --- Schritt 1: Metadaten laden ---
metadaten    = json.load(open("data/ml/modell_metadaten_aral_duerener.json"))
feature_cols = metadaten["feature_cols"]
ziel_cols    = metadaten["ziel_cols"]
nachbar_uuids = metadaten["nachbar_uuids"]

def _download_model_if_missing(local_path: str, env_url_key: str) -> bool:
    if os.path.exists(local_path):
        return True
    fname = os.path.basename(local_path)
    candidates = []
    env_url = os.getenv(env_url_key)
    if env_url:
        candidates.append(env_url)
    candidates.append(f"https://github.com/felixschrader/spritpreisprognose/releases/latest/download/{fname}")
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    for url in candidates:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and r.content:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                print(f"✅ Modell geladen von: {url}")
                return True
            print(f"ℹ️ Kein Modell unter {url} (HTTP {r.status_code})")
        except Exception as e:
            print(f"ℹ️ Download fehlgeschlagen ({url}): {e}")
    return False

# --- Schritt 2: Aktuelle Preise via Tankerkönig — max 10 IDs pro Request ---
import math

alle_uuids   = [STATION_UUID] + nachbar_uuids
batch_size   = 10
live_preise  = {}

for i in range(0, len(alle_uuids), batch_size):
    batch    = alle_uuids[i:i + batch_size]
    ids_str  = ",".join(batch)
    url      = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={ids_str}&apikey={TANKERKOENIG_KEY}"
    response = requests.get(url, timeout=10)
    live_preise.update(response.json()["prices"])

# --- Schritt 3: Historische Preise laden als Fallback ---
preise_hist = pd.read_parquet("data/tankstellen_preise.parquet")
preise_hist = preise_hist[preise_hist["station_uuid"].isin(alle_uuids) & preise_hist["diesel"].notna()].copy()
preise_hist["date"] = pd.to_datetime(preise_hist["date"])

def get_preis(uuid, live_preise, preise_hist):
    """Gibt aktuellen Diesel-Preis zurück — live wenn verfügbar, sonst letzter bekannter."""
    data = live_preise.get(uuid, {})
    if data.get("status") != "closed" and data.get("diesel") is not None:
        return float(data["diesel"])
    hist = preise_hist[preise_hist["station_uuid"] == uuid].sort_values("date")
    if len(hist) > 0:
        return float(hist["diesel"].iloc[-1])
    return None

# Preise sammeln
preis_dict = {uuid: get_preis(uuid, live_preise, preise_hist) for uuid in alle_uuids}
preis_aral = preis_dict[STATION_UUID]

nachbar_preise = [v for k, v in preis_dict.items() if k != STATION_UUID and v is not None]

# --- Schritt 4: Stündliche Historie ARAL aufbauen ---
aral_hist = preise_hist[preise_hist["station_uuid"] == STATION_UUID].copy()
aral_hist["stunde_bin"] = aral_hist["date"].dt.floor("h")
aral_hist = (
    aral_hist.groupby("stunde_bin")["diesel"]
    .last()
    .reset_index()
    .sort_values("stunde_bin")
)

# Aktuelle Stunde anhängen
aktuelle_stunde = JETZT.replace(minute=0, second=0, microsecond=0, tzinfo=None)
neue_zeile      = pd.DataFrame({"stunde_bin": [aktuelle_stunde], "diesel": [preis_aral]})
aral_hist       = pd.concat([aral_hist, neue_zeile]).drop_duplicates(subset="stunde_bin").sort_values("stunde_bin")

# Vollständiges Stundenraster auffüllen
alle_stunden = pd.date_range(start=aral_hist["stunde_bin"].min(), end=aktuelle_stunde, freq="h")
aral_hist    = aral_hist.set_index("stunde_bin").reindex(alle_stunden).ffill().reset_index()
aral_hist.columns = ["stunde_bin", "preis_aral"]

# Letzte 30 Tage reichen für Features
aral_hist = aral_hist[aral_hist["stunde_bin"] >= aktuelle_stunde - timedelta(days=30)].reset_index(drop=True)

# --- Schritt 5: Zyklusfeatures berechnen ---
aral_hist["delta_1h"]  = aral_hist["preis_aral"].diff(1)
aral_hist["delta_3h"]  = aral_hist["preis_aral"].diff(3)
aral_hist["delta_24h"] = aral_hist["preis_aral"].diff(24)

aral_hist["ist_erhoehung"] = (aral_hist["delta_1h"] > 0).astype(int)
aral_hist["stunden_seit_erhoehung"] = (
    aral_hist["ist_erhoehung"]
    .groupby((aral_hist["ist_erhoehung"] == 1).cumsum())
    .cumcount()
)

aral_hist["roll_max_24h"]    = aral_hist["preis_aral"].rolling(24, min_periods=1).max()
aral_hist["abstand_vom_max"] = aral_hist["preis_aral"] - aral_hist["roll_max_24h"]
aral_hist["roll_min_24h"]    = aral_hist["preis_aral"].rolling(24, min_periods=1).min()
aral_hist["abstand_vom_min"] = aral_hist["preis_aral"] - aral_hist["roll_min_24h"]

aral_hist["roll7d"]          = aral_hist["preis_aral"].rolling(24*7,  min_periods=1).mean()
aral_hist["roll30d"]         = aral_hist["preis_aral"].rolling(24*30, min_periods=1).mean()
aral_hist["volatilitaet_7d"] = aral_hist["preis_aral"].rolling(24*7,  min_periods=2).std()

aral_hist["stunde"]       = aral_hist["stunde_bin"].dt.hour
aral_hist["stunde_t6h"]   = (aral_hist["stunde_bin"] + pd.Timedelta(hours=6)).dt.hour
aral_hist["stunde_t12h"]  = (aral_hist["stunde_bin"] + pd.Timedelta(hours=12)).dt.hour
aral_hist["wochentag_t6h"]  = (aral_hist["stunde_bin"] + pd.Timedelta(hours=6)).dt.dayofweek
aral_hist["wochentag_t12h"] = (aral_hist["stunde_bin"] + pd.Timedelta(hours=12)).dt.dayofweek

# --- Schritt 6: Nachbar-Features berechnen ---
nachbar_mean = float(np.mean(nachbar_preise))
nachbar_min  = float(np.min(nachbar_preise))
nachbar_max  = float(np.max(nachbar_preise))

# Shell direkt nebenan — erster Nachbar in der Liste
shell_uuid  = nachbar_uuids[0]
preis_shell = preis_dict.get(shell_uuid)

# Wie viele Nachbarn sind günstiger?
nachbarn_guenstiger = sum(1 for p in nachbar_preise if p < preis_aral)

# Änderung der Nachbarn zur letzten Stunde — aus Historie schätzen
# (im Live-Betrieb: letzte bekannte Preise der Nachbarn)
nachbarn_steigen_anteil = 0.0  # Fallback — wird in zukünftiger Version aus Log gelesen

# --- Schritt 7: Externe Features ---
brent   = pd.read_csv("data/brent_futures_daily.csv",  parse_dates=["period"]).sort_values("period")
eur_usd = pd.read_csv("data/eur_usd_rate.csv",         parse_dates=["period"]).sort_values("period")

brent_aktuell   = float(brent["brent_futures_usd"].iloc[-1])
brent_lag1      = float(brent["brent_futures_usd"].iloc[-2])
brent_lag2      = float(brent["brent_futures_usd"].iloc[-3])
brent_delta1    = brent_lag1 - brent_lag2
eur_usd_aktuell = float(eur_usd["eur_usd"].iloc[-1])
eur_usd_lag1    = float(eur_usd["eur_usd"].iloc[-2])
brent_eur       = brent_aktuell / eur_usd_aktuell

# Externe Effekte
externe = pd.read_csv("data/externe_effekte.csv", parse_dates=["date"])
energie = pd.read_csv("data/energiesteuer.csv",   parse_dates=["date"])

heute_str  = JETZT.strftime("%Y-%m-%d")
ext_heute  = externe[externe["date"].dt.strftime("%Y-%m-%d") == heute_str]
ener_heute = energie[energie["date"].dt.strftime("%Y-%m-%d") == heute_str]

ist_lockdown      = int(ext_heute["ist_lockdown"].values[0])      if len(ext_heute) > 0 else 0
ist_niedrigwasser = int(ext_heute["ist_niedrigwasser"].values[0]) if len(ext_heute) > 0 else 0
ist_tankrabatt    = int(ener_heute["ist_tankrabatt"].values[0])    if len(ener_heute) > 0 else 0
energiesteuer     = float(ener_heute["energiesteuer_diesel"].values[0]) if len(ener_heute) > 0 else 47.04

# --- Schritt 8: Feature-Vektor aus letzter Zeile der Historie ---
letzte = aral_hist.iloc[-1]

feature_dict = {
    "delta_1h":                float(letzte["delta_1h"]),
    "delta_3h":                float(letzte["delta_3h"]),
    "delta_24h":               float(letzte["delta_24h"]),
    "stunden_seit_erhoehung":  float(letzte["stunden_seit_erhoehung"]),
    "roll_max_24h":            float(letzte["roll_max_24h"]),
    "abstand_vom_max":         float(letzte["abstand_vom_max"]),
    "roll_min_24h":            float(letzte["roll_min_24h"]),
    "abstand_vom_min":         float(letzte["abstand_vom_min"]),
    "roll7d":                  float(letzte["roll7d"]),
    "roll30d":                 float(letzte["roll30d"]),
    "volatilitaet_7d":         float(letzte["volatilitaet_7d"]),
    "stunde_t6h":              float(letzte["stunde_t6h"]),
    "stunde_t12h":             float(letzte["stunde_t12h"]),
    "wochentag_t6h":           float(letzte["wochentag_t6h"]),
    "wochentag_t12h":          float(letzte["wochentag_t12h"]),
    "nachbar_mean":            nachbar_mean,
    "nachbar_min":             nachbar_min,
    "nachbar_max":             nachbar_max,
    "delta_zu_nachbar_mean":   preis_aral - nachbar_mean,
    "delta_zu_nachbar_min":    preis_aral - nachbar_min,
    "nachbarn_guenstiger":     float(nachbarn_guenstiger),
    "nachbarn_steigen_anteil": nachbarn_steigen_anteil,
    "delta_zu_shell":          preis_aral - preis_shell if preis_shell else 0.0,
    "brent":                   brent_aktuell,
    "eur_usd":                 eur_usd_aktuell,
    "brent_eur":               brent_eur,
    "brent_lag1":              brent_lag1,
    "brent_lag2":              brent_lag2,
    "brent_delta1":            brent_delta1,
    "eur_usd_lag1":            eur_usd_lag1,
    "stunde":                  float(letzte["stunde"]),
    "ist_lockdown":            ist_lockdown,
    "ist_niedrigwasser":       ist_niedrigwasser,
    "energiesteuer_diesel":    energiesteuer,
    "ist_tankrabatt":          ist_tankrabatt,
}

X_live = pd.DataFrame([feature_dict])[feature_cols]

# --- Schritt 9: Prognose ---
MODELL_PATH_MULTI = "data/ml/modell_rf_multi_aral_duerener.pkl"
if _download_model_if_missing(MODELL_PATH_MULTI, "MODELL_RF_MULTI_URL"):
    modell = joblib.load(MODELL_PATH_MULTI)
    prognose_arr = modell.predict(X_live)[0]  # Array mit 24 binären Werten
else:
    # Fallback, damit der Workflow nicht bei fehlender .pkl-Datei ausfällt.
    trend_up = float(letzte["delta_3h"]) > 0
    prognose_arr = np.array([1 if trend_up else 0] * 24)
    print(f"⚠️ Modell fehlt: {MODELL_PATH_MULTI} — nutze Trend-Fallback ({'steigt' if trend_up else 'fällt'}).")

# Stufenlinie aufbauen — ausgehend vom aktuellen Preis
prognose_stufen = []
preis_simuliert = preis_aral
for h, richtung in enumerate(prognose_arr, start=1):
    zeitpunkt = (JETZT + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M")
    prognose_stufen.append({
        "stunde_offset": h,
        "zeitpunkt":     zeitpunkt,
        "richtung":      "steigt" if richtung == 1 else "fällt",
    })

# --- Schritt 10: Entscheidungsmatrix ---
# D: aktueller Preis vs. Nachbar-Mittel
dip_oder_peak = "Dip" if preis_aral < nachbar_mean else "Peak"

# A: steigt in den nächsten 6h?
richtung_6h  = "steigt" if prognose_arr[5] == 1 else "fällt"

# B: steigt in den nächsten 12h?
richtung_12h = "steigt" if prognose_arr[11] == 1 else "fällt"

if dip_oder_peak == "Dip" and richtung_6h == "steigt":
    empfehlung  = "heute tanken"
    begruendung = "Aktuell günstig — Preis steigt in den nächsten Stunden"
elif dip_oder_peak == "Dip" and richtung_6h == "fällt" and richtung_12h == "steigt":
    empfehlung  = "heute tanken"
    begruendung = "Günstiger Dip — in 12h steigt der Preis wieder"
elif dip_oder_peak == "Dip" and richtung_6h == "fällt" and richtung_12h == "fällt":
    empfehlung  = "später tanken"
    begruendung = "Sparfuchs: Preis fällt weiter — noch etwas warten"
elif dip_oder_peak == "Peak" and richtung_6h == "fällt":
    empfehlung  = "später tanken"
    begruendung = "Aktuell im Peak — Preis fällt in den nächsten Stunden"
elif dip_oder_peak == "Peak" and richtung_6h == "steigt" and richtung_12h == "fällt":
    empfehlung  = "in 6-12h tanken"
    begruendung = "Kurzer Anstieg erwartet — danach fällt der Preis"
else:
    empfehlung  = "notfalls heute tanken"
    begruendung = "Peak und weiter steigend — wenn nötig jetzt, sonst morgen früh"

# --- Schritt 11: Live-Log ---
LOG_PATH = "data/ml/preis_live_log.csv"

letzter_log_preis = None
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r") as f:
        zeilen = list(csv.DictReader(f))
        if zeilen:
            letzter_log_preis = float(zeilen[-1]["preis"])

preis_geaendert = (letzter_log_preis is None) or (abs(preis_aral - letzter_log_preis) > 0.001)

if preis_geaendert:
    datei_existiert = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "preis", "richtung_6h", "richtung_12h"])
        if not datei_existiert:
            writer.writeheader()
        writer.writerow({
            "timestamp":    JETZT.strftime("%Y-%m-%d %H:%M"),
            "preis":        round(preis_aral, 3),
            "richtung_6h":  richtung_6h,
            "richtung_12h": richtung_12h,
        })
    print(f"Live-Log aktualisiert: {preis_aral:.3f} € ({JETZT.strftime('%H:%M')})")
else:
    print(f"Preis unverändert ({preis_aral:.3f} €) — kein Log-Eintrag")

# --- Schritt 12: JSON speichern ---
prognose = {
    "timestamp":          JETZT.strftime("%Y-%m-%d %H:%M"),
    "station_uuid":       STATION_UUID,
    "station":            "ARAL Dürener Str. 407",
    "preis_aktuell":      round(preis_aral, 3),
    "nachbar_mean":       round(nachbar_mean, 3),
    "dip_oder_peak":      dip_oder_peak,
    "delta_zu_nachbarn":  round(preis_aral - nachbar_mean, 4),
    "richtung_6h":        richtung_6h,
    "richtung_12h":       richtung_12h,
    "empfehlung":         empfehlung,
    "begruendung":        begruendung,
    "prognose_stufen":    prognose_stufen,
    "modell_accuracy":    metadaten["accuracy_mean"],
}

with open("data/ml/prognose_aktuell.json", "w", encoding="utf-8") as f:
    json.dump(prognose, f, indent=2, ensure_ascii=False)

print(json.dumps(prognose, indent=2, ensure_ascii=False))