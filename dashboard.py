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
    page_title="Dieselpreis · Köln",
    page_icon="⛽",
    layout="centered"
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
JSON_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/prognose_aktuell.json"
PARQUET_URL  = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/tankstellen_preise.parquet"
LOG_URL      = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/preis_live_log.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# CSS
# =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Roboto', sans-serif;
    background-color: #F0F2F5 !important;
    color: #212529;
    font-size: 18px;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.block-container {
    padding: 0 0 3rem 0 !important;
    max-width: 860px !important;
}

/* ── TOPBAR ── */
.topbar {
    background: #1565C0;
    padding: 0 2rem;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    margin-bottom: 2rem;
}
.topbar-left { display: flex; flex-direction: column; gap: 2px; }
.topbar-title {
    font-size: 1.8rem;
    font-weight: 500;
    color: #FFFFFF;
    letter-spacing: 0.01em;
    line-height: 1.2;
}
.topbar-sub {
    font-size: 0.95rem;
    color: rgba(255,255,255,0.85);
}
.topbar-time {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.95rem;
    color: #FFFFFF;
    background: rgba(0,0,0,0.18);
    padding: 6px 14px;
    border-radius: 4px;
    letter-spacing: 0.04em;
    white-space: nowrap;
}

/* ── METRIC CARDS ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    align-items: stretch;
    margin-bottom: 1.25rem;
}
.card {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.5rem 1.75rem;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}
.card-title {
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #616161;
    margin-bottom: 0.6rem;
}
.card-value {
    font-size: clamp(2.2rem, 3.2vw, 2.8rem);
    font-weight: 300;
    color: #1A1A1A;
    line-height: 1.1;
    letter-spacing: -0.01em;
    margin-bottom: auto;
}
.card-value sup {
    font-size: 0.42em;
    vertical-align: super;
    font-weight: 400;
    color: #757575;
}
.card-delta {
    font-size: 0.95rem;
    font-weight: 500;
    margin-top: 0.6rem;
}
.delta-green { color: #2E7D32; }
.delta-red   { color: #C62828; }
.delta-blue  { color: #1565C0; }

.tendenz-val {
    font-size: clamp(2.8rem, 5vw, 3.6rem);
    font-weight: 300;
    line-height: 1;
}
.tendenz-down { color: #2E7D32; }
.tendenz-up   { color: #C62828; }

/* ── EMPFEHLUNG ── */
.empfehlung-card {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.6rem 1.75rem 1.2rem 1.75rem;
    border-left: 5px solid #1565C0;
    margin-bottom: 1.5rem;
}
.empfehlung-card.heute  { border-left-color: #2E7D32; }
.empfehlung-card.morgen { border-left-color: #E65100; }
.empfehlung-card.warten { border-left-color: #C62828; }

.empfehlung-badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    margin-bottom: 0.8rem;
}
.badge-heute  { background: #E8F5E9; color: #1B5E20; }
.badge-morgen { background: #FFF3E0; color: #BF360C; }
.badge-warten { background: #FFEBEE; color: #B71C1C; }

.empfehlung-text {
    font-size: 1.1rem;
    color: #212121;
    line-height: 1.8;
}
.empfehlung-text strong {
    color: #1A1A1A;
    font-weight: 500;
}
.ki-footer {
    font-size: 0.8rem;
    color: #9E9E9E;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid #F5F5F5;
}
.ki-footer a { color: #757575; text-decoration: none; }
.ki-footer a:hover { text-decoration: underline; }

/* ── SECTION LABEL ── */
.section-label {
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #9E9E9E;
    margin: 1.75rem 0 0.75rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #E0E0E0;
}

/* ── FOOTER ── */
.page-footer {
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid #E0E0E0;
    font-size: 0.82rem;
    color: #9E9E9E;
    line-height: 2;
}
.page-footer a { color: #757575; text-decoration: none; }
.page-footer a:hover { text-decoration: underline; }

/* ── BARRIEREFREIHEIT ── */
:focus-visible {
    outline: 3px solid #1565C0;
    outline-offset: 3px;
    border-radius: 3px;
}

/* ── RESPONSIVE ── */
@media (max-width: 640px) {
    .metric-grid { grid-template-columns: 1fr; }
    .topbar { padding: 0 1rem; height: auto; min-height: 56px; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem 1rem; }
    .topbar-sub { display: none; }
    .card-value { font-size: 2rem; }
    .tendenz-val { font-size: 2.4rem; }
    .empfehlung-text { font-size: 1rem; }
}
</style>
""", unsafe_allow_html=True)

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
    df = df.rename(columns={"date": "stunde", "diesel": "preis"})
    return df[["stunde", "preis"]]

@st.cache_data(ttl=60)
def lade_live_log():
    try:
        df = pd.read_csv(LOG_URL, parse_dates=["timestamp"], on_bad_lines="skip")
        return df
    except:
        return pd.DataFrame(columns=["timestamp", "preis", "richtung_6h", "richtung_12h"])

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

@st.cache_data(ttl=3600)
def generiere_empfehlung(preis, mean_24h, richtung_6h, richtung_12h, dip_peak, empfehlung):
    prompt = f"""Du bist ein hilfreicher Tankstellen-Assistent für normale Autofahrer. Schreibe 2-3 Sätze auf Deutsch.

Fakten:
- Aktueller Dieselpreis: {preis:.3f} € ({preis - mean_24h:+.3f} € vs. 24h-Schnitt)
- Aktuelle Lage: {dip_peak} (Dip = günstiger als Nachbarn, Peak = teurer)
- Preistrend in 6 Stunden: {richtung_6h}
- Preistrend in 12 Stunden: {richtung_12h}
- Empfehlung: {empfehlung}

Regeln:
- Die Empfehlung "{empfehlung}" ist KORREKT — begründe sie überzeugend, stelle sie NICHT in Frage
- Erster Satz fett mit **: klare Handlungsempfehlung die mit "{empfehlung}" übereinstimmt
- Keine konkreten Eurobeträge für erwartete Preisänderungen nennen
- Kein Fachjargon, vorsichtig aber konsistent formulieren"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=10
    )
    return r.json()["content"][0]["text"]

# =========================================
# Daten zusammenführen
# =========================================
prognose    = lade_prognose()
df_ext      = lade_preisverlauf()
df_live_raw = lade_live_log()
preis_live  = lade_aktueller_preis()

if not df_live_raw.empty and "timestamp" in df_live_raw.columns:
    df_live = df_live_raw[["timestamp", "preis"]].copy()
    df_live = df_live.rename(columns={"timestamp": "stunde"})
    df_live["stunde"] = pd.to_datetime(df_live["stunde"])
    df_live = df_live.sort_values("stunde").drop_duplicates("stunde").reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=["stunde", "preis"])

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

jetzt_ts      = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live if preis_live else float(prognose["preis_aktuell"])
uhrzeit       = jetzt_ts.strftime("%H:%M")

# Prognose-Farbzonen aus prognose_stufen aufbauen
# Kein Betrag — nur Richtung als farbiger Hintergrund, Opazität nimmt ab
prognose_stufen = prognose.get("prognose_stufen", [])
prognose_zonen  = []  # Liste von (x0, x1, farbe, opazität)
if prognose_stufen:
    for i, s in enumerate(prognose_stufen):
        ts_start = jetzt_ts + pd.Timedelta(hours=i)
        ts_ende  = jetzt_ts + pd.Timedelta(hours=i + 1)
        # Opazität nimmt linear ab: von 0.18 auf 0.04
        opazitaet = 0.18 - (i / len(prognose_stufen)) * 0.14
        farbe = "rgba(46,125,50," if s["richtung"] == "fällt" else "rgba(198,40,40,"
        prognose_zonen.append({
            "x0": ts_start, "x1": ts_ende,
            "fillcolor": f"{farbe}{opazitaet:.3f})",
        })

cutoff_7d = jetzt_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

df_hist = pd.concat([
    df_plot[["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).sort_values("stunde").drop_duplicates("stunde", keep="last").reset_index(drop=True)

bin_grenzen = [jetzt_ts - pd.Timedelta(hours=24 * i) for i in range(8, -1, -1)]
df_24h_rows = []
for i in range(len(bin_grenzen) - 1):
    start = bin_grenzen[i]
    ende  = bin_grenzen[i + 1]
    mask  = (df_hist["stunde"] >= start) & (df_hist["stunde"] < ende)
    if mask.sum() > 0:
        df_24h_rows.append({"stunde": start, "preis": df_hist.loc[mask, "preis"].mean()})

df_24h = pd.DataFrame(df_24h_rows).sort_values("stunde").reset_index(drop=True)
if not df_24h.empty:
    df_24h = pd.concat([
        df_24h,
        pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
    ]).reset_index(drop=True)

mean_24h = float(df_hist[df_hist["stunde"] >= (jetzt_ts - pd.Timedelta(hours=24))]["preis"].mean())

# KI-Empfehlung
richtung_6h  = prognose.get("richtung_6h", "unbekannt")
richtung_12h = prognose.get("richtung_12h", "unbekannt")
dip_peak     = prognose.get("dip_oder_peak", "")

try:
    ki_text = generiere_empfehlung(
        letzter_preis, mean_24h,
        richtung_6h, richtung_12h,
        dip_peak, prognose["empfehlung"]
    )
except:
    ki_text = f"**{prognose['empfehlung'].capitalize()}.** {prognose['begruendung']}"

# =========================================
# Hilfsfunktionen
# =========================================
def preis_fmt(p):
    s = f"{p:.3f}"
    return f"{s[:-1]}<sup>{s[-1]}</sup>"

def bold(text):
    return text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

# =========================================
# TOPBAR
# =========================================
st.markdown(f"""
<div class="topbar" role="banner">
    <div class="topbar-left">
        <span class="topbar-title">Dieselpreisprognose</span>
        <span class="topbar-sub">ARAL &middot; Dürener Str. 407 &middot; Köln</span>
    </div>
    <span class="topbar-time" aria-label="Stand: {uhrzeit} Uhr">Live &middot; {uhrzeit} Uhr</span>
</div>
""", unsafe_allow_html=True)

# =========================================
# METRIKEN
# =========================================
delta_val   = letzter_preis - mean_24h
delta_class = "delta-green" if delta_val < 0 else "delta-red"
delta_arrow = "↓" if delta_val < 0 else "↑"
delta_label = "günstiger" if delta_val < 0 else "teurer"

# Tendenz aus richtung_6h
tendenz_pfeil = "↓" if richtung_6h == "fällt" else "↑"
tendenz_class = "tendenz-down" if richtung_6h == "fällt" else "tendenz-up"
tendenz_aria  = "Preis fällt in 6h" if richtung_6h == "fällt" else "Preis steigt in 6h"

st.markdown(f"""
<div class="metric-grid" role="region" aria-label="Preiskennzahlen">
    <div class="card">
        <div class="card-title">Ø letzte 24 Stunden</div>
        <div class="card-value" aria-label="{mean_24h:.3f} Euro">{preis_fmt(mean_24h)} &euro;</div>
    </div>
    <div class="card">
        <div class="card-title">Aktueller Preis &middot; {uhrzeit} Uhr</div>
        <div class="card-value" aria-label="{letzter_preis:.3f} Euro">{preis_fmt(letzter_preis)} &euro;</div>
        <div class="card-delta {delta_class}" aria-label="{abs(delta_val):.2f} Euro {delta_label} als 24h-Schnitt">
            {delta_arrow} {abs(delta_val):.2f} &euro; vs. &Oslash; 24h
        </div>
    </div>
    <div class="card">
        <div class="card-title">Tendenz nächste 6h</div>
        <div class="tendenz-val {tendenz_class}" aria-label="{tendenz_aria}">{tendenz_pfeil}</div>
        <div class="card-delta delta-blue">12h: {richtung_12h}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# EMPFEHLUNG
# =========================================
if "heute" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", "Jetzt tanken"
elif "morgen" in prognose["empfehlung"] or "später" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "morgen", "badge-morgen", "Später tanken"
else:
    card_cls, badge_cls, badge_txt = "warten", "badge-warten", "Abwarten"

st.markdown(f"""
<div class="empfehlung-card {card_cls}" role="region" aria-label="Empfehlung: {badge_txt}">
    <div class="empfehlung-badge {badge_cls}">{badge_txt}</div>
    <div class="empfehlung-text">{bold(ki_text)}</div>
    <div class="ki-footer">
        KI-generierter Text &middot;
        <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude API &middot; Anthropic</a>
        &middot; Modell: Random Forest MultiOutput &middot; Acc: {prognose['modell_accuracy']:.1f}% &middot; Keine Garantie
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# CHART
# =========================================
st.markdown('<div class="section-label" role="heading" aria-level="2">Preisverlauf — 7 Tage + Prognose 24h</div>', unsafe_allow_html=True)

fig = go.Figure()

# Historischer Preisverlauf
fig.add_trace(go.Scatter(
    x=df_hist["stunde"],
    y=df_hist["preis"],
    mode="lines",
    name="Preisverlauf",
    line=dict(color="#BDBDBD", width=1.5, shape="hv"),
))

# 24h-Mittel-Bins
fig.add_trace(go.Scatter(
    x=df_24h["stunde"],
    y=df_24h["preis"],
    mode="lines",
    name="24h-Mittel",
    line=dict(color="#1565C0", width=2.5, shape="hv"),
))

# Prognose-Farbzonen — grün = fällt, rot = steigt, Opazität nimmt ab
for zone in prognose_zonen:
    fig.add_vrect(
        x0=zone["x0"], x1=zone["x1"],
        fillcolor=zone["fillcolor"],
        layer="below",
        line_width=0,
    )

# Aktueller Preis Marker
fig.add_trace(go.Scatter(
    x=[jetzt_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(
        color="#FFFFFF",
        size=10,
        symbol="circle",
        line=dict(color="#1565C0", width=2.5)
    ),
))

# Trennlinie jetzt
fig.add_vline(
    x=jetzt_ts,
    line_width=1,
    line_dash="dash",
    line_color="#BDBDBD",
)

mitternacht_linien = []
tag = cutoff_7d.normalize()
while tag <= jetzt_ts + pd.Timedelta(days=1):
    mitternacht_linien.append(dict(
        type="line",
        x0=tag, x1=tag, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#EEEEEE", width=1),
    ))
    tag += pd.Timedelta(days=1)

fig.update_layout(
    shapes=mitternacht_linien,
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font=dict(family="Roboto", size=13, color="#757575"),
    xaxis=dict(
        dtick=24 * 3600 * 1000,
        tick0="2020-01-01 12:00:00",
        tickformat="%d.%m.",
        tickangle=0,
        tickfont=dict(size=13, color="#9E9E9E"),
        gridcolor="#F5F5F5",
        showline=True,
        linecolor="#E0E0E0",
        zeroline=False,
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="#9E9E9E"),
        gridcolor="#F5F5F5",
        showline=False,
        zeroline=False,
        ticksuffix=" €",
        title=None,
    ),
    legend=dict(
        orientation="h",
        y=-0.15,
        font=dict(size=13, color="#757575"),
        bgcolor="rgba(0,0,0,0)",
    ),
    margin=dict(l=10, r=20, t=15, b=10),
    height=360,
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        bordercolor="#E0E0E0",
        font=dict(color="#212529", size=13, family="Roboto"),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# =========================================
# FOOTER
# =========================================
st.markdown(f"""
<div class="page-footer" role="contentinfo">
    Preisinformationen von
    <a href="https://tankerkoenig.de" target="_blank" rel="noopener">Tankerkönig</a>
    unter <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>
    &middot; Datenquelle: MTS-K (Markttransparenzstelle für Kraftstoffe)
    &middot; Prognose stündlich via GitHub Actions
    &middot; DSI Capstone 2026
</div>
""", unsafe_allow_html=True)