#!/usr/bin/env python3
"""
Baut data/ml/prognose_log.csv für die letzten 28 Kalendertage (Europe/Berlin):
eine Zeile pro Tag, Lücken mit Modell + Ist nach gleicher Logik wie live_inference_tagesbasis.py.

Tage ohne Kernpreis-Zeile (z. B. nach dem letzten Stand in tankstellen_preise.parquet)
bekommen leere Felder — bis neue Preisdaten da sind, gibt es keine Features/Prognose.

Aufruf vom Repo-Root:  python scripts/fill_prognose_log_calendar.py
Optional:  --ende 2026-04-04  (sonst heute Berlin)

Wird täglich nach live_inference_tagesbasis.py in GitHub Actions ausgeführt, damit das
Dashboard-CSV mit der Parquet-Zeitreihe mitläuft (nicht nur ein Append pro Lauf).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytz
import requests
from dotenv import load_dotenv

load_dotenv()

REPO = Path(__file__).resolve().parents[1]
ML_DIR = REPO / "data" / "ml"
LOG_PATH = ML_DIR / "prognose_log.csv"
MODELL_PATH = ML_DIR / "modell_rf_ml_master_station_kern_tp1_tm1.pkl"
META_PATH = ML_DIR / "modell_metadaten_ml_master_station_kern_tp1_tm1.json"
BRENT_CSV = REPO / "data" / "brent_futures_daily.csv"
EUR_CSV = REPO / "data" / "eur_usd_rate.csv"
PREISE_PQ = REPO / "data" / "tankstellen_preise.parquet"

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
KERN_STUNDEN = list(range(13, 21))
SCHWELLE_ANP = 0.005
BRENT_CAL_FORWARD_DAYS = 14

BERLIN = pytz.timezone("Europe/Berlin")


def tage_seit(series):
    result, z = [], 0
    for v in series:
        z = 0 if v == 1 else z + 1
        result.append(z)
    return result


def safe(val, fallback=0.0):
    return float(val) if not pd.isna(val) else fallback


def load_brent_eur_calendar(tag_start: pd.Timestamp, tag_end: pd.Timestamp) -> pd.DataFrame:
    brent = pd.read_csv(BRENT_CSV, parse_dates=["period"]).sort_values("period")
    eur = pd.read_csv(EUR_CSV, parse_dates=["period"]).sort_values("period")
    brent = brent.rename(columns={"period": "tag", "brent_futures_usd": "brent_usd"})
    eur = eur.rename(columns={"period": "tag"})
    m = brent.merge(eur[["tag", "eur_usd"]], on="tag", how="left")
    m["brent_eur"] = m["brent_usd"] / m["eur_usd"]

    kal = pd.DataFrame({"tag": pd.date_range(tag_start.normalize(), tag_end.normalize(), freq="D")})
    out = kal.merge(m[["tag", "brent_eur"]], on="tag", how="left").sort_values("tag")
    out["brent_eur"] = out["brent_eur"].ffill().bfill()
    out["brent_delta1"] = out["brent_eur"].diff(1)
    out["brent_delta2"] = out["brent_eur"].diff(2)
    out["brent_delta3"] = out["brent_eur"].diff(3)
    return out


def _index_fuer_basis_tag(df: pd.DataFrame, basis_day: date) -> int | None:
    tnorm = pd.Timestamp(basis_day).normalize()
    mask = (pd.to_datetime(df["tag"]).dt.normalize() == tnorm).to_numpy()
    hit = np.flatnonzero(mask)
    if len(hit) != 1:
        return None
    return int(hit[0])


def richtung_positiv_scharf(x: float) -> int:
    return int(float(x) > 0)


def _download_model_if_missing(local_path: Path) -> bool:
    """Wie live_inference_tagesbasis.py — CI hat oft kein .pkl im Repo."""
    if local_path.is_file():
        return True
    fname = local_path.name
    candidates = []
    env_url = os.getenv("MODELL_RF_ML_MASTER_URL")
    if env_url:
        candidates.append(env_url)
    candidates.append(
        f"https://github.com/felixschrader/dieselpreisprognose/releases/latest/download/{fname}"
    )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    for url in candidates:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and r.content:
                local_path.write_bytes(r.content)
                print(f"Modell geladen: {url}")
                return True
            print(f"Kein Modell unter {url} (HTTP {r.status_code})")
        except Exception as e:
            print(f"Download fehlgeschlagen ({url}): {e}")
    return False


def _predict_delta(fd: dict, features: list[str], modell) -> float:
    """RandomForest oder gleiche Heuristik wie live_inference_tagesbasis ohne .pkl."""
    X = pd.DataFrame([{c: fd[c] for c in features}])[features]
    if modell is not None:
        return float(modell.predict(X)[0])
    h = np.nanmean(
        [
            fd.get("delta_kern_lag1", 0.0),
            fd.get("delta_kern_lag2", 0.0),
            fd.get("brent_delta2", 0.0),
        ]
    )
    return float(np.clip(h, -0.03, 0.03))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ende",
        type=str,
        default=None,
        help="Enddatum YYYY-MM-DD (Berlin-Kalendertag), Standard: heute",
    )
    args = ap.parse_args()

    if args.ende:
        ende = date.fromisoformat(args.ende)
    else:
        ende = datetime_now_berlin_date()

    start = ende - timedelta(days=27)

    metadaten = json.loads(META_PATH.read_text(encoding="utf-8"))
    features: list[str] = metadaten["feature_cols"]

    modell = None
    if _download_model_if_missing(MODELL_PATH):
        modell = joblib.load(MODELL_PATH)
        print(f"Prognose-Log-Füllung: Modell · {len(features)} Features")
    else:
        print("Prognose-Log-Füllung: Heuristik (kein .pkl — wie live_inference Fallback)")

    preise = pd.read_parquet(PREISE_PQ)
    preise = preise[(preise["station_uuid"] == STATION_UUID) & preise["diesel"].notna()].copy()
    preise["date"] = pd.to_datetime(preise["date"])
    preise["stunde_bin"] = preise["date"].dt.floor("h")
    preise["stunde_h"] = preise["date"].dt.hour

    std_bins = preise.groupby("stunde_bin")["diesel"].median().reset_index()
    std_bins["tag"] = pd.to_datetime(std_bins["stunde_bin"].dt.date)
    std_bins["stunde_h"] = std_bins["stunde_bin"].dt.hour

    kern_hist = (
        std_bins[std_bins["stunde_h"].isin(KERN_STUNDEN)]
        .groupby("tag")["diesel"]
        .quantile(0.10)
        .reset_index()
        .rename(columns={"diesel": "kernpreis_p10"})
        .sort_values("tag")
        .reset_index(drop=True)
    )

    kern_hist["delta_kern"] = kern_hist["kernpreis_p10"].diff(1)
    kern_hist["delta_kern_lag1"] = kern_hist["delta_kern"].shift(1)
    kern_hist["delta_kern_lag2"] = kern_hist["delta_kern"].shift(2)
    kern_hist["hat_erhoehung"] = (kern_hist["delta_kern"] > SCHWELLE_ANP).astype(int)
    kern_hist["hat_senkung"] = (kern_hist["delta_kern"] < -SCHWELLE_ANP).astype(int)
    kern_hist["hat_anpassung"] = (kern_hist["delta_kern"].abs() > SCHWELLE_ANP).astype(int)
    kern_hist["wochentag"] = kern_hist["tag"].dt.dayofweek
    kern_hist["ist_montag"] = (kern_hist["wochentag"] == 0).astype(int)
    kern_hist["tage_seit_erhoehung"] = tage_seit(kern_hist["hat_erhoehung"])
    kern_hist["tage_seit_senkung"] = tage_seit(kern_hist["hat_senkung"])

    t_min = pd.Timestamp(kern_hist["tag"].min())
    t_max = pd.Timestamp(kern_hist["tag"].max()) + pd.Timedelta(days=BRENT_CAL_FORWARD_DAYS)
    brent_tag = load_brent_eur_calendar(t_min, t_max)

    df_markt = kern_hist.merge(
        brent_tag[["tag", "brent_eur", "brent_delta1", "brent_delta2", "brent_delta3"]],
        on="tag",
        how="left",
    )
    df_markt["kern_roll7_std"] = df_markt["kernpreis_p10"].rolling(7, min_periods=2).std()

    brent_bei_anp = np.nan
    bruck = []
    for _, row in df_markt.iterrows():
        if row["hat_anpassung"] == 1 or np.isnan(brent_bei_anp):
            brent_bei_anp = row["brent_eur"]
        bruck.append(row["brent_eur"] - brent_bei_anp if not np.isnan(brent_bei_anp) else 0.0)
    df_markt["brent_druck_seit_anpassung"] = bruck

    roll3 = df_markt["brent_eur"].rolling(3, min_periods=2).mean()
    df_markt["brent_roll_delta_tm1_tm3"] = roll3.shift(1) - roll3.shift(3)

    fieldnames = ["datum", "predicted_delta", "actual_delta", "richtung_korrekt"]
    out_rows: list[dict] = []

    d = start
    while d <= ende:
        j = _index_fuer_basis_tag(kern_hist, d)
        if j is None:
            out_rows.append(
                {
                    "datum": str(d),
                    "predicted_delta": "",
                    "actual_delta": "",
                    "richtung_korrekt": "",
                }
            )
        else:
            row_m = df_markt.iloc[j]
            fd = {c: safe(row_m[c]) for c in features}
            pred = _predict_delta(fd, features, modell)

            actual_s = ""
            richtung_s = ""
            if j >= 1 and j < len(kern_hist) - 1:
                actual = float(
                    kern_hist.iloc[j + 1]["kernpreis_p10"] - kern_hist.iloc[j - 1]["kernpreis_p10"]
                )
                actual_s = str(round(actual, 5))
                richtung_s = str(
                    int(
                        richtung_positiv_scharf(pred) == richtung_positiv_scharf(actual)
                    )
                )

            out_rows.append(
                {
                    "datum": str(d),
                    "predicted_delta": str(round(pred, 5)),
                    "actual_delta": actual_s,
                    "richtung_korrekt": richtung_s,
                }
            )
        d += timedelta(days=1)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)

    kern_max = pd.Timestamp(kern_hist["tag"].max()).date()
    n_leer = sum(1 for r in out_rows if r["predicted_delta"] == "")
    print(
        f"geschrieben: {LOG_PATH} · Fenster {start} … {ende} ({len(out_rows)} Tage) · "
        f"letzter Kerntag in Daten: {kern_max} · ohne Prognose (leer): {n_leer}"
    )


def datetime_now_berlin_date() -> date:
    return pd.Timestamp.now(tz=BERLIN).date()


if __name__ == "__main__":
    main()
