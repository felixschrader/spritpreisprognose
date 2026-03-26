# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Läuft auf Streamlit Cloud, liest prognose_aktuell.json aus dem Repo

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
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
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# Daten laden
# =========================================
@st.cache_data(ttl=300)  # 5 Minuten Cache
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
    # Letzte 7 Tage
    cutoff = df["date"].max() - pd.Timedelta(days=7)
    df = df[df["date"] >= cutoff]
    # Stundenbins
    df["stunde"] = df["date"].dt.floor("h")
    df = df.groupby("stunde").agg(preis=("diesel", "mean")).reset_index()
    return df

prognose = lade_prognose()
df_plot  = lade_preisverlauf()

# =========================================
# Header
# =========================================
st.title("⛽ Diesel-Preisprognose")
st.caption(f"ARAL Dürener Str. 407, Köln · Stand: {prognose['timestamp']} Uhr")

st.divider()

# =========================================
# Empfehlung — Hauptkarte
# =========================================
empfehlung = prognose["empfehlung"]
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
            padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
    <h1 style='margin:0; font-size: 2.5em;'>{emoji}</h1>
    <h2 style='margin:5px 0;'>{empfehlung.capitalize()}</h2>
    <p style='margin:0; color: #555;'>{begruendung}</p>
</div>
""", unsafe_allow_html=True)

# =========================================
# Metriken — 3 Spalten
# =========================================
col1, col2, col3 = st.columns(3)

with col1:
    dip_peak = prognose["dip_oder_peak"]
    abweichung = prognose["abweichung_t0_24h"]
    delta_str = f"{abweichung:+.3f} €"
    st.metric(
        label="Aktueller Preis",
        value=f"{prognose['preis_aktuell']:.3f} €",
        delta=f"{dip_peak} ({delta_str})",
        delta_color="inverse"
    )

with col2:
    richtung = prognose["richtung_24h"]
    richtung_emoji = "📈" if richtung == "steigt" else "📉"
    st.metric(
        label="Prognose 24h",
        value=f"{richtung_emoji} {richtung}",
        delta=f"Konfidenz: {prognose['konfidenz']:.1f}%",
        delta_color="off"
    )

with col3:
    st.metric(
        label="Ø letzte 24h",
        value=f"{prognose['mean_24h_rueck']:.3f} €",
        delta=f"Volatilität: ±{prognose['volatilitaet_7d']:.3f} €",
        delta_color="off"
    )

st.divider()

# =========================================
# Preisverlauf letzte 7 Tage + Prognose
# =========================================
st.subheader("Preisverlauf — letzte 7 Tage + Prognose 24h")

@st.cache_data(ttl=300)
def lade_preisverlauf_extended():
    df = pd.read_parquet(PARQUET_URL)
    df = df[df["station_uuid"] == STATION_UUID].copy()
    df = df[df["diesel"].notna()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["stunde"] = df["date"].dt.floor("h")
    df = df.groupby("stunde").agg(preis=("diesel", "mean")).reset_index()
    return df

df_ext = lade_preisverlauf_extended()

# --- Tagesverlaufsmuster der letzten 4 Wochen ---
cutoff_4w = df_ext["stunde"].max() - pd.Timedelta(weeks=4)
df_4w     = df_ext[df_ext["stunde"] >= cutoff_4w].copy()
df_4w["stunde_des_tages"] = df_4w["stunde"].dt.hour

# Relativer Stundeneffekt: Abweichung vom Tagesmittel
df_4w["datum"] = df_4w["stunde"].dt.date
tagesmittel    = df_4w.groupby("datum")["preis"].transform("mean")
df_4w["delta"] = df_4w["preis"] - tagesmittel

stundeneffekt = df_4w.groupby("stunde_des_tages")["delta"].mean()

# --- Prognose: ab letztem bekannten Preis ---
letzter_ts    = df_ext["stunde"].max()
letzter_preis = float(df_ext["preis"].iloc[-1])

prognose_ts     = [letzter_ts + pd.Timedelta(hours=i) for i in range(25)]
prognose_preise = [letzter_preis]

for i in range(1, 25):
    stunde_h  = prognose_ts[i].hour
    effekt    = stundeneffekt.get(stunde_h, 0)
    naechster = prognose_preise[-1] + effekt * 0.3  # gedämpft
    prognose_preise.append(naechster)

# --- Letzte 7 Tage für Plot ---
cutoff_7d = df_ext["stunde"].max() - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

fig = go.Figure()

# Historischer Preisverlauf — Stufenlinie
fig.add_trace(go.Scatter(
    x=df_plot["stunde"],
    y=df_plot["preis"],
    mode="lines",
    name="Dieselpreis",
    line=dict(color="#1f77b4", width=2, shape="hv"),  # hv = Stufenlinie
))

# Prognose — gestrichelte Linie
fig.add_trace(go.Scatter(
    x=prognose_ts,
    y=prognose_preise,
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#ff7f0e", width=2, dash="dash", shape="hv"),
))

# Aktueller Preis als Punkt
fig.add_trace(go.Scatter(
    x=[letzter_ts],
    y=[letzter_preis],
    mode="markers",
    name="Aktuell",
    marker=dict(color="red", size=10, symbol="circle"),
    showlegend=False
))

# 24h-Mittel
fig.add_hline(
    y=prognose["mean_24h_rueck"],
    line_dash="dot",
    line_color="gray",
    opacity=0.5,
    annotation_text=f"Ø 24h: {prognose['mean_24h_rueck']:.3f} €",
    annotation_position="bottom right"
)

fig.update_layout(
    xaxis_title="Datum",
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