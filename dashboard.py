# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Läuft auf Streamlit Cloud, liest prognose_aktuell.json aus dem Repo

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

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
    df["date"]  = pd.to_datetime(df["date"])
    df          = df.sort_values("date")
    df["bin3h"] = df["date"].dt.floor("3h")
    df = df.groupby("bin3h").agg(preis=("diesel", "mean")).reset_index()
    df = df.rename(columns={"bin3h": "stunde"})
    return df

@st.cache_data(ttl=60)
def lade_live_log():
    try:
        df = pd.read_csv(LOG_URL, parse_dates=["timestamp"])
        df = df.rename(columns={"timestamp": "stunde"})
        df["stunde"] = df["stunde"].dt.floor("3h")
        df = df.groupby("stunde").agg(preis=("preis", "last")).reset_index()
        return df
    except:
        return pd.DataFrame(columns=["stunde", "preis"])

prognose = lade_prognose()
df_ext   = lade_preisverlauf()
df_live  = lade_live_log()

# Live-Log an Parquet anhängen — überschreibt ältere Bins mit aktuellen Werten
if not df_live.empty:
    df_ext = (
        pd.concat([df_ext, df_live])
        .drop_duplicates("stunde", keep="last")
        .sort_values("stunde")
        .reset_index(drop=True)
    )

# =========================================
# Prognose-Logik
# =========================================
letzter_ts    = df_ext["stunde"].max()
letzter_preis = float(df_ext["preis"].iloc[-1])

delta_erwartet = float(prognose["delta_erwartet"])
if prognose["richtung_24h"] == "fällt":
    delta_erwartet = -abs(delta_erwartet)
else:
    delta_erwartet = abs(delta_erwartet)

# Vorlagetage: letzte 4 Wochen, mind. 6 Bins (= 18h)
cutoff_4w  = letzter_ts - pd.Timedelta(weeks=4)
df_4w      = df_ext[(df_ext["stunde"] >= cutoff_4w) & (df_ext["stunde"] < letzter_ts)].copy()
df_4w["datum"] = df_4w["stunde"].dt.date

vollstaendige_tage = (
    df_4w.groupby("datum")
    .filter(lambda x: len(x) >= 6)["datum"]
    .unique()
)

# Nur Tage filtern deren natürlicher Drift zur Prognose-Richtung passt
passende_tage = []
for tag in vollstaendige_tage:
    df_tag = df_4w[df_4w["datum"] == tag].sort_values("stunde")
    drift = float(df_tag["preis"].iloc[-1]) - float(df_tag["preis"].iloc[0])
    if prognose["richtung_24h"] == "fällt" and drift < 0:
        passende_tage.append(tag)
    elif prognose["richtung_24h"] == "steigt" and drift > 0:
        passende_tage.append(tag)

# Fallback falls keine passenden Tage gefunden
if len(passende_tage) == 0:
    passende_tage = vollstaendige_tage

# Tagesbasierter Seed — stabil über den Tag, wechselt täglich
seed       = int(pd.Timestamp.now().strftime("%Y%m%d"))
rng        = np.random.default_rng(seed)
vorlagetag = rng.choice(passende_tage)

df_vorlage = df_4w[df_4w["datum"] == vorlagetag].sort_values("stunde").reset_index(drop=True)

# Vorlage auf n_bins auffüllen falls nötig
n_bins = 8
while len(df_vorlage) < n_bins + 1:
    df_vorlage = pd.concat([df_vorlage, df_vorlage]).reset_index(drop=True)

# Normalisiertes Intraday-Muster aus Vorlage extrahieren
vorlage_werte = [float(df_vorlage["preis"].iloc[i]) for i in range(n_bins)]
v_min   = min(vorlage_werte)
v_max   = max(vorlage_werte)
v_range = v_max - v_min if v_max != v_min else 0.001

vorlage_norm = [(v - v_min) / v_range for v in vorlage_werte]

# Bei "fällt": Muster umkehren damit Kurve garantiert fällt
if prognose["richtung_24h"] == "fällt":
    vorlage_norm = [1.0 - v for v in vorlage_norm]

# Amplitude aus historischer Volatilität, Endpunkt aus delta_erwartet
amplitude = float(prognose["volatilitaet_7d"])

prognose_ts     = [letzter_ts]
prognose_preise = [letzter_preis]

for i in range(1, n_bins):
    t = vorlage_norm[i]
    # Kurvenform skaliert auf Volatilität, Drift linear Richtung Ziel
    drift_anteil     = (i / (n_bins - 1)) * delta_erwartet
    form_anteil      = (t - vorlage_norm[i - 1] if i > 0 else 0)
    skalierter_preis = letzter_preis + drift_anteil + (t - 0.5) * amplitude
    prognose_preise.append(skalierter_preis)
    prognose_ts.append(letzter_ts + pd.Timedelta(hours=i * 3))

# =========================================
# Header
# =========================================
st.title("⛽ Diesel-Preisprognose")
st.caption(f"ARAL Dürener Str. 407, Köln · Stand: {prognose['timestamp']} Uhr")

st.divider()

# =========================================
# Empfehlung — Hauptkarte
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
    st.metric(
        label="Aktueller Preis",
        value=f"{prognose['preis_aktuell']:.3f} €",
        delta=f"{prognose['dip_oder_peak']} ({prognose['abweichung_t0_24h']:+.3f} €)",
        delta_color="inverse"
    )

with col2:
    richtung_emoji = "📈" if prognose["richtung_24h"] == "steigt" else "📉"
    st.metric(
        label="Prognose 24h",
        value=f"{richtung_emoji} {prognose['richtung_24h']}",
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

cutoff_7d = letzter_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

fig = go.Figure()

# Historischer Preisverlauf — Stufenlinie
fig.add_trace(go.Scatter(
    x=df_plot["stunde"],
    y=df_plot["preis"],
    mode="lines",
    name="Dieselpreis",
    line=dict(color="#1f77b4", width=2, shape="hv"),
))

# Prognose — gestrichelte Stufenlinie
fig.add_trace(go.Scatter(
    x=prognose_ts,
    y=prognose_preise,
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#ff7f0e", width=2, shape="hv"),
))

# Übergangspunkt
fig.add_trace(go.Scatter(
    x=[letzter_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(color="red", size=8, symbol="circle"),
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