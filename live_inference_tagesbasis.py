#!/usr/bin/env python3
# live_inference_tagesbasis.py
# Täglich 09:00 UTC via GitHub Actions.
# NRW-Marktpreis: 50 ARAL-Stationen via Tankerkönig API.
# Schreibt: data/ml/prognose_tagesbasis.json + data/ml/prognose_log.csv

import pandas as pd
import numpy as np
import joblib, json, os, csv, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

load_dotenv()
TANKERKOENIG_KEY = os.getenv("TANKERKOENIG_KEY")
BERLIN        = pytz.timezone("Europe/Berlin")
JETZT         = datetime.now(BERLIN)
HEUTE         = JETZT.date()
GESTERN       = HEUTE - timedelta(days=1)
STATION_UUID  = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
KERN_STUNDEN  = list(range(13, 21))
SCHWELLE_ANP  = 0.005
MODELL_PATH   = "data/ml/modell_rf_markt_aral_duerener.pkl"
META_PATH     = "data/ml/modell_metadaten_markt_aral_duerener.json"
PROGNOSE_PATH = "data/ml/prognose_tagesbasis.json"
LOG_PATH      = "data/ml/prognose_log.csv"
SAMPLE_PATH   = "data/ml/aral_nrw_sample_uuids.csv"

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

metadaten = json.load(open(META_PATH, encoding="utf-8"))
FEATURES  = metadaten["feature_cols"]
modell = None
if _download_model_if_missing(MODELL_PATH, "MODELL_RF_MARKT_URL"):
    modell = joblib.load(MODELL_PATH)
    print(f"Modell geladen · Features: {FEATURES}")
else:
    print(f"⚠️ Modell fehlt: {MODELL_PATH} — nutze Heuristik-Fallback.")

# ARAL Kernpreis
preise = pd.read_parquet("data/tankstellen_preise.parquet")
preise = preise[(preise["station_uuid"] == STATION_UUID) & preise["diesel"].notna()].copy()
preise["date"]       = pd.to_datetime(preise["date"])
preise["stunde_bin"] = preise["date"].dt.floor("h")
preise["stunde_h"]   = preise["date"].dt.hour

std_bins = preise.groupby("stunde_bin")["diesel"].median().reset_index()
std_bins["tag"]      = pd.to_datetime(std_bins["stunde_bin"].dt.date)
std_bins["stunde_h"] = std_bins["stunde_bin"].dt.hour

kern_hist = (
    std_bins[std_bins["stunde_h"].isin(KERN_STUNDEN)]
    .groupby("tag")["diesel"].quantile(0.10)
    .reset_index().rename(columns={"diesel": "kernpreis_p10"})
    .sort_values("tag").reset_index(drop=True)
)
kern_hist["delta_kern"]          = kern_hist["kernpreis_p10"].diff(1)
kern_hist["delta_kern_lag1"]     = kern_hist["delta_kern"].shift(1)
kern_hist["delta_kern_lag2"]     = kern_hist["delta_kern"].shift(2)
kern_hist["hat_erhoehung"]       = (kern_hist["delta_kern"] >  SCHWELLE_ANP).astype(int)
kern_hist["hat_senkung"]         = (kern_hist["delta_kern"] < -SCHWELLE_ANP).astype(int)
kern_hist["hat_anpassung"]       = (kern_hist["delta_kern"].abs() > SCHWELLE_ANP).astype(int)
kern_hist["wochentag"]           = kern_hist["tag"].dt.dayofweek
kern_hist["ist_montag"]          = (kern_hist["wochentag"] == 0).astype(int)

def tage_seit(series):
    result, z = [], 0
    for v in series:
        z = 0 if v == 1 else z + 1
        result.append(z)
    return result

kern_hist["tage_seit_erhoehung"] = tage_seit(kern_hist["hat_erhoehung"])
kern_hist["tage_seit_senkung"]   = tage_seit(kern_hist["hat_senkung"])
letzte_aral     = kern_hist.iloc[-1]
kernpreis_heute = float(letzte_aral["kernpreis_p10"])
print(f"ARAL Kernpreis: {kernpreis_heute:.3f} € ({letzte_aral['tag'].date()})")

# NRW-Marktpreis via API
nrw_uuids  = pd.read_csv(SAMPLE_PATH)["uuid"].tolist()
nrw_preise = []
for i in range(0, len(nrw_uuids), 10):
    batch = nrw_uuids[i:i+10]
    url   = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={','.join(batch)}&apikey={TANKERKOENIG_KEY}"
    try:
        data = requests.get(url, timeout=10).json().get("prices", {})
        for info in data.values():
            if info.get("status") != "closed" and info.get("diesel") is not None:
                nrw_preise.append(float(info["diesel"]))
    except Exception as e:
        print(f"API-Fehler: {e}")

