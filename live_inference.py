#!/usr/bin/env python3
# live_inference.py
# Täglich ausgeführt via GitHub Actions.
# Liest aktuelle Daten, berechnet Features, macht Prognose,
# schreibt data/ml/prognose_aktuell.json

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

# --- Schritt 1: Aktueller Preis ---
url          = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={TANKERKOENIG_KEY}"
response     = requests.get(url, timeout=10)
data         = response.json()
station_data = data["prices"][STATION_UUID]

if station_data.get("status") == "closed" or "diesel" not in station_data:
    preise_tmp    = pd.read_parquet("data/tankstellen_preise.parquet")
    preise_tmp    = preise_tmp[(preise_tmp["station_uuid"] == STATION_UUID) & (preise_tmp["diesel"].notna())].sort_values("date")
    preis_aktuell = float(preise_tmp["diesel"].iloc[-1])
else:
    preis_aktuell = float(station_data["diesel"])

# --- Schritt 2: Letzte 48h Stundenbins ---
preise               = pd.read_parquet("data/tankstellen_preise.parquet")
preise               = preise[(preise["station_uuid"] == STATION_UUID) & (preise["diesel"].notna())].copy()
preise["date"]       = pd.to_datetime(preise["date"])
preise               = preise.sort_values("date")
preise["stunde_bin"] = preise["date"].dt.floor("h")

preise_std = (
    preise.groupby("stunde_bin")
    .agg(preis=("diesel", "mean"))
    .reset_index()
    .rename(columns={"stunde_bin": "date"})
)
preise_std = preise_std.set_index("date").asfreq("h").reset_index()
preise_std["preis"] = preise_std["preis"].ffill()

aktuelle_stunde = JETZT.replace(minute=0, second=0, microsecond=0, tzinfo=None)
neue_zeile      = pd.DataFrame({"date": [aktuelle_stunde], "preis": [preis_aktuell]})
preise_std      = pd.concat([preise_std, neue_zeile]).drop_duplicates(subset="date").sort_values("date")

# --- Schritt 3: Rolling Features ---
mean_24h_rueck       = float(preise_std["preis"].iloc[-24:].mean())
mean_48h_rueck       = float(preise_std["preis"].iloc[-48:-24].mean())
delta_24h_rueckblick = mean_24h_rueck - mean_48h_rueck
abweichung_t0_24h    = preis_aktuell - mean_24h_rueck
roll7d               = float(preise_std["preis"].iloc[-24*7:].mean())
roll30d              = float(preise_std["preis"].iloc[-24*30:].mean())
volatilitaet_7d      = float(preise_std["preis"].iloc[-24*7:].std())
abweichung_roll7d    = preis_aktuell - roll7d
abweichung_roll30d   = preis_aktuell - roll30d

# --- Schritt 4: Brent + EUR/USD ---
brent   = pd.read_csv("data/brent_futures_intraday_1h.csv", parse_dates=["period"]).sort_values("period")
eur_usd = pd.read_csv("data/eur_usd_rate.csv",              parse_dates=["period"]).sort_values("period")

brent_lag1d      = float(brent["brent_futures_usd_1h"].iloc[-25])
brent_lag2d      = float(brent["brent_futures_usd_1h"].iloc[-49])
brent_lag3d      = float(brent["brent_futures_usd_1h"].iloc[-73])
brent_lag4d      = float(brent["brent_futures_usd_1h"].iloc[-97])
eur_usd_lag1d    = float(eur_usd["eur_usd"].iloc[-2])
eur_usd_lag2d    = float(eur_usd["eur_usd"].iloc[-3])
eur_usd_lag3d    = float(eur_usd["eur_usd"].iloc[-4])
eur_usd_lag4d    = float(eur_usd["eur_usd"].iloc[-5])

brent_delta1d        = brent_lag1d - brent_lag2d
brent_delta2d        = brent_lag2d - brent_lag3d
brent_delta3d        = brent_lag3d - brent_lag4d
brent_steigt         = int(brent_delta1d > 0)
brent_richtungswechsel = int(brent_steigt != int(brent_lag2d - brent_lag3d > 0))
eur_usd_delta1d      = eur_usd_lag1d - eur_usd_lag2d
eur_usd_delta2d      = eur_usd_lag2d - eur_usd_lag3d
eur_usd_delta3d      = eur_usd_lag3d - eur_usd_lag4d
brent_eur_lag1d      = brent_lag1d / eur_usd_lag1d
brent_eur_lag2d      = brent_lag2d / eur_usd_lag2d
brent_eur_delta1d    = brent_eur_lag1d - brent_eur_lag2d

# --- Schritt 5: Kalender ---
feiertage   = pd.read_csv("data/feiertage.csv",   parse_dates=["datum"])
schulferien = pd.read_csv("data/schulferien.csv")
morgen      = (JETZT + timedelta(days=1)).date()

ist_feiertag_t1 = int(
    feiertage[
        (feiertage["datum"].dt.date == morgen) &
        (feiertage["bundesland_kuerzel"].str.contains("NW", na=False))
    ].shape[0] > 0
)

schulferien["datum_start"] = pd.to_datetime(schulferien["datum_start"]).dt.date
schulferien["datum_ende"]  = pd.to_datetime(schulferien["datum_ende"]).dt.date
ist_schulferien_t1 = int(
    schulferien[
        (schulferien["bundesland_code"] == "DE-NW") &
        (schulferien["datum_start"] <= morgen) &
        (schulferien["datum_ende"]  >= morgen)
    ].shape[0] > 0
)

