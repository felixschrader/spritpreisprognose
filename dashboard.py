# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Läuft auf Streamlit Cloud, liest prognose_aktuell.json aus dem Repo

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime
import pytz

# =========================================
# Konfiguration
# =========================================
st.set_page_config(
    page_title="Spritpreis Köln",
    page_icon="⛽",
    layout="centered"
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
JSON_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/prognose_aktuell.json"
PARQUET_URL  = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/tankstellen_preise.parquet"
LOG_URL      = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/preis_live_log.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# Daten laden
# =========================================
@st.cache_data(ttl=300)
def lade_prognose():
    r = requests.get(JSON_URL)
    return r.json()

@st.cache_data(ttl=300)
def lade_preisverlauf():
    df = pd.read_parquet(PARQUET_URL)
    df = df[df["station_uuid"] == STATION_UUID].copy()
    df = df[df["diesel"].notna()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["bin3h"] = df["date"].dt.floor("3h")
    df = df.groupby("bin3h").agg(preis=("diesel", "mean")).reset_index()
    df = df.rename(columns={"bin3h": "stunde"})
    return df

@st.cache_data(ttl=60)
def lade_live_log():
    try:
        df = pd.read_csv(LOG_URL, parse_dates=["timestamp"])
        return df
    except:
        return pd.DataFrame(columns=["timestamp", "preis", "tendenz_24h"])

@st.cache_data(ttl=60)
def lade_aktueller_preis():
    try:
        key = st.secrets["TANKERKOENIG_KEY"]
        url = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={key}"
        r   = requests.get(url, timeout=5)
        d   = r.json()
        return float(d["prices"][STATION_UUID]["diesel"])
    except:
        return None

prognose    = lade_prognose()
df_ext      = lade_preisverlauf()
df_live_raw = lade_live_log()
preis_live  = lade_aktueller_preis()

# =========================================
# Live-Log aufbereiten
# =========================================
# Volle Auflösung für graue Linie
if not df_live_raw.empty and "timestamp" in df_live_raw.columns:
    df_live = df_live_raw[["timestamp", "preis"]].copy()
    df_live = df_live.rename(columns={"timestamp": "stunde"})
    df_live["stunde"] = pd.to_datetime(df_live["stunde"])
    df_live = df_live.sort_values("stunde").drop_duplicates("stunde").reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=["stunde", "preis"])

# Gebinnt für 24h-Mittel-Berechnung
if not df_live.empty:
    df_live_binned = df_live.copy()
    df_live_binned["stunde"] = df_live_binned["stunde"].dt.floor("3h")
    df_live_binned = df_live_binned.groupby("stunde").agg(preis=("preis", "last")).reset_index()
    df_ext = (
        pd.concat([df_ext, df_live_binned])
        .drop_duplicates("stunde", keep="last")
        .sort_values("stunde")
        .reset_index(drop=True)
    )

# =========================================
# Zeitstempel
# =========================================
letzter_ts    = df_ext["stunde"].max()
jetzt_ts      = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live if preis_live else float(prognose["preis_aktuell"])
uhrzeit       = jetzt_ts.strftime("%H:%M")

# =========================================
# Prognose-Wert
# =========================================
delta_erwartet = float(prognose["delta_erwartet"])
if prognose["richtung_24h"] == "fällt":
    delta_erwartet = -abs(delta_erwartet)
else:
    delta_erwartet = abs(delta_erwartet)

prognose_preis = letzter_preis + delta_erwartet
prognose_ende  = jetzt_ts + pd.Timedelta(hours=24)

# =========================================
# Plot-Daten vorbereiten
# =========================================
cutoff_7d = jetzt_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

# Graue Linie: Parquet + Live-Log + aktueller Punkt
df_hist = pd.concat([
    df_plot[["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).drop_duplicates("stunde").sort_values("stunde").reset_index(drop=True)

# Rollierende 24h-Bins rückwärts von jetzt_ts
bin_grenzen = [jetzt_ts - pd.Timedelta(hours=24 * i) for i in range(8, -1, -1)]

df_24h_rows = []
for i in range(len(bin_grenzen) - 1):
    start = bin_grenzen[i]
    ende  = bin_grenzen[i + 1]
    mask  = (df_hist["stunde"] >= start) & (df_hist["stunde"] < ende)
    if mask.sum() > 0:
        mittel = df_hist.loc[mask, "preis"].mean()
        df_24h_rows.append({"stunde": start, "preis": mittel})

df_24h = pd.DataFrame(df_24h_rows).sort_values("stunde").reset_index(drop=True)

# Letzter blauer Bin endet horizontal auf Höhe des roten Punkts
if not df_24h.empty:
    df_24h = pd.concat([
        df_24h,
        pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
    ]).reset_index(drop=True)

# Mittel der letzten 24h
mean_24h = float(df_hist[df_hist["stunde"] >= (jetzt_ts - pd.Timedelta(hours=24))]["preis"].mean())

# =========================================
# Evaluation aus Live-Log
# =========================================
eval_text = None
if not df_live_raw.empty and "tendenz_24h" in df_live_raw.columns:
    df_live_raw["timestamp"] = pd.to_datetime(df_live_raw["timestamp"])
    df_live_sorted = df_live_raw.sort_values("timestamp")
    ziel_ts  = jetzt_ts - pd.Timedelta(hours=24)
    toleranz = pd.Timedelta(minutes=30)
    df_t24   = df_live_sorted[
        (df_live_sorted["timestamp"] >= ziel_ts - toleranz) &
        (df_live_sorted["timestamp"] <= ziel_ts + toleranz)
    ]
    if not df_t24.empty:
        preis_t24   = float(df_t24.iloc[-1]["preis"])
        tendenz_t24 = float(df_t24.iloc[-1]["tendenz_24h"])
        eval_diff   = letzter_preis - (preis_t24 + tendenz_t24)
        eval_text   = f"Eval: {eval_diff:+.3f} €"

# =========================================
# Header
# =========================================
st.title("⛽ Diesel-Preisprognose")
st.caption(f"ARAL Dürener Str. 407, Köln · Stand: {uhrzeit} Uhr")

st.divider()

# =========================================
# Metriken — 3 Spalten
# =========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Ø letzte 24h",
        value=f"{mean_24h:.3f} €",
    )

with col2:
    st.metric(
        label=f"Aktueller Preis ({uhrzeit} Uhr)",
        value=f"{letzter_preis:.3f} €",
        delta=f"{letzter_preis - mean_24h:+.3f} € vs. Ø 24h",
        delta_color="inverse"
    )

with col3:
    tendenz_pfeil = "↑" if prognose["richtung_24h"] == "steigt" else "↓"
    st.metric(
        label="Tendenz nächste 24h",
        value=f"{tendenz_pfeil} {delta_erwartet:+.3f} €",
        help=f"Konfidenz: {prognose['konfidenz']:.1f}%"
    )
    if eval_text:
        st.caption(eval_text)

st.divider()

# =========================================
# Empfehlung
# =========================================
empfehlung  = prognose["empfehlung"]
begruendung = prognose["begruendung"]

if "heute" in empfehlung:
    farbe = "green"
    emoji = "🟢"
elif "morgen" in empfehlung:
    farbe = "orange"
    emoji = "🟡"
else:
    farbe = "red"
    emoji = "🔴"

st.markdown(f"""
<div style='background-color: {"#d4edda" if farbe=="green" else "#fff3cd" if farbe=="orange" else "#f8d7da"};
            padding: 16px 20px; border-radius: 10px; margin-bottom: 20px;'>
    <span style='font-size: 1.3em;'>{emoji}</span>
    <strong style='font-size: 1.1em; margin-left: 8px;'>{empfehlung.capitalize()}</strong>
    <span style='color: #555; margin-left: 12px; font-size: 0.95em;'>{begruendung}</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# =========================================
# Preisverlauf letzte 7 Tage + Prognose
# =========================================
st.subheader("Preisverlauf — letzte 7 Tage + Prognose 24h")

fig = go.Figure()

# Historische Linie — grau, Stufenlinie
fig.add_trace(go.Scatter(
    x=df_hist["stunde"],
    y=df_hist["preis"],
    mode="lines",
    name="Preisverlauf",
    line=dict(color="#aaaaaa", width=1.5, shape="hv"),
))

# 24h-Mittel — blau, Stufenlinie
fig.add_trace(go.Scatter(
    x=df_24h["stunde"],
    y=df_24h["preis"],
    mode="lines",
    name="24h-Mittel",
    line=dict(color="#1f77b4", width=2, shape="hv"),
))

# Prognose — ein 24h-Bin ab jetzt_ts, orange
fig.add_trace(go.Scatter(
    x=[jetzt_ts, prognose_ende],
    y=[prognose_preis, prognose_preis],
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#ff7f0e", width=2, shape="hv"),
))

# Übergangspunkt — aktueller Live-Preis
fig.add_trace(go.Scatter(
    x=[jetzt_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(color="red", size=8, symbol="circle"),
))

# Ø 24h Referenzlinie
fig.add_hline(
    y=mean_24h,
    line_dash="dot",
    line_color="gray",
    opacity=0.5,
    annotation_text=f"Ø 24h: {mean_24h:.3f} €",
    annotation_position="bottom right"
)

# Mitternachts-Separatoren
mitternacht_linien = []
tag = cutoff_7d.normalize()
while tag <= jetzt_ts:
    mitternacht_linien.append(dict(
        type="line",
        x0=tag, x1=tag,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="lightgray", width=1, dash="dot"),
    ))
    tag += pd.Timedelta(days=1)

fig.update_layout(
    shapes=mitternacht_linien,
    xaxis=dict(
        dtick=12 * 3600 * 1000,
        tickformat="%d.%m\n%H:%M",
        tickangle=0,
    ),
    yaxis_title="Preis (€)",
    legend=dict(orientation="h"),
    margin=dict(l=0, r=0, t=10, b=0),
    height=350,
)

st.plotly_chart(fig, use_container_width=True)

# =========================================
# Footer
# =========================================
st.divider()
st.caption(
    f"Modell: XGBoost · Trainingsgenauigkeit: {prognose['modell_accuracy']:.1f}% · "
    f"Prognose wird stündlich aktualisiert"
)