if len(nrw_preise) >= 5:
    markt_median_live = float(np.median(nrw_preise))
    residuum_live     = kernpreis_heute - markt_median_live
    print(f"NRW-Markt: {markt_median_live:.3f} € (n={len(nrw_preise)})")
else:
    df_fb = pd.read_parquet("data/ml/aral_nrw_tagesbasis.parquet")
    df_fb["tag"] = pd.to_datetime(df_fb["tag"])
    markt_median_live = float(df_fb.groupby("tag")["kernpreis_p10"].median().iloc[-1])
    residuum_live     = kernpreis_heute - markt_median_live
    print(f"Fallback NRW-Markt: {markt_median_live:.3f} €")

# Markt-Lags aus Parquet-Historie + heutigem API-Wert
df_nrw_hist = pd.read_parquet("data/ml/aral_nrw_tagesbasis.parquet")
df_nrw_hist["tag"] = pd.to_datetime(df_nrw_hist["tag"])
markt_serie = (
    df_nrw_hist.groupby("tag")["kernpreis_p10"].median()
    .reset_index().rename(columns={"kernpreis_p10": "markt_median"})
    .sort_values("tag")
)
heute_row = pd.DataFrame({"tag": [pd.Timestamp(HEUTE)], "markt_median": [markt_median_live]})
markt_serie = pd.concat([markt_serie, heute_row]).drop_duplicates("tag", keep="last").sort_values("tag").reset_index(drop=True)
markt_serie["delta_markt"]      = markt_serie["markt_median"].diff(1)
markt_serie["delta_markt_lag1"] = markt_serie["delta_markt"].shift(1)
markt_serie["delta_markt_lag2"] = markt_serie["delta_markt"].shift(2)
markt_serie["markt_std"]        = markt_serie["markt_median"].rolling(7, min_periods=2).std()
letzte_markt = markt_serie.iloc[-1]

# Residuum-Lags
res_serie = kern_hist.merge(markt_serie[["tag", "markt_median"]], on="tag", how="left")
res_serie["residuum"]      = res_serie["kernpreis_p10"] - res_serie["markt_median"]
res_serie["residuum_lag1"] = res_serie["residuum"].shift(1)
letzte_res = res_serie.dropna(subset=["residuum_lag1"]).iloc[-1]

# Brent
brent   = pd.read_csv("data/brent_futures_daily.csv", parse_dates=["period"]).sort_values("period")
eur_usd = pd.read_csv("data/eur_usd_rate.csv",        parse_dates=["period"]).sort_values("period")
brent   = brent.rename(columns={"period": "tag", "brent_futures_usd": "brent_usd"})
eur_usd = eur_usd.rename(columns={"period": "tag"})
brent_tag = brent.merge(eur_usd, on="tag", how="left")
brent_tag["brent_eur"]    = brent_tag["brent_usd"] / brent_tag["eur_usd"]
brent_tag["brent_delta2"] = brent_tag["brent_eur"].diff(2)
letzte_brent = brent_tag.dropna(subset=["brent_delta2"]).iloc[-1]
brent_delta2 = float(letzte_brent["brent_delta2"])
brent_eur    = float(letzte_brent["brent_eur"])

# Feature-Vektor
def safe(val, fallback=0.0):
    return float(val) if not pd.isna(val) else fallback

feature_dict = {
    "brent_delta2":       brent_delta2,
    "delta_kern_lag1":    safe(letzte_aral["delta_kern_lag1"]),
    "delta_kern_lag2":    safe(letzte_aral["delta_kern_lag2"]),
    "delta_markt_lag1":   safe(letzte_markt["delta_markt_lag1"]),
    "delta_markt_lag2":   safe(letzte_markt["delta_markt_lag2"]),
    "residuum_lag1":      safe(letzte_res["residuum_lag1"]),
    "tage_seit_erhoehung": float(letzte_aral["tage_seit_erhoehung"]),
    "tage_seit_senkung":   float(letzte_aral["tage_seit_senkung"]),
    "wochentag":           float(letzte_aral["wochentag"]),
    "ist_montag":          float(letzte_aral["ist_montag"]),
    "markt_std":           safe(letzte_markt["markt_std"]),
}