wochentag_t1            = (JETZT.weekday() + 1) % 7
ist_montag_t1           = int(wochentag_t1 == 0)
stunde_t0               = JETZT.hour
ist_hauptanpassungszeit = int(6 <= stunde_t0 <= 10)
wt_dummies              = {f"wt_{i}": int(wochentag_t1 == i) for i in range(7)}

# --- Schritt 6: Feature-Vektor ---
modell_metadaten = json.load(open("data/ml/modell_metadaten_aral_duerener.json"))
feature_cols     = modell_metadaten["feature_cols"]

feature_dict = {
    "delta_24h_rueckblick":    delta_24h_rueckblick,
    "roll7d":                  roll7d,
    "roll30d":                 roll30d,
    "volatilitaet_7d":         volatilitaet_7d,
    "abweichung_roll7d":       abweichung_roll7d,
    "abweichung_roll30d":      abweichung_roll30d,
    "abweichung_t0_24h":       abweichung_t0_24h,
    "brent_delta1d":           brent_delta1d,
    "brent_delta2d":           brent_delta2d,
    "brent_delta3d":           brent_delta3d,
    "brent_steigt":            brent_steigt,
    "brent_richtungswechsel":  brent_richtungswechsel,
    "eur_usd_delta1d":         eur_usd_delta1d,
    "eur_usd_delta2d":         eur_usd_delta2d,
    "eur_usd_delta3d":         eur_usd_delta3d,
    "brent_eur_delta1d":       brent_eur_delta1d,
    "ist_covid":               0,
    "ist_ukraine":             0,
    "ist_tankrabatt":          0,
    "ist_niedrigwasser":       0,
    "stunde_t0":               stunde_t0,
    "ist_hauptanpassungszeit": ist_hauptanpassungszeit,
    "ist_montag_t1":           ist_montag_t1,
    **wt_dummies,
    "ist_feiertag_t1":         ist_feiertag_t1,
    "ist_schulferien_t1":      ist_schulferien_t1,
}

X_live = pd.DataFrame([feature_dict])[feature_cols]

# --- Schritt 7: Prognose + Entscheidungsmatrix ---
modell        = joblib.load("data/ml/modell_xgb_aral_duerener.pkl")
richtung_pred = int(modell.predict(X_live)[0])
prob          = modell.predict_proba(X_live)[0]
richtung_text = "steigt" if richtung_pred == 1 else "fällt"
konfidenz     = float(prob[richtung_pred])
delta_erwartet = abs(delta_24h_rueckblick * 0.5)

if abweichung_t0_24h < 0 and richtung_pred == 1:
    empfehlung  = "heute tanken"
    begruendung = "Aktuell im Dip — Preis steigt in den nächsten 24h"
elif abweichung_t0_24h < 0 and richtung_pred == 0:
    if abs(delta_erwartet) > volatilitaet_7d:
        empfehlung  = "morgen tanken"
        begruendung = "Dip — Preis fällt weiter, Rückgang übersteigt Volatilität"
    else:
        empfehlung  = "heute tanken"
        begruendung = "Dip — Rückgang wird von Volatilität aufgefressen"
elif abweichung_t0_24h >= 0 and richtung_pred == 0:
    empfehlung  = "morgen tanken"
    begruendung = "Aktuell im Peak — Preis fällt in den nächsten 24h"
else:
    empfehlung  = "dip abpassen"
    begruendung = "Peak und Preis steigt — heute Abend 18-20 Uhr tanken"

# --- Live-Log: nur committen wenn Preis sich geändert hat ---


LOG_PATH = "data/ml/preis_live_log.csv"

# Letzten bekannten Preis aus Log lesen
letzter_log_preis = None
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r") as f:
        zeilen = list(csv.DictReader(f))
        if zeilen:
            letzter_log_preis = float(zeilen[-1]["preis"])

# Nur schreiben wenn Preis sich geändert hat
preis_geaendert = (letzter_log_preis is None) or (abs(preis_aktuell - letzter_log_preis) > 0.001)

if preis_geaendert:
    datei_existiert = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "preis", "tendenz_24h"])
        if not datei_existiert:
            writer.writeheader()
        writer.writerow({
            "timestamp":   JETZT.strftime("%Y-%m-%d %H:%M"),
            "preis":       round(preis_aktuell, 3),
            "tendenz_24h": round(delta_erwartet, 4),  # bereits vorzeichenbehaftet
        })
    print(f"Live-Log aktualisiert: {preis_aktuell:.3f} € ({JETZT.strftime('%H:%M')})")
else:
    print(f"Preis unverändert ({preis_aktuell:.3f} €) — kein Log-Eintrag")

# --- Schritt 8: JSON speichern ---
prognose = {
    "timestamp":          JETZT.strftime("%Y-%m-%d %H:%M"),
    "station_uuid":       STATION_UUID,
    "station":            "ARAL Dürener Str. 407",
    "preis_aktuell":      round(preis_aktuell, 3),
    "mean_24h_rueck":     round(mean_24h_rueck, 3),
    "abweichung_t0_24h":  round(abweichung_t0_24h, 4),
    "dip_oder_peak":      "Dip" if abweichung_t0_24h < 0 else "Peak",
    "richtung_24h":       richtung_text,
    "konfidenz":          round(konfidenz * 100, 1),
    "delta_erwartet":     round(float(delta_erwartet), 4),
    "volatilitaet_7d":    round(volatilitaet_7d, 4),
    "empfehlung":         empfehlung,
    "begruendung":        begruendung,
    "modell_accuracy":    modell_metadaten["accuracy_test"],
}

with open("data/ml/prognose_aktuell.json", "w", encoding="utf-8") as f:
    json.dump(prognose, f, indent=2, ensure_ascii=False)

print(json.dumps(prognose, indent=2, ensure_ascii=False))
