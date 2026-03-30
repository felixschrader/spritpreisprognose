# dashboard.py — Spritpreisprognose ARAL Dürener Str. 407 · Köln
# Streamlit Cloud · DSI Capstone 2026

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(
    page_title="Dieselpreis · Köln",
    page_icon="⛽",
    layout="centered"
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
BASE_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main"
JSON_URL     = f"{BASE_URL}/data/ml/prognose_aktuell.json"
TAGES_URL    = f"{BASE_URL}/data/ml/prognose_tagesbasis.json"
PARQUET_URL  = f"{BASE_URL}/data/tankstellen_preise.parquet"
LOG_URL      = f"{BASE_URL}/data/ml/preis_live_log.csv"
PROG_LOG_URL = f"{BASE_URL}/data/ml/prognose_log.csv"
BRENT_1H_URL = f"{BASE_URL}/data/brent_futures_intraday_1h.csv"
BRENT_DAILY_URL = f"{BASE_URL}/data/brent_futures_daily.csv"
EURUSD_URL   = f"{BASE_URL}/data/eur_usd_rate.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# Öffnungszeiten ARAL Dürener Str. 407
OEFFNUNG_VON = 6   # 06:00 Uhr
OEFFNUNG_BIS = 22  # 22:00 Uhr (letzte angezeigte Stunde: 21:xx)

OEFFNUNGSZEITEN = [
    ("Mo – Fr", "06:00 – 22:00"),
    ("Sa",      "07:00 – 22:00"),
    ("So",      "08:00 – 22:00"),
]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"], .stApp {
    font-family: 'Roboto', sans-serif;
    background-color: #F0F2F5 !important;
    color: #212529; font-size: 16px;
}
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding: 0 0 3rem 0 !important; max-width: 920px !important; }

/* TOPBAR */
.topbar {
    background: #1565C0;
    padding: 1.2rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    margin-bottom: 1.5rem;
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 1rem;
}
.topbar-left { flex: 1; }
.topbar-title {
    font-size: 2.2rem; font-weight: 500;
    color: #FFFFFF; line-height: 1.15;
}
.topbar-addr {
    font-size: 1.1rem; color: rgba(255,255,255,0.92);
    margin-top: 6px;
}
.topbar-hours {
    margin-top: 10px;
    display: flex; flex-direction: column; gap: 3px;
}
.topbar-hours-row {
    font-size: 0.95rem; color: rgba(255,255,255,0.8);
    display: flex; gap: 0.6rem;
}
.topbar-hours-row b { color: rgba(255,255,255,0.95); font-weight: 500; min-width: 60px; }
.topbar-right {
    display: flex; flex-direction: column;
    align-items: flex-end; gap: 0.6rem; flex-shrink: 0;
}
.topbar-time {
    font-family: 'Roboto Mono', monospace;
    font-size: 1rem; color: #FFFFFF;
    background: rgba(0,0,0,0.2);
    padding: 6px 14px; border-radius: 4px;
    white-space: nowrap;
}
.topbar-refresh {
    display: inline-block;
    margin-top: 2px;
    padding: 6px 12px;
    border-radius: 4px;
    background: rgba(255,255,255,0.18);
    color: #FFFFFF !important;
    text-decoration: none !important;
    font-size: 0.88rem;
    font-weight: 500;
}
.topbar-refresh:hover {
    background: rgba(255,255,255,0.28);
}
.stButton > button[kind="primary"] {
    background-color: #1565C0 !important;
    border: 1px solid #1565C0 !important;
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #0D47A1 !important;
    border-color: #0D47A1 !important;
}