X_live     = pd.DataFrame([feature_dict])[FEATURES]
if modell is not None:
    pred_delta = float(modell.predict(X_live)[0])
else:
    # Fallback ohne .pkl: konservative Schätzung aus jüngsten ARAL/Markt-Lags
    pred_delta = float(np.nanmean([
        feature_dict.get("delta_kern_lag1", 0.0),
        feature_dict.get("delta_kern_lag2", 0.0),
        feature_dict.get("delta_markt_lag1", 0.0),
    ]))
    pred_delta = float(np.clip(pred_delta, -0.03, 0.03))
    print(f"⚠️ Heuristik-Fallback aktiv: pred_delta={pred_delta*100:+.2f} ct")

if pred_delta > SCHWELLE_ANP:
    richtung, empfehlung = "steigt", "heute tanken"
elif pred_delta < -SCHWELLE_ANP:
    richtung, empfehlung = "fällt", "übermorgen tanken"
else:
    richtung, empfehlung = "stabil", "flexibel tanken"

print(f"Prognose: {pred_delta*100:+.2f} ct → {richtung}")

# Prognose-Log
def richtung_klasse(d):
    if d > SCHWELLE_ANP:  return 1
    if d < -SCHWELLE_ANP: return -1
    return 0

prev_delta, prev_datum = None, None
if os.path.exists(PROGNOSE_PATH):
    try:
        prev = json.load(open(PROGNOSE_PATH, encoding="utf-8"))
        prev_delta = prev.get("predicted_delta")
        prev_datum = prev.get("datum")
    except: pass

kern_g  = kern_hist[kern_hist["tag"] == pd.Timestamp(GESTERN)]["kernpreis_p10"].values
kern_vg = kern_hist[kern_hist["tag"] == pd.Timestamp(GESTERN - timedelta(days=1))]["kernpreis_p10"].values

if len(kern_g) > 0 and len(kern_vg) > 0 and prev_delta is not None:
    actual_delta = float(kern_g[0]) - float(kern_vg[0])
    korrekt      = int(richtung_klasse(prev_delta) == richtung_klasse(actual_delta))
    log_exists   = os.path.exists(LOG_PATH)
    bereits = False
    if log_exists:
        with open(LOG_PATH) as f:
            for row in csv.DictReader(f):
                if row.get("datum") == str(GESTERN):
                    bereits = True; break
    if not bereits:
        with open(LOG_PATH, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["datum","predicted_delta","actual_delta","richtung_korrekt"])
            if not log_exists: w.writeheader()
            w.writerow({"datum": str(GESTERN), "predicted_delta": round(prev_delta,5),
                        "actual_delta": round(actual_delta,5), "richtung_korrekt": korrekt})
        print(f"Log: {GESTERN} pred={prev_delta*100:+.2f}ct actual={actual_delta*100:+.2f}ct korrekt={korrekt}")
    else:
        print(f"Log: {GESTERN} bereits vorhanden")
else:
    print(f"Log: Kein Eintrag möglich für {GESTERN}")

# JSON speichern
prognose_json = {
    "datum": str(HEUTE), "timestamp": JETZT.strftime("%Y-%m-%d %H:%M"),
    "station_uuid": STATION_UUID, "station": "ARAL Dürener Str. 407",
    "kernpreis_aktuell": round(kernpreis_heute, 3),
    "markt_median": round(markt_median_live, 3),
    "residuum_heute": round(residuum_live * 100, 2),
    "predicted_delta": round(pred_delta, 5),
    "predicted_delta_cent": round(pred_delta * 100, 2),
    "richtung": richtung, "empfehlung": empfehlung,
    "begruendung": f"Δ Kernpreis roll3 +2T: {pred_delta*100:+.1f} ct",
    "brent_eur": round(brent_eur, 2), "brent_delta2": round(brent_delta2, 3),
    "tage_seit_erhoehung": int(letzte_aral["tage_seit_erhoehung"]),
    "tage_seit_senkung": int(letzte_aral["tage_seit_senkung"]),
    "nrw_stationen_live": len(nrw_preise),
    "modell": metadaten["modell"] if modell is not None else "fallback_heuristik_ohne_pkl",
    "richtung_accuracy_test": metadaten["richtung_accuracy_test"],
    "horizont": metadaten["horizont"],
}

with open(PROGNOSE_PATH, "w", encoding="utf-8") as f:
    json.dump(prognose_json, f, indent=2, ensure_ascii=False)

print(f"\nGespeichert: {PROGNOSE_PATH}")
print(json.dumps(prognose_json, indent=2, ensure_ascii=False))