/* METRIC CARDS */
.metric-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1rem; margin-bottom: 1.25rem;
}
.card {
    background: #FFFFFF; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.25rem 1.5rem;
}
.card-title {
    font-size: 0.72rem; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #616161; margin-bottom: 0.5rem;
}
.card-value {
    font-size: clamp(2rem, 3vw, 2.6rem);
    font-weight: 300; color: #1A1A1A;
    line-height: 1.1; letter-spacing: -0.01em;
}
.card-value sup { font-size: 0.42em; vertical-align: super; font-weight: 400; color: #757575; }
.card-delta { font-size: 0.88rem; font-weight: 500; margin-top: 0.5rem; }
.delta-green  { color: #2E7D32; }
.delta-red    { color: #C62828; }
.delta-blue   { color: #1565C0; }
.tendenz-val  { font-size: clamp(2.2rem, 3.5vw, 3rem); font-weight: 300; line-height: 1; }
.tendenz-down { color: #2E7D32; }
.tendenz-up   { color: #C62828; }
.tendenz-flat { color: #757575; }

/* EMPFEHLUNG */
.empfehlung-card {
    background: #FFFFFF; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.4rem 1.5rem 1rem 1.5rem;
    border-left: 5px solid #1565C0; margin-bottom: 1.5rem;
}
.empfehlung-card.heute  { border-left-color: #2E7D32; }
.empfehlung-card.morgen { border-left-color: #E65100; }
.empfehlung-card.warten { border-left-color: #C62828; }
.empfehlung-badge {
    display: inline-block; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 4px; margin-bottom: 0.8rem;
}
.badge-heute  { background: #E8F5E9; color: #1B5E20; }
.badge-morgen { background: #FFF3E0; color: #BF360C; }
.badge-warten { background: #FFEBEE; color: #B71C1C; }
.empfehlung-text { font-size: 1.05rem; color: #212121; line-height: 1.7; }
.empfehlung-text strong { color: #1A1A1A; font-weight: 500; }
.ki-footer {
    font-size: 0.78rem; color: #9E9E9E;
    margin-top: 0.9rem; padding-top: 0.7rem;
    border-top: 1px solid #F5F5F5;
}
.ki-footer a { color: #757575; text-decoration: none; }

/* SECTION LABEL */
.section-label {
    font-size: 1rem; font-weight: 500;
    letter-spacing: 0.04em; text-transform: uppercase;
    color: #616161; margin: 1.5rem 0 0.75rem 0;
    padding-bottom: 0.5rem; border-bottom: 2px solid #E0E0E0;
}

/* KPI CARDS */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem; margin-bottom: 1.25rem;
}
.kpi-card {
    background: #FFFFFF; border: 1px solid #E8EAED;
    border-radius: 8px; padding: 1rem; text-align: center;
}
.kpi-val {
    font-family: 'Roboto Mono', monospace;
    font-size: 1.5rem; font-weight: 400; color: #1A1A1A;
}
.kpi-lbl {
    font-size: 0.68rem; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #9E9E9E; margin-top: 4px;
}

/* TAGES-KACHELN — Kalender-Layout */
.kalender-woche {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 4px;
}
.kalender-header {
    text-align: center;
    font-size: 0.68rem; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: #9E9E9E; padding: 4px 0;
}
.tag-kachel {
    border-radius: 6px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 3px; padding: 8px 4px;
    font-size: 0.78rem; font-weight: 500;
}
.tag-kachel.korrekt { background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; }
.tag-kachel.falsch  { background: #FFEBEE; color: #B71C1C; border: 1px solid #EF9A9A; }
.tag-kachel.leer    { background: transparent; border: 1px solid #F0F0F0; }
.tag-symbol { font-size: 1.1rem; }
.tag-datum  { font-size: 0.75rem; font-weight: 600; }
.tag-delta  { font-size: 0.75rem; }

/* TABS */
.stTabs [data-baseweb="tab"] {
    font-size: 1rem !important; font-weight: 500 !important;
    padding: 0.6rem 1.2rem !important;
}

/* FOOTER */
.page-footer {
    margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid #E0E0E0;
    font-size: 0.9rem; color: #757575; line-height: 2.2;
}
.page-footer a { color: #616161; text-decoration: none; }
.page-footer a:hover { text-decoration: underline; }
.page-footer .footer-context {
    margin-top: 0.85rem; margin-bottom: 0.35rem;
    font-size: 0.85rem; line-height: 1.65; color: #616161;
}

@media (max-width: 640px) {
    .metric-grid { grid-template-columns: 1fr; }
    .kpi-grid    { grid-template-columns: repeat(2, 1fr); }
    .topbar      { flex-direction: column; padding: 1rem; }
    .topbar-right { align-items: flex-start; }
    .topbar-title { font-size: 1.6rem; }
    .kalender-woche { grid-template-columns: repeat(4, 1fr); }
}
</style>
""", unsafe_allow_html=True)

# ── Daten laden ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def lade_prognose():
    return requests.get(JSON_URL, timeout=10).json()

@st.cache_data(ttl=300)
def lade_tagesprognose():
    try:
        return requests.get(TAGES_URL, timeout=10).json()
    except:
        return {}

@st.cache_data(ttl=300)
def lade_preisverlauf():
    df = pd.read_parquet(PARQUET_URL)
    df = df[df["station_uuid"] == STATION_UUID].copy()
    df = df[df["diesel"].notna()]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").rename(columns={"date": "stunde", "diesel": "preis"})
    return df[["stunde", "preis"]]

@st.cache_data(ttl=60)
def lade_live_log():
    try:
        return pd.read_csv(LOG_URL, parse_dates=["timestamp"], on_bad_lines="skip")
    except:
        return pd.DataFrame(columns=["timestamp", "preis"])

@st.cache_data(ttl=60)
def lade_aktueller_preis():
    try:
        key = st.secrets["TANKERKOENIG_KEY"]
        url = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={key}"
        return float(requests.get(url, timeout=5).json()["prices"][STATION_UUID]["diesel"])
    except:
        return None

@st.cache_data(ttl=1800)
def lade_prognose_log():
    try:
        df = pd.read_csv(PROG_LOG_URL, parse_dates=["datum"])
        return df.sort_values("datum").reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["datum", "predicted_delta", "actual_delta", "richtung_korrekt"])

@st.cache_data(ttl=900)
def lade_brent_intraday_csv():
    try:
        df = pd.read_csv(BRENT_1H_URL, parse_dates=["period"])
        df = df.rename(columns={"period": "stunde", "brent_futures_usd_1h": "brent_usd"})
        df = df[["stunde", "brent_usd"]].dropna().sort_values("stunde").reset_index(drop=True)
        return df
    except:
        return pd.DataFrame(columns=["stunde", "brent_usd"])

@st.cache_data(ttl=3600)
def lade_brent_daily():
    try:
        df = pd.read_csv(BRENT_DAILY_URL, parse_dates=["period"])
        df = df.rename(columns={"period": "tag", "brent_futures_usd": "brent_usd"})
        df = df[["tag", "brent_usd"]].dropna().sort_values("tag").reset_index(drop=True)
        return df
    except:
        return pd.DataFrame(columns=["tag", "brent_usd"])

@st.cache_data(ttl=3600)
def lade_eurusd():
    """Lädt EURUSD (USD je EUR) direkt aus CSV."""
    try:
        fx = pd.read_csv(EURUSD_URL, parse_dates=["period"])
        fx = fx[["period", "eur_usd"]].dropna().sort_values("period")
        if not fx.empty:
            eur_usd = float(fx.iloc[-1]["eur_usd"])
            if eur_usd > 0:
                return eur_usd
    except:
        pass
    return 1.08

@st.cache_data(ttl=3600)
def generiere_empfehlung(preis, mean_ref, richtung_tage, brent_vs_3d_pct, residuum):
    prompt = f"""Du bist ein nüchterner Datenanalyst. Schreibe genau 2 Sätze auf Deutsch.

Daten:
- Aktueller Preis: {preis:.2f} € ({(preis - mean_ref)*100:+.1f} ct vs. Durchschnitt gestern)
- Tages-Modell (Horizont 2 Tage): Richtung {richtung_tage}
- Brent vs. 3-Tage-Mittel (Werktage): {brent_vs_3d_pct:+.1f} %
- ARAL vs. NRW-Markt: {residuum:+.1f} Cent

Regeln:
- Keine Handlungsempfehlung, kein "tanken", kein "warten"
- Beschreibe nur was die Daten zeigen
- Satz 1: aktuelle Preislage in 1 Satz mit Zahlen
- Satz 2: was das Modell + Brent signalisieren
- Maximal 40 Wörter gesamt, kein Konjunktiv"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 100,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=10
    )
    return r.json()["content"][0]["text"]

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def preis_fmt(p):
    s = f"{p:.3f}"
    return f"{s[:-1]}<sup>{s[-1]}</sup>"

def bold(text):
    return text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

def ist_offen(stunde_h, wochentag):
    """Gibt True zurück wenn die Tankstelle in dieser Stunde geöffnet ist."""
    if wochentag == 5:   # Samstag
        return 7 <= stunde_h < 22
    elif wochentag == 6: # Sonntag
        return 8 <= stunde_h < 22
    else:                # Mo–Fr
        return 6 <= stunde_h < 22

def baue_prognose_linie(jetzt_ts, letzter_preis, kern_preis, pred_delta_cent, hist_28d_df, df_hist_all):
    """
    Prognose mit fixer Tagesform vom letzten vollen Tag (gestern).
    Für heute/morgen/übermorgen wird diese Form wiederverwendet und nur
    in Niveau (max/min) gemäß Modell-Shift verschoben.
    """
    heute_norm = jetzt_ts.normalize()
    gestern_norm = heute_norm - pd.Timedelta(days=1)

    df_gestern = df_hist_all[df_hist_all["stunde"].dt.normalize() == gestern_norm].copy()
    if df_gestern.empty:
        return pd.DataFrame(columns=["stunde", "preis"])

    df_gestern["stunde_h"] = df_gestern["stunde"].dt.hour
    df_gestern["wochentag"] = df_gestern["stunde"].dt.dayofweek
    df_gestern = df_gestern[df_gestern.apply(lambda r: ist_offen(r["stunde_h"], r["wochentag"]), axis=1)].copy()
    if df_gestern.empty:
        return pd.DataFrame(columns=["stunde", "preis"])

    df_g_bin = df_gestern.copy()
    df_g_bin["bin3"] = (df_g_bin["stunde"].dt.hour // 3) * 3
    df_g_bin = df_g_bin.groupby("bin3")["preis"].mean().reset_index().sort_values("bin3")
    if df_g_bin.empty:
        return pd.DataFrame(columns=["stunde", "preis"])

    g_min = float(df_g_bin["preis"].min())
    g_max = float(df_g_bin["preis"].max())
    g_spread = max(g_max - g_min, 0.01)
    df_g_bin["norm"] = (df_g_bin["preis"] - g_min) / g_spread
    norm_map = {int(r["bin3"]): float(r["norm"]) for _, r in df_g_bin.iterrows()}
    default_norm = float(df_g_bin["norm"].mean())

    df_today = df_hist_all[df_hist_all["stunde"].dt.normalize() == heute_norm].copy()
    if not df_today.empty:
        today_max_obs = float(df_today["preis"].max())
    else:
        today_max_obs = float(letzter_preis)
    today_min_target = today_max_obs - g_spread

    pred_delta_eur = pred_delta_cent / 100.0
    tomorrow_max_target = today_max_obs + 0.5 * pred_delta_eur
    overmorrow_max_target = today_max_obs + 1.0 * pred_delta_eur
    tomorrow_min_target = tomorrow_max_target - g_spread
    overmorrow_min_target = overmorrow_max_target - g_spread

    start_ts = jetzt_ts.floor("3h") + timedelta(hours=3)
    ende_exklusiv = (jetzt_ts + timedelta(days=3)).normalize()
    punkte = []
    ts = start_ts

    while ts < ende_exklusiv:
        wd = ts.dayofweek
        h = ts.hour
        if not ist_offen(h, wd):
            ts += timedelta(hours=3)
            continue

        bin3 = (h // 3) * 3
        n = norm_map.get(bin3, default_norm)
        day_offset = (ts.normalize() - heute_norm).days

        if day_offset == 0:
            p_min, p_max = today_min_target, today_max_obs
        elif day_offset == 1:
            p_min, p_max = tomorrow_min_target, tomorrow_max_target
        else:
            p_min, p_max = overmorrow_min_target, overmorrow_max_target

        preis = p_min + n * (p_max - p_min)
        punkte.append({"stunde": ts, "preis": round(float(preis), 4)})
        ts += timedelta(hours=3)

    return pd.DataFrame(punkte)

# ── Daten zusammenführen ──────────────────────────────────────────────────────
prognose    = lade_prognose()
tages       = lade_tagesprognose()
df_ext      = lade_preisverlauf()
df_live_raw = lade_live_log()
preis_live  = lade_aktueller_preis()
df_prog_log = lade_prognose_log()
df_brent_csv = lade_brent_intraday_csv()
df_brent = df_brent_csv
brent_source = "Yahoo Finance Futures (BZ=F)"
df_brent_daily = lade_brent_daily()
eur_usd_fx  = lade_eurusd()

if not df_live_raw.empty and "timestamp" in df_live_raw.columns:
    df_live = df_live_raw[["timestamp", "preis"]].rename(
        columns={"timestamp": "stunde"}).copy()
    df_live["stunde"] = pd.to_datetime(df_live["stunde"])
    df_live = df_live.sort_values("stunde").drop_duplicates("stunde").reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=["stunde", "preis"])

if not df_live.empty:
    binned = df_live.copy()
    binned["stunde"] = binned["stunde"].dt.floor("3h")
    binned = binned.groupby("stunde").agg(preis=("preis", "last")).reset_index()
    df_ext = pd.concat([df_ext, binned]).drop_duplicates(
        "stunde", keep="last").sort_values("stunde").reset_index(drop=True)

jetzt_ts      = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live if preis_live else float(prognose.get("preis_aktuell", 0))
uhrzeit       = jetzt_ts.strftime("%H:%M")

# Tages-Prognose
richtung_tage   = tages.get("richtung", "—")
empfehlung_tage = tages.get("empfehlung", "—")
brent_delta2    = float(tages.get("brent_delta2", 0))
residuum_cent   = float(tages.get("residuum_heute", 0))
pred_delta_cent = float(tages.get("predicted_delta_cent", 0))
kern_preis      = float(tages.get("kernpreis_aktuell", letzter_preis))

# Historische Basis (28 Tage)
cutoff_7d  = jetzt_ts - pd.Timedelta(days=7)
cutoff_28d = jetzt_ts - pd.Timedelta(days=28)

df_hist_all = pd.concat([
    df_ext[df_ext["stunde"] >= cutoff_7d][["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty
        else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).sort_values("stunde").drop_duplicates("stunde", keep="last").reset_index(drop=True)

# Öffnungszeiten-Filter für Historik
df_hist = df_hist_all.copy()
df_hist["stunde_h"]  = df_hist["stunde"].dt.hour
df_hist["wochentag"] = df_hist["stunde"].dt.dayofweek
df_hist = df_hist[df_hist.apply(
    lambda r: ist_offen(r["stunde_h"], r["wochentag"]), axis=1
)].reset_index(drop=True)

# Rolling 28-Tage Basis für Prognoseprofil
hist_28d = df_ext[df_ext["stunde"] >= cutoff_28d].copy()

# Prognose-Linie
df_prognose_linie = baue_prognose_linie(
    jetzt_ts, letzter_preis, kern_preis,
    pred_delta_cent, hist_28d, df_hist_all
)

# 3h-Bins für Prognose-Darstellung
if not df_prognose_linie.empty:
    df_prognose_bin = df_prognose_linie.copy().sort_values("stunde").reset_index(drop=True)
else:
    df_prognose_bin = pd.DataFrame(columns=["stunde", "preis"])

# Referenz-Basis: Durchschnitt gestern (robuster für frühe Tagesstunden).
start_heute = jetzt_ts.normalize()
start_gestern = start_heute - pd.Timedelta(days=1)
df_yesterday = df_hist_all[
    (df_hist_all["stunde"] >= start_gestern) & (df_hist_all["stunde"] < start_heute)
].copy()
if df_yesterday.empty:
    mean_ref = float(letzter_preis)
else:
    mean_ref = float(df_yesterday["preis"].mean())

# Brent-Referenz: Prozent ggü. 3-Tage-Mittel (letzte 3 Werktage)
# "Aktuell" immer aus der gezeigten Brent-Reihe (Futures), nicht aus Tages-JSON.
brent_eur_aktuell = np.nan
if not df_brent.empty:
    brent_eur_aktuell = float(df_brent.iloc[-1]["brent_usd"]) / eur_usd_fx
else:
    brent_eur_aktuell = float(tages.get("brent_eur", np.nan))

if not df_brent_daily.empty:
    df_bd = df_brent_daily.copy()
    df_bd["wd"] = df_bd["tag"].dt.dayofweek
    df_bd = df_bd[df_bd["wd"] < 5]
    if len(df_bd) >= 3:
        brent_3d_mean_eur = float(df_bd.tail(3)["brent_usd"].mean()) / eur_usd_fx
    else:
        brent_3d_mean_eur = brent_eur_aktuell
else:
    brent_3d_mean_eur = brent_eur_aktuell
brent_vs_3d_pct = float((brent_eur_aktuell / brent_3d_mean_eur - 1.0) * 100) if (
    (not np.isnan(brent_eur_aktuell)) and brent_3d_mean_eur and brent_3d_mean_eur > 0
) else 0.0

# KI-Empfehlung
try:
    ki_text = generiere_empfehlung(
        letzter_preis, mean_ref,
        richtung_tage,
        brent_vs_3d_pct, residuum_cent
    )
except:
    ki_text = tages.get("begruendung", "Keine Prognose verfügbar.")

# Empfehlungs-Klasse
if "heute" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", "Jetzt tanken"
elif "übermorgen" in empfehlung_tage or "später" in empfehlung_tage or "warten" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "morgen", "badge-morgen", "Warten"
elif "flexibel" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", "Flexibel"
else:
    card_cls, badge_cls, badge_txt = "warten", "badge-warten", "Abwarten"

# ── TOPBAR ────────────────────────────────────────────────────────────────────
oeff_rows = "".join(
    f'<div class="topbar-hours-row"><b>{tag}</b> {zeiten}</div>'
    for tag, zeiten in OEFFNUNGSZEITEN
)
st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-title">Dieselpreisprognose</div>
        <div class="topbar-addr">ARAL · Dürener Str. 407 · 50931 Köln-Lindenthal</div>
        <div class="topbar-hours">{oeff_rows}</div>
    </div>
    <div class="topbar-right">
        <span class="topbar-time">Live · {uhrzeit} Uhr</span>
        <a class="topbar-refresh" href="?refresh=1">↺ Aktualisieren</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Refresh via Query-Parameter (Button sitzt im blauen Top-Block)
if st.query_params.get("refresh") == "1":
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

# ── METRIKEN ──────────────────────────────────────────────────────────────────
delta_val   = letzter_preis - mean_ref
delta_cent  = delta_val * 100
delta_cls  = "delta-green" if delta_val < 0 else "delta-red"
delta_sign = "−" if delta_val < 0 else "+"

if richtung_tage == "fällt":
    tend_pfeil, tend_cls = "↓", "tendenz-down"
    tend_sub = f"Preis fällt bis übermorgen · {pred_delta_cent:+.1f} ct"
elif richtung_tage == "steigt":
    tend_pfeil, tend_cls = "↑", "tendenz-up"
    tend_sub = f"Preis steigt bis übermorgen · {pred_delta_cent:+.1f} ct"
else:
    tend_pfeil, tend_cls = "→", "tendenz-flat"
    tend_sub = "Kein klares Signal"

st.markdown(f"""
<div class="metric-grid">
    <div class="card">
        <div class="card-title">Ø gestern</div>
        <div class="card-value">{preis_fmt(mean_ref)} &euro;</div>
    </div>
    <div class="card">
        <div class="card-title">Aktueller Preis · {uhrzeit} Uhr</div>
        <div class="card-value">{preis_fmt(letzter_preis)} &euro;</div>
        <div class="card-delta {delta_cls}">{delta_sign} {abs(delta_cent):.1f} ct vs. Ø gestern</div>
    </div>
    <div class="card">
        <div class="card-title">Tages-Prognose · übermorgen</div>
        <div class="tendenz-val {tend_cls}">{tend_pfeil}</div>
        <div class="card-delta delta-blue">{tend_sub}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── EMPFEHLUNG ────────────────────────────────────────────────────────────────
# Farbe der Empfehlung-Card basiert auf Richtung, nicht Empfehlung
if richtung_tage == "fällt":
    emp_border = "#2E7D32"
elif richtung_tage == "steigt":
    emp_border = "#C62828"
else:
    emp_border = "#1565C0"

st.markdown(f"""
<div class="empfehlung-card" style="border-left-color: {emp_border}">
    <div class="empfehlung-text">{ki_text}</div>
    <div class="ki-footer">
        KI-generiert · <a href="https://www.anthropic.com" target="_blank">Claude API · Anthropic</a> · Keine Garantie
    </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Preisverlauf", "🔍 KPIs", "📊 Modell-Performance"])

# ─── TAB 1: Preisverlauf ─────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-label">Preisverlauf — 7 Tage + Prognose bis übermorgen</div>',
                unsafe_allow_html=True)
    st.caption("Darstellung in 3h-Bins · Nur Öffnungszeiten (Mo–Fr 06–22h, Sa 07–22h, So 08–22h)")
    show_brent = st.toggle("Brent-Preis anzeigen", value=False, key="show_brent_line")
    if show_brent:
        if not df_brent.empty:
            letzter_brent = pd.to_datetime(df_brent["stunde"]).max()
            st.caption(f"Brent-Quelle: {brent_source} · Letzter Stand: {letzter_brent.strftime('%d.%m.%Y %H:%M')}")
        else:
            st.caption(f"Brent-Quelle: {brent_source} · Keine Daten verfügbar")

    # 3h-Bins für historischen Verlauf
    df_hist_bin = df_hist.copy()
    df_hist_bin["stunde_bin"] = df_hist_bin["stunde"].dt.floor("3h")
    df_hist_bin = df_hist_bin.groupby("stunde_bin")["preis"].mean().reset_index()
    df_hist_bin = df_hist_bin.rename(columns={"stunde_bin": "stunde"})

    fig = go.Figure()
    aktueller_bin_start = jetzt_ts.floor("3h")
    aktueller_bin_ende = aktueller_bin_start + pd.Timedelta(hours=3)
    fig.add_trace(go.Scatter(
        x=df_hist_bin["stunde"], y=df_hist_bin["preis"],
        mode="lines", name="Preisverlauf Diesel",
        line=dict(color="#BDBDBD", width=1.5, shape="hv"),
    ))

    # Optional: Brent-Futures als Linie (EUR/Barrel), nur bis letztem bekannten Datenpunkt.
    if show_brent and not df_brent.empty:
        df_brent_plot = df_brent[df_brent["stunde"] >= cutoff_7d].copy()
        if not df_brent_plot.empty:
            df_brent_plot = df_brent_plot.sort_values("stunde").reset_index(drop=True)
            df_brent_plot["brent_eur"] = df_brent_plot["brent_usd"] / eur_usd_fx
            fig.add_trace(go.Scatter(
                x=df_brent_plot["stunde"],
                y=df_brent_plot["brent_eur"],
                mode="lines",
                name="Brent in Euro pro Barrel",
                yaxis="y2",
                line=dict(color="#2E7D32", width=1.3),
            ))
    # Aktuellen Bin bis zum rechten Rand "schließen" und dort auf den Live-Preis springen.
    df_bin_now = df_hist_bin[df_hist_bin["stunde"] <= aktueller_bin_start]
    if not df_bin_now.empty:
        aktueller_bin_preis = float(df_bin_now.iloc[-1]["preis"])
        fig.add_trace(go.Scatter(
            x=[aktueller_bin_start, aktueller_bin_ende, aktueller_bin_ende],
            y=[aktueller_bin_preis, aktueller_bin_preis, letzter_preis],
            mode="lines", showlegend=False,
            line=dict(color="#BDBDBD", width=1.5, shape="hv"),
            hoverinfo="skip",
        ))

    # Tages-Mittelwert (Kalendertag). Für heute: bis "jetzt".
    # Darstellung nur innerhalb der Öffnungszeiten (keine "Nacht-Linie").
    # Start/Ende werden an sichtbare 3h-Bins gekoppelt, damit nichts "verschoben" wirkt.
    df_hist_day = df_hist_all.copy()
    df_hist_day["tag"] = df_hist_day["stunde"].dt.normalize()
    if not df_hist_day.empty:
        heute_norm = jetzt_ts.normalize()
        df_past = df_hist_day[df_hist_day["tag"] < heute_norm]
        df_hist_bin_day = df_hist_bin.copy()
        df_hist_bin_day["tag"] = df_hist_bin_day["stunde"].dt.normalize()
        bin_bounds = (
            df_hist_bin_day.groupby("tag")["stunde"]
            .agg(first_bin="min", last_bin="max")
            .reset_index()
        )
        bin_bounds_dict = {
            row["tag"]: (row["first_bin"], row["last_bin"])
            for _, row in bin_bounds.iterrows()
        }

        df_day_med_parts = []
        if not df_past.empty:
            df_day_med_parts.append(
                df_past.groupby("tag")["preis"].mean().reset_index(name="preis")
            )

        if df_day_med_parts:
            df_day_mean = pd.concat(df_day_med_parts, ignore_index=True).sort_values("tag")

            def oeffnung_ende(tag_ts: pd.Timestamp):
                wd = tag_ts.dayofweek
                # Anzeige/Öffnung bis 22:00 (letzte Stunde 21:xx)
                ende_h = 22
                return tag_ts + pd.Timedelta(hours=ende_h)

            # Baue horizontale Segmente pro Tag (open -> close) und trenne Tage mit None.
            x_seg, y_seg = [], []
            for _, row in df_day_mean.iterrows():
                tag_ts = pd.Timestamp(row["tag"])
                preis_tag = float(row["preis"])
                bounds = bin_bounds_dict.get(tag_ts)
                if not bounds:
                    continue
                start_ts, last_bin_ts = bounds
                ende_ts = min(last_bin_ts + pd.Timedelta(hours=3), oeffnung_ende(tag_ts))

                x_seg.extend([start_ts, ende_ts, None])
                y_seg.extend([preis_tag, preis_tag, None])

            if x_seg:
                fig.add_trace(go.Scatter(
                    x=x_seg, y=y_seg,
                    mode="lines", name="Tages-Ø",
                    line=dict(color="#1565C0", width=2.5),
                    connectgaps=False,
                ))

    # Prognose-Linie (3h-Bins, bis Mitternacht übermorgen)
    if not df_prognose_bin.empty:
        # Verbindungspunkt: aktueller Preis am rechten Rand des aktuellen 3h-Bins
        df_prog_future = df_prognose_bin[df_prognose_bin["stunde"] >= aktueller_bin_ende].copy()
        df_prog_plot = pd.concat([
            pd.DataFrame([{"stunde": aktueller_bin_ende, "preis": letzter_preis}]),
            df_prog_future
        ]).reset_index(drop=True)
        fig.add_trace(go.Scatter(
            x=df_prog_plot["stunde"], y=df_prog_plot["preis"],
            mode="lines", name="Prognose (3h-Bin)",
            line=dict(color="#E65100", width=2, shape="hv", dash="dot"),
        ))

    # Aktueller Preis als Punkt am Bin-Ende (sauberer Übergang zur Prognose)
    fig.add_trace(go.Scatter(
        x=[aktueller_bin_ende], y=[letzter_preis],
        mode="markers", showlegend=False,
        marker=dict(color="#FFFFFF", size=10, symbol="circle",
                    line=dict(color="#1565C0", width=2.5)),
    ))
    fig.add_vline(x=jetzt_ts, line_width=1, line_dash="dash", line_color="#BDBDBD")

    # Mitternacht-Linien
    mitternacht = []
    tag = cutoff_7d.normalize()
    uebermorgen_mitternacht = (jetzt_ts + pd.Timedelta(days=2)).normalize()
    while tag <= uebermorgen_mitternacht:
        mitternacht.append(dict(type="line", x0=tag, x1=tag, y0=0, y1=1,
                                xref="x", yref="paper",
                                line=dict(color="#EEEEEE", width=1)))
        tag += pd.Timedelta(days=1)

    fig.update_layout(
        shapes=mitternacht, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        font=dict(family="Roboto", size=13, color="#757575"),
        xaxis=dict(dtick=24*3600*1000, tick0="2020-01-01 12:00:00",
                   tickformat="%d.%m.", tickangle=0,
                   tickfont=dict(size=13, color="#9E9E9E"),
                   gridcolor="#F5F5F5", showline=True, linecolor="#E0E0E0", zeroline=False),
        xaxis_rangeslider_visible=False,
        yaxis=dict(
            tickfont=dict(size=13, color="#9E9E9E"),
            gridcolor="#F5F5F5",
            zeroline=False,
            ticksuffix=" €",
            tickformat=".2f",
            title="Preisverlauf Diesel"
        ),
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            tickfont=dict(size=12, color="#8D6E63"),
            ticksuffix=" €",
            tickformat=".2f",
            title="Brent in Euro pro Barrel"
        ),
        legend=dict(orientation="h", y=-0.18, font=dict(size=13, color="#757575"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=20, t=15, b=10),
        height=380, hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#E0E0E0",
                        font=dict(color="#212529", size=13, family="Roboto")),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── TAB 2: Algo-KPIs ────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-label">Analyse — letzte 14 Tage (ohne heute)</div>',
                unsafe_allow_html=True)

    cutoff_14d = jetzt_ts.normalize() - pd.Timedelta(days=14)
    heute_datum = jetzt_ts.normalize().date()

    # Nur vollständige Tage (heute ausgeschlossen)
    df_14 = df_hist[
        (df_hist["stunde"] >= cutoff_14d) &
        (df_hist["stunde"].dt.date < heute_datum)
    ].copy().sort_values("stunde")
    df_14["delta"]    = df_14["preis"].diff()
    df_14["tag"]      = df_14["stunde"].dt.date
    df_14["stunde_h"] = df_14["stunde"].dt.hour

    aend_tag = df_14.groupby("tag")["delta"].count().mean() if not df_14.empty else 0.0

    # Volatilität je Tag (inkl. Morning-Spike)
    df_ext_14 = df_ext[
        (df_ext["stunde"] >= cutoff_14d) &
        (df_ext["stunde"].dt.date < heute_datum)
    ].copy()
    df_ext_14["tag_v"] = df_ext_14["stunde"].dt.date
    df_vol = df_ext_14.groupby("tag_v")["preis"].std().reset_index() if not df_ext_14.empty else pd.DataFrame(columns=["tag_v", "preis"])
    volatilitaet = float(df_vol["preis"].mean()) if not df_vol.empty else 0.0

    # Morning-Spike vs Closing Abstand je Tag (Morning - Closing), je Tag aus echten Tagespunkten
    df_mc = df_ext_14.copy()
    df_mc["stunde_h"] = df_mc["stunde"].dt.hour
    df_mc["tag"] = df_mc["stunde"].dt.date
    df_mc = df_mc.sort_values("stunde")
    if not df_mc.empty:
        df_morning = df_mc.groupby("tag").first().reset_index()[["tag", "preis"]].rename(columns={"preis": "preis_morning"})
        df_closing = df_mc.groupby("tag").last().reset_index()[["tag", "preis"]].rename(columns={"preis": "preis_closing"})
        df_mc_delta = df_morning.merge(df_closing, on="tag", how="inner")
    else:
        df_mc_delta = pd.DataFrame(columns=["tag", "preis_morning", "preis_closing"])
    if not df_mc_delta.empty:
        df_mc_delta["abstand_ct"] = (df_mc_delta["preis_morning"] - df_mc_delta["preis_closing"]) * 100
        avg_abstand_ct = float(df_mc_delta["abstand_ct"].mean())
    else:
        avg_abstand_ct = 0.0

    # KPI-Cards (nur die 3 gewünschten Kennzahlen)
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1.25rem">
        <div class="kpi-card"><div class="kpi-val">{aend_tag:.1f}</div><div class="kpi-lbl">Ø Änderungen/Tag (14T)</div></div>
        <div class="kpi-card"><div class="kpi-val">{volatilitaet*100:.1f}<span style="font-size:0.75rem"> ct</span></div><div class="kpi-lbl">Ø Volatilität/Tag (14T)</div></div>
        <div class="kpi-card"><div class="kpi-val">{avg_abstand_ct:.1f}<span style="font-size:0.75rem"> ct</span></div><div class="kpi-lbl">Ø Morning−Closing (14T)</div></div>
    </div>
    """, unsafe_allow_html=True)

    df_tag = df_14.groupby("tag").agg(
        n_aenderungen=("delta", "count"),
    ).reset_index()
    df_tag["tag"] = pd.to_datetime(df_tag["tag"])

    BASE_L = dict(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                  margin=dict(l=10, r=10, t=10, b=10),
                  legend=dict(orientation="h", y=-0.35, font=dict(size=12)),
                  xaxis=dict(gridcolor="#F5F5F5"))

    # Änderungen/Tag
    st.markdown('<div class="section-label">Änderungen pro Tag — täglich</div>',
                unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df_tag["tag"], y=df_tag["n_aenderungen"],
        mode="lines", name="Ändg/Tag", line=dict(color="#1565C0", width=1.5)))
    fig3.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False))
    st.plotly_chart(fig3, use_container_width=True)

    # Volatilität (ganzer Tag, inkl. Morning-Spike)
    st.markdown('<div class="section-label">Tägliche Preisvolatilität — ganzer Tag</div>',
                unsafe_allow_html=True)
    df_vol["tag_v"] = pd.to_datetime(df_vol["tag_v"])
    fig6_kpi = go.Figure()
    fig6_kpi.add_trace(go.Scatter(x=df_vol["tag_v"], y=df_vol["preis"]*100,
        mode="lines", name="Volatilität",
        line=dict(color="#E65100", width=1.5),
        fill="tozeroy", fillcolor="rgba(230,81,0,0.08)"))
    fig6_kpi.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"))
    st.plotly_chart(fig6_kpi, use_container_width=True)

    # Morning-Spike vs. Closing Abstand (heute ausgeschlossen)
    st.markdown('<div class="section-label">Abstand Morning-Spike − Closing — täglich</div>',
                unsafe_allow_html=True)
    df_mc_delta["tag"] = pd.to_datetime(df_mc_delta["tag"])
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df_mc_delta["tag"], y=df_mc_delta["abstand_ct"],
        mode="lines+markers", name="Closing − Morning",
        line=dict(color="#6A1B9A", width=1.5), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(106,27,154,0.08)"
    ))
    fig4.update_layout(**BASE_L, height=220,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct", rangemode="tozero"))
    st.plotly_chart(fig4, use_container_width=True)

# ─── TAB 3: Modell-Performance ───────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-label">Retrograde Bewertung — Tages-Prognose</div>',
                unsafe_allow_html=True)
    st.caption("""**Zielvariable:** Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage.
Kernpreis = p10 der Stundenbins 13–20 Uhr.
**Richtung korrekt** = Predicted und Actual auf gleicher Seite der ±0.5ct Schwelle.
**MAE** = durchschnittliche Abweichung Predicted vs. Actual in Cent.""")

    if df_prog_log.empty:
        st.info("Noch keine Log-Daten verfügbar.")
    else:
        heute_dt = jetzt_ts.normalize()
        start_laufende_woche = heute_dt - pd.Timedelta(days=heute_dt.dayofweek)
        # Letzte 3 vollständige Kalenderwochen (Mo–So), ohne laufende Woche
        first_day_3voll = start_laufende_woche - pd.Timedelta(weeks=3)
        last_day_3voll = start_laufende_woche - pd.Timedelta(days=1)

        df_log_3w = df_prog_log[
            (df_prog_log["datum"] >= first_day_3voll) & (df_prog_log["datum"] <= last_day_3voll)
        ].copy().sort_values("datum")
        df_log_14 = df_prog_log[df_prog_log["datum"] >= (heute_dt - pd.Timedelta(days=14))].copy().sort_values("datum")

        n_tage    = len(df_log_3w)
        n_korrekt = int(df_log_3w["richtung_korrekt"].sum()) if n_tage > 0 else 0
        acc_3w    = df_log_3w["richtung_korrekt"].mean() * 100 if n_tage > 0 else 0
        mae_3w    = df_log_3w["actual_delta"].sub(
            df_log_3w["predicted_delta"]).abs().mean() * 100 if n_tage > 0 else 0

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-val">{acc_3w:.1f}<span style="font-size:0.75rem">%</span></div>
                <div class="kpi-lbl">Richtungs-Acc. (3W)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{n_korrekt}/{n_tage}</div>
                <div class="kpi-lbl">Korrekt / 3W</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{mae_3w:.2f}<span style="font-size:0.75rem"> ct</span></div>
                <div class="kpi-lbl">MAE (3W)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">67.9<span style="font-size:0.75rem">%</span></div>
                <div class="kpi-lbl">Acc. Test-Set</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Methodik der Modellbewertung"):
            st.markdown("""
            **Zielgröße und Horizont**
            - Bewertet wird die Tages-Prognose für den **Kernpreis** mit einem Horizont von **2 Tagen**.
            - Die Richtung (steigt/fällt/stabil) wird über eine Stabilitätsschwelle von **±0.5 ct** klassifiziert.

            **Datenbasis für diese Ansicht**
            - **Richtungs-Acc. (3W), Korrekt/3W, MAE (3W):** letzte **3 vollständige** Kalenderwochen (Mo–So), ohne die laufende Woche.
            - **Predicted vs. Actual:** letzte 14 Tage.

            **Kennzahlen**
            - **Richtungs-Acc. (3W):** Anteil korrekter Richtungsprognosen in Prozent.
            - **Korrekt / 3W:** absolute Trefferzahl im betrachteten 3-Wochen-Fenster.
            - **MAE (3W):** mittlere absolute Abweichung zwischen vorhergesagtem und tatsächlichem Delta (in ct).
            - **Acc. Test-Set:** Offline-Benchmark aus der Modellentwicklung (statischer Referenzwert).

            **Hinweis zur Interpretation**
            - Kurze Zeitfenster reagieren stärker auf Ausreißer und Regimewechsel.
            - Deshalb werden Trend (Richtung), Fehlermaß (MAE) und Wochen-Trefferquote gemeinsam gezeigt.
            """)

        # Wöchentliche Trefferquote: 3 letzte vollständige Wochen (Mo–So), Schlüssel = Wochenende So.
        sonntage_3voll = pd.to_datetime([
            start_laufende_woche - pd.Timedelta(days=15),
            start_laufende_woche - pd.Timedelta(days=8),
            start_laufende_woche - pd.Timedelta(days=1),
        ]).normalize()
        df_week = df_log_3w.copy()
        if not df_week.empty:
            d = df_week["datum"].dt.normalize()
            df_week["wochenende_so"] = d + pd.to_timedelta((6 - d.dt.dayofweek) % 7, unit="D")
            df_week_acc = df_week.groupby("wochenende_so", as_index=False).agg(
                acc_frac=("richtung_korrekt", "mean"),
                n_tage=("richtung_korrekt", "count"),
            )
            df_week_acc["acc_pct"] = df_week_acc["acc_frac"] * 100.0
            df_week_acc = df_week_acc.drop(columns=["acc_frac"])
        else:
            df_week_acc = pd.DataFrame(columns=["wochenende_so", "acc_pct", "n_tage"])

        df_plot = pd.DataFrame({"wochenende_so": sonntage_3voll})
        df_plot = df_plot.merge(df_week_acc, on="wochenende_so", how="left")
        df_plot["n_tage"] = df_plot["n_tage"].fillna(0).astype(int)
        df_plot["acc_pct"] = df_plot["acc_pct"].where(df_plot["n_tage"] > 0)
        bar_text = [
            f"{v:.0f} %" if pd.notna(v) else "—"
            for v in df_plot["acc_pct"]
        ]
        st.markdown('<div class="section-label">Wöchentliche Trefferquote — letzte 3 vollständige Wochen (So)</div>',
                    unsafe_allow_html=True)
        fig_week = go.Figure()
        fig_week.add_trace(go.Bar(
            x=df_plot["wochenende_so"], y=df_plot["acc_pct"],
            name="Trefferquote", marker_color="#1565C0",
            text=bar_text, textposition="outside", textfont=dict(size=11, color="#424242"),
        ))
        fig_week.update_layout(
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=220,
            margin=dict(l=10, r=10, t=28, b=10),
            xaxis=dict(
                gridcolor="#F5F5F5", tickformat="%d.%m.",
                tickmode="array", tickvals=df_plot["wochenende_so"], ticktext=[
                    f"So {ts.strftime('%d.%m.')} ({n} T.)" for ts, n in zip(df_plot["wochenende_so"], df_plot["n_tage"])
                ],
            ),
            yaxis=dict(gridcolor="#F5F5F5", zeroline=False, range=[0, 100], ticksuffix=" %"),
            showlegend=False
        )
        st.plotly_chart(fig_week, use_container_width=True)

        # Kalender
        st.markdown('<div class="section-label">Prognose-Trefferquote — letzte 3 vollständige Wochen</div>',
                    unsafe_allow_html=True)
        st.caption("Grün = Richtung korrekt · Rot = falsch · P = predicted Δ · A = actual Δ · Schwelle: ±0.5 ct")

        def rich_pfeil(delta_ct):
            if delta_ct > 0.5:  return "↑"
            if delta_ct < -0.5: return "↓"
            return "→"

        heute           = jetzt_ts.date()
        fd = pd.Timestamp(first_day_3voll).date()
        ld = pd.Timestamp(last_day_3voll).date()
        alle_tage = [fd + timedelta(days=i) for i in range((ld - fd).days + 1)]
        log_dict = {row["datum"].date(): row for _, row in df_prog_log.iterrows()}

        header_html = '<div class="kalender-woche">' + \
            "".join(f'<div class="kalender-header">{w}</div>'
                    for w in ["Mo","Di","Mi","Do","Fr","Sa","So"]) + "</div>"
        st.markdown(header_html, unsafe_allow_html=True)

        wochen, woche_aktuell = [], []
        for tag in alle_tage:
            woche_aktuell.append(tag)
            if tag.weekday() == 6:
                wochen.append(woche_aktuell)
                woche_aktuell = []
        if woche_aktuell:
            wochen.append(woche_aktuell)

        for woche in wochen:
            erster_wt  = woche[0].weekday()
            letzter_wt = woche[-1].weekday()
            woche_html = '<div class="kalender-woche">'
            for _ in range(erster_wt):
                woche_html += '<div class="tag-kachel leer"></div>'
            for tag in woche:
                if tag in log_dict:
                    row   = log_dict[tag]
                    korr  = int(row["richtung_korrekt"])
                    cls   = "korrekt" if korr == 1 else "falsch"
                    p_ct  = row["predicted_delta"] * 100
                    a_ct  = row["actual_delta"] * 100
                    p_pf  = rich_pfeil(p_ct)
                    a_pf  = rich_pfeil(a_ct)
                    datum = tag.strftime("%d.%m")
                    woche_html += f"""<div class="tag-kachel {cls}" style="min-height:72px">
                        <span class="tag-datum">{datum}</span>
                        <span class="tag-delta">P {p_pf} {p_ct:+.1f}</span>
                        <span class="tag-delta">A {a_pf} {a_ct:+.1f}</span>
                    </div>"""
                elif tag <= heute:
                    woche_html += f"""<div class="tag-kachel leer">
                        <span class="tag-datum">{tag.strftime('%d.%m')}</span>
                    </div>"""
                else:
                    woche_html += '<div class="tag-kachel leer"></div>'
            for _ in range(6 - letzter_wt):
                woche_html += '<div class="tag-kachel leer"></div>'
            woche_html += "</div>"
            st.markdown(woche_html, unsafe_allow_html=True)

        # Predicted vs. Actual — letzte 14 Tage
        st.markdown('<div class="section-label">Predicted vs. Actual Delta — letzte 14 Tage (Cent)</div>',
                    unsafe_allow_html=True)
        if not df_log_14.empty:
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Scatter(
                x=df_log_14["datum"], y=df_log_14["predicted_delta"]*100,
                mode="lines+markers", name="Predicted",
                line=dict(color="#1565C0", width=2), marker=dict(size=5),
            ))
            fig_perf.add_trace(go.Scatter(
                x=df_log_14["datum"], y=df_log_14["actual_delta"]*100,
                mode="lines+markers", name="Actual",
                line=dict(color="#E65100", width=2), marker=dict(size=5),
            ))
            fig_perf.add_hrect(y0=-0.5, y1=0.5,
                               fillcolor="#F5F5F5", opacity=0.6, line_width=0)
            fig_perf.add_hline(y=0, line_dash="dash", line_color="#CCCCCC", line_width=1)
            fig_perf.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=-0.25, font=dict(size=12)),
                xaxis=dict(gridcolor="#F5F5F5", tickformat="%d.%m."),
                yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_perf, use_container_width=True)
            st.caption("Grauer Bereich = ±0.5 ct Stabilitätsschwelle")
        else:
            st.info("Noch nicht genug Daten.")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-footer">
    Preisinformationen: <a href="https://tankerkoenig.de" target="_blank">Tankerkönig</a>
    · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a>
    · Quelle: MTS-K (Markttransparenzstelle für Kraftstoffe)<br>
    Modell: Random Forest Regressor (scikit-learn)
    · Zielvariable: Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage
    · Richtungs-Accuracy Test-Set: 67.9% · Baseline: 38.6%
    · Schwelle "stabil": ±0.5 Cent · Trainingsperiode: 2019–2023<br>
    Prognose täglich 09:00 UTC via GitHub Actions (Berlin: 10:00/11:00)<br>
    · <a href="https://github.com/felixschrader/spritpreisprognose" target="_blank">GitHub</a>
    · LinkedIn:
    <a href="https://www.linkedin.com/in/felixschrader/" target="_blank">Felix Schrader</a>,
    <a href="https://www.linkedin.com/in/girandoux-fandio-08628bb9/" target="_blank">Girandoux Fandio Nganwajop</a>,
    <a href="https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo" target="_blank">Ghislain Wamo</a><br>
    <div class="footer-context">
        Dieses Projekt entstand im Rahmen der sechsmonatigen Weiterbildung Data Science; die Abschlussarbeit wurde in der Zeit vom 16. bis 27. März 2026 erstellt.
        Es wendet erlernte Tools und Denkweisen bewusst in der Praxis an.
        Das Dashboard ist ein MVP im Sinne eines Prototyps und offen für eine Weiterentwicklung, die weitere Zusammenhänge in der Preisfindung von Kraftstoffpreisen einbeziehen kann.
    </div>
    <a href="https://data-science-institute.de/" target="_blank">DSI — Data Science Institute by Fabian Rappert</a>
    · Capstone 2026
</div>
""", unsafe_allow_html=True)