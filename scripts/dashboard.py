# dashboard.py — Dieselpreisprognose (Streamlit)
# Streamlit Cloud · DSI Capstone Projekt 2026

import json
import time
from io import BytesIO

import streamlit as st
import pandas as pd

import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(
    page_title="Dieselpreisprognose",
    page_icon="assets/favicon.svg",
    layout="centered",
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
ARAL_STATION_URL = "https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400"
BASE_URL     = "https://raw.githubusercontent.com/felixschrader/dieselpreisprognose/main"
JSON_URL     = f"{BASE_URL}/data/ml/prognose_aktuell.json"
TAGES_URL    = f"{BASE_URL}/data/ml/prognose_tagesbasis.json"
PARQUET_URL  = f"{BASE_URL}/data/tankstellen_preise.parquet"
LOG_URL      = f"{BASE_URL}/data/ml/preis_live_log.csv"
PROG_LOG_URL = f"{BASE_URL}/data/ml/prognose_log.csv"
BRENT_1H_URL = f"{BASE_URL}/data/brent_futures_intraday_1h.csv"
BRENT_DAILY_URL = f"{BASE_URL}/data/brent_futures_daily.csv"
EURUSD_URL   = f"{BASE_URL}/data/eur_usd_rate.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# Öffnungszeiten laut tankstelle.aral.de (Stand: Oliver Rosenbach, Dürener Str. 407)
OEFFNUNG_VON = 6   # 06:00 Uhr
OEFFNUNG_BIS = 22  # konservativ für 3h-Bins / Charts (Schluss je nach Wochentag s. ist_offen)

SOCIAL_TEAM = {
    "felix": {"name": "Felix Schrader", "linkedin": "https://www.linkedin.com/in/felixschrader/"},
    "girandoux": {
        "name": "Girandoux Fandio Nganwajop",
        "linkedin": "https://www.linkedin.com/in/girandoux-fandio-08628bb9/",
    },
    "ghislain": {
        "name": "Ghislain Djifag Wamo",
        "linkedin": "https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Djifag%20Wamo",
    },
}

tx = {
    "badge_fill_now": "Jetzt",
    "badge_wait": "Später",
    "badge_flexible": "Flexibel",
    "badge_hold": "Beobachten",
    "opening": [
        ("Mo–Fr", "06:00–21:30"),
        ("Sa–So", "07:00–21:00"),
    ],
    "topbar_title": "Dieselpreisprognose",
    "topbar_aral_link": "Website",
    "topbar_hours_heading": "Öffnungszeiten",
    "topbar_live": "Live",
    "topbar_refresh": "Aktualisieren",
    "section_glance": "Auf einen Blick",
    "card_avg_yesterday": "Ø gestern",
    "card_current": "Jetzt",
    "vs_avg_yesterday": "ct vs. Ø gestern",
    "card_model_dir": "Modell (Tagesrichtung)",
    "tab_price": "Preisverlauf",
    "tab_kpi": "KPI",
    "tab_perf": "Prognose-Performance",
    "pv_section": "Preisverlauf (3h-Stufen, letzter Preis je Bin)",
    "pv_brent_toggle": "Brent-Linie einblenden",
    "pv_brent_cap": "Quelle:",
    "pv_brent_last": "Stand:",
    "pv_brent_none": "Keine Intraday-Daten",
    "legend_diesel": "Diesel",
    "legend_brent": "Brent (USD)",
    "legend_day_avg": "Tagesmittel",
    "yaxis_diesel": "Diesel €/l",
    "yaxis_brent": "Brent USD",
    "kpi_section": "Kennzahlen (14 Kalendertage bis gestern)",
    "kpi_chg_lbl": "Ø Preiswechsel/Tag",
    "kpi_vol_lbl": "Ø Tagesvolatilität",
    "kpi_cap_range": "Zeitraum: {a} – {b}",
    "kpi_cap_chg_def": "Preiswechsel = nur echte Sprünge im Preis (nicht jede Messung); nur während Öffnungszeiten.",
    "kpi_cap_kpi_src": "KPI-Zeitreihe: Parquet + Live-Log mit Original-Zeitstempeln (ohne 3h-Bins wie im Preisverlauf).",
    "kpi_sec_chg": "Preiswechsel pro Tag",
    "kpi_legend_chg": "Anzahl Sprünge",
    "kpi_hover_chg": "%{x|%d.%m.}<br>%{y} Wechsel<extra></extra>",
    "kpi_sec_vol": "Volatilität (ganzer Tag)",
    "kpi_legend_vol": "Std. je Tag (ct)",
    "kpi_hover_vol": "%{x|%d.%m.}<br>%{y:.1f} ct<extra></extra>",
    "perf_section": "Modell-Performance (Log)",
    "perf_cap": (
        "Richtungstreffer aus `prognose_log.csv` (Vorzeichen Δ). "
        "Notebook-Test: ~{acc:.0f} % vs. Baseline ~{base:.0f} %."
    ),
    "perf_no_log": "Kein Prognose-Log geladen.",
    "perf_acc_3w": "Trefferquote 3 Wo.",
    "perf_ok_3w": "Korrekt / Tage",
    "perf_acc_nb": "Richtung (Test, NB)",
    "perf_baseline": "Baseline Richtung",
    "perf_cal_title": "Kalender (Richtung)",
    "perf_cal_cap": (
        "Kacheln: P / A = vorhergesagte bzw. tatsächliche Tages-Δ in Cent (im Log als €/l, Anzeige ×100). "
        "Nur Tage mit Richtungsauswertung. Kalender endet am letzten ausgewerteten Tag (gestern)."
    ),
    "cal_weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "perf_weekly_title": "Trefferquote nach Woche",
    "perf_bar_hover": "Trefferquote",
    "perf_bar_days": "Tage",
    "perf_pred_actual_title": "Vorhersage vs. Ist (Δ, ct)",
    "perf_trace_pred": "Vorhergesagt",
    "perf_hover_pred": "%{x|%d.%m.}<br>Vorhersage: %{y:.1f} ct<extra></extra>",
    "perf_trace_act": "Ist",
    "perf_hover_act": "%{x|%d.%m.}<br>Ist: %{y:.1f} ct<extra></extra>",
    "perf_band_cap": (
        "Δ in Cent: Spalten `predicted_delta` / `actual_delta` im Log sind €/l → Anzeige ×100. "
        "Grauer Streifen: ±0,5 ct um 0."
    ),
    "social_github": "GitHub",
    "footer_price": "Preisdaten:",
    "footer_mtsk": "MTS-K",
    "footer_dsi": "Capstone DSI",
}

_SVG_GH = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#24292f" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/></svg>"""
_SVG_IN = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.125 2.062 2.062 0 0 1 0 4.125zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>"""

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700&family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

:root {
  --surface: #FFFFFF;
  --bg-page: #EEF1F6;
  --border-subtle: #E4E8EF;
  --text-primary: #1A1D24;
  --text-secondary: #5C6370;
  --brand: #1565C0;
  --brand-dark: #0D47A1;
  --radius-sm: 8px;
  --radius-md: 12px;
  --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 12px rgba(16, 24, 40, 0.06);
  --shadow-card-hover: 0 4px 8px rgba(16, 24, 40, 0.06), 0 12px 24px rgba(16, 24, 40, 0.08);
}

*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }

html, body, [class*="css"], .stApp {
    font-family: 'Roboto', system-ui, sans-serif;
    background: var(--bg-page) !important;
    background-image: linear-gradient(180deg, #E8ECF3 0%, var(--bg-page) 48%, #E9EDF4 100%) !important;
    background-attachment: fixed !important;
    color: var(--text-primary);
    font-size: 18px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Hauptinhalt: etwas größer & luftiger lesbar */
[data-testid="stMain"] {
    font-size: 1.05rem !important;
    line-height: 1.65 !important;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li {
    font-size: 1.05rem !important;
    line-height: 1.68 !important;
}
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] label {
    font-size: 1rem !important;
}
[data-testid="stAlert"] {
    font-size: 1.02rem !important;
    line-height: 1.6 !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p,
[data-testid="stExpander"] li {
    font-size: 1.02rem !important;
    line-height: 1.65 !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.block-container {
    padding: 0 1.25rem 3.5rem 1.25rem !important;
    max-width: 960px !important;
}

/* Streamlit: Captions & Hilfetext */
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] {
    color: var(--text-secondary) !important;
    font-size: 1rem !important;
    line-height: 1.58 !important;
}

/* TOPBAR */
.topbar {
    font-family: 'Plus Jakarta Sans', 'Roboto', sans-serif;
    background: linear-gradient(135deg, #1565C0 0%, #0D47A1 55%, #0A3A85 100%);
    padding: 1.35rem 1.75rem 1.35rem 1.75rem;
    box-shadow: 0 4px 20px rgba(13, 71, 161, 0.35), 0 1px 0 rgba(255,255,255,0.12) inset;
    margin-bottom: 1.35rem;
    border-radius: var(--radius-md);
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 1rem;
}
.topbar-left { flex: 1; min-width: 0; }
.topbar-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: clamp(1.85rem, 4.2vw, 2.45rem);
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    line-height: 1.12;
}
.topbar-addr {
    font-size: 1.08rem;
    color: rgba(255,255,255,0.9);
    margin-top: 8px;
    line-height: 1.5;
}
.topbar-addr a {
    color: #FFFFFF;
    text-decoration: underline;
    text-decoration-color: rgba(255,255,255,0.45);
    text-underline-offset: 3px;
    transition: text-decoration-color 0.15s ease;
}
.topbar-addr a:hover {
    text-decoration-color: rgba(255,255,255,0.95);
}
.topbar-addr a:focus-visible {
    outline: 2px solid rgba(255,255,255,0.85);
    outline-offset: 3px;
    border-radius: 2px;
}
.topbar-hours-heading {
    margin-top: 12px;
    font-size: 0.88rem;
    font-weight: 600;
    color: rgba(255,255,255,0.92);
    letter-spacing: 0.04em;
}
.topbar-hours {
    margin-top: 6px;
    display: flex; flex-direction: column; gap: 4px;
}
.topbar-hours-row {
    font-size: 1rem; color: rgba(255,255,255,0.82);
    display: flex; gap: 0.65rem; align-items: baseline;
}
.topbar-hours-row b {
    color: rgba(255,255,255,0.95);
    font-weight: 600;
    min-width: 62px;
    font-size: 0.92rem;
    letter-spacing: 0.02em;
}
.topbar-right {
    display: flex; flex-direction: column;
    align-items: flex-end; gap: 0.55rem; flex-shrink: 0;
}
.topbar-time {
    font-family: 'Roboto Mono', ui-monospace, monospace;
    font-size: 1.02rem; color: #FFFFFF;
    background: rgba(0,0,0,0.22);
    padding: 8px 14px;
    border-radius: 999px;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.12);
    letter-spacing: 0.02em;
}
.topbar-refresh {
    display: inline-block;
    margin-top: 0;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(255,255,255,0.16);
    color: #FFFFFF !important;
    text-decoration: none !important;
    font-size: 0.96rem;
    font-weight: 600;
    border: 1px solid rgba(255,255,255,0.22);
    transition: background 0.15s ease, transform 0.12s ease;
}
.topbar-refresh:hover {
    background: rgba(255,255,255,0.28);
    transform: translateY(-1px);
}
.topbar-refresh:focus-visible {
    outline: 2px solid #FFFFFF;
    outline-offset: 3px;
}
form.topbar-refresh-form {
    display: inline-block;
    margin: 0;
    padding: 0;
}
button.topbar-refresh {
    font-family: inherit;
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
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

/* METRIC CARDS — drei Zeilen: Kopf · Inhalt · Fuß; gleiche vertikale Raster */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem 1.1rem;
    margin-bottom: 1.35rem;
    align-items: stretch;
}
.card {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    padding: 1.15rem 1.2rem 1.05rem 1.2rem;
    transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
    display: grid;
    grid-template-rows: auto minmax(4.5rem, 1fr) auto;
    align-items: stretch;
    text-align: center;
}
.card:hover {
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-2px);
    border-color: #D8DEE9;
}
.card-head {
    align-self: start;
}
.card-main {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 4.25rem;
}
.card-foot {
    align-self: end;
    font-size: 0.84rem;
    font-weight: 500;
    line-height: 1.4;
    color: #6B7280;
    margin-top: 0.5rem;
    padding-top: 0.55rem;
    border-top: 1px solid #EEF1F4;
    min-height: 2.6em;
}
.card-title {
    font-size: 0.8rem; font-weight: 600;
    letter-spacing: 0.09em; text-transform: uppercase;
    color: var(--text-secondary); margin-bottom: 0;
}
.card-value {
    font-size: clamp(2.15rem, 3.2vw, 2.85rem);
    font-weight: 300; color: var(--text-primary);
    line-height: 1.08; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}
.card-value sup { font-size: 0.42em; vertical-align: super; font-weight: 400; color: #8E959F; }
.card-delta { font-size: 1rem; font-weight: 500; letter-spacing: 0.01em; }
.delta-green  { color: #2E7D32; }
.delta-red    { color: #C62828; }
.delta-blue   { color: #1565C0; }
.tendenz-val  { font-size: clamp(2.35rem, 3.6vw, 3.15rem); font-weight: 300; line-height: 1; }
.tendenz-down { color: #2E7D32; }
.tendenz-up   { color: #C62828; }
.tendenz-flat { color: #757575; }
.card--model-direction {
    background: linear-gradient(165deg, #FAFCFE 0%, #F0F4FA 55%, #E8EEF6 100%);
    border: 1px solid #C5D4E8;
    box-shadow: 0 2px 8px rgba(13, 71, 161, 0.08), 0 8px 24px rgba(16, 24, 40, 0.06);
}
.card--model-direction:hover {
    border-color: #90CAF9;
    box-shadow: 0 4px 14px rgba(13, 71, 161, 0.12), 0 12px 32px rgba(16, 24, 40, 0.08);
}
.tendenz-val-model {
    font-family: 'Plus Jakarta Sans', 'Roboto', sans-serif;
    font-size: clamp(3.15rem, 6.5vw, 4.25rem);
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.06em;
    display: block;
    margin: 0 auto;
    -webkit-text-stroke: 0.025em currentColor;
    paint-order: stroke fill;
}
.card--model-direction .tendenz-down { color: #1B5E20; }
.card--model-direction .tendenz-up   { color: #B71C1C; }
.card--model-direction .tendenz-flat { color: #424242; }

/* KI-Block: äußerer Wrapper dämpft Streamlit-Abstand zur nächsten Sektion */
.ki-wrap {
    margin-bottom: 0 !important;
    padding-bottom: 0;
}

/* EMPFEHLUNG */
.empfehlung-card {
    background: var(--surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    box-shadow: var(--shadow-card);
    padding: 1.35rem 1.45rem 1.1rem 1.45rem;
    border-left: 5px solid #1565C0;
    margin-bottom: 1.5rem;
    transition: box-shadow 0.2s ease;
}
.empfehlung-card:hover { box-shadow: var(--shadow-card-hover); }
.empfehlung-card.heute  { border-left-color: #2E7D32; }
.empfehlung-card.morgen { border-left-color: #E65100; }
.empfehlung-card.warten { border-left-color: #C62828; }
.empfehlung-badge {
    display: inline-block; font-size: 0.8rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 4px; margin-bottom: 0.8rem;
}
.badge-heute  { background: #E8F5E9; color: #1B5E20; }
.badge-morgen { background: #FFF3E0; color: #BF360C; }
.badge-warten { background: #FFEBEE; color: #B71C1C; }
.empfehlung-text { font-size: 1.125rem; color: var(--text-primary); line-height: 1.75; }
.empfehlung-text strong { color: var(--text-primary); font-weight: 600; }
.ki-footer {
    font-size: 0.9rem; color: #8E959F;
    margin-top: 0.95rem; padding-top: 0.75rem;
    border-top: 1px solid #EEF1F4;
}
.ki-footer a { color: var(--text-secondary); text-decoration: none; }
.ki-footer a:hover { text-decoration: underline; }

/* Social: Zeile 1 = Links · Zeile 2 = Aufklapp (kein Flex-Wrap-Konflikt) */
.social-info-wrap {
    margin: 0 0 0.35rem 0; padding: 0.85rem 1.15rem;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
}
.social-row-links {
    width: 100%;
}
.social-row-meta {
    width: 100%;
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #EEF1F4;
}
.social-strip {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 0.5rem 0.85rem; margin: 0; padding: 0;
    font-size: 0.96rem;
}
.social-strip a {
    display: inline-flex; align-items: center; gap: 0.35rem;
    color: var(--text-primary); text-decoration: none;
    border-radius: 6px;
    padding: 2px 4px;
    margin: -2px -4px;
    transition: color 0.15s ease, background 0.15s ease;
}
.social-strip a:hover { color: var(--brand); background: rgba(21, 101, 192, 0.06); }
.social-strip a:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
.social-strip .social-ico { display: inline-flex; line-height: 0; flex-shrink: 0; }
.social-strip-sep { color: #BDBDBD; user-select: none; }
.header-details {
    width: 100%;
    margin: 0;
    font-size: 0.98rem; color: #424242; line-height: 1.65;
}
.header-details[open] { width: 100%; }
.header-details summary {
    cursor: pointer; list-style: none;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.96rem; font-weight: 600;
    color: var(--brand-dark);
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: 1px solid #B8D4F0;
    background: linear-gradient(180deg, #F5FAFF 0%, #E3F0FC 100%);
    box-shadow: 0 1px 2px rgba(13, 71, 161, 0.08);
    text-align: left;
    width: 100%;
    box-sizing: border-box;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    transition: background 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.header-details summary::after {
    content: "▾";
    flex-shrink: 0;
    font-size: 0.8rem;
    opacity: 0.55;
    font-weight: 700;
}
.header-details[open] summary::after { content: "▴"; }
.header-details summary:hover {
    background: #E3F2FD;
    border-color: #64B5F6;
    color: #0D47A1;
    box-shadow: 0 2px 8px rgba(13, 71, 161, 0.12);
}
.header-details summary:focus-visible {
    outline: 2px solid var(--brand);
    outline-offset: 3px;
}
.header-details summary::-webkit-details-marker { display: none; }
.header-details-body {
    margin-top: 0.65rem; padding: 0.9rem 1.1rem;
    background: #F8FAFC;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 1.02rem;
    line-height: 1.68;
}
.header-details-body p { margin: 0 0 0.65rem 0; }
.header-details-body p:last-child { margin-bottom: 0; }

/* OSM-Karte */
.osm-map-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.02rem; font-weight: 600;
    color: var(--text-secondary);
    margin: 0.35rem 0 0.55rem 0;
    letter-spacing: 0.01em;
}
.osm-map-title a {
    color: var(--brand);
    text-decoration: none;
    font-weight: 600;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s ease, color 0.15s ease;
}
.osm-map-title a:hover { border-bottom-color: rgba(21, 101, 192, 0.45); }
.osm-map-title a:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; border-radius: 2px; }

/* SECTION LABEL */
.section-label {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.92rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--text-secondary);
    margin: 1.1rem 0 0.75rem 0;
    padding: 0 0 0.65rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
    border-left: 3px solid var(--brand);
}
/* Erste Sektion unter der Topbar: weniger Abstand nach oben */
.section-label.section-label-first {
    margin-top: 0.35rem;
}
/* Direkt nach KI-Karte: kein doppelter Luftpolster wie bei normaler section-label */
.section-label.section-label-tight-top {
    margin-top: 0.35rem;
}
/* Erster Unterabschnitt im Modell-Tab (Kalender direkt unter Retrograde-Intro) */
.section-label.section-label-priority {
    margin-top: 0.35rem;
    margin-bottom: 0.55rem;
    font-size: 0.98rem;
    font-weight: 800;
    color: var(--text-primary);
    border-left-width: 4px;
}
.card-foot--empty {
    border-top: none !important;
    min-height: 0 !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
}
/* Abstand unter der OSM-Karte (Klasse am Leaflet-Wrapper) */
.content-block-map {
    margin-bottom: 1.35rem;
}

/* KPI CARDS */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 0.85rem; margin-bottom: 1.35rem;
}
.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 1rem 0.85rem;
    text-align: center;
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.kpi-card:hover {
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
}
.kpi-val {
    font-family: 'Roboto Mono', ui-monospace, monospace;
    font-size: 1.62rem; font-weight: 500; color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}
.kpi-lbl {
    font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: #8E959F; margin-top: 6px; line-height: 1.3;
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
    font-size: 0.76rem; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: #9E9E9E; padding: 4px 0;
}
.tag-kachel {
    border-radius: 6px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 3px; padding: 9px 5px;
    font-size: 0.86rem; font-weight: 500;
}
.tag-kachel.korrekt { background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; }
.tag-kachel.falsch  { background: #FFEBEE; color: #B71C1C; border: 1px solid #EF9A9A; }
.tag-kachel.leer    { background: transparent; border: 1px solid #F0F0F0; }
.tag-symbol { font-size: 1.1rem; }
.tag-datum  { font-size: 0.82rem; font-weight: 600; }
.tag-delta  { font-size: 0.8rem; }

/* TABS — segmentiert, ruhig */
.stTabs [data-baseweb="tab-list"] {
    background-color: #E4E9F2 !important;
    border-radius: 12px !important;
    padding: 5px !important;
    gap: 4px !important;
    border: none !important;
    box-shadow: inset 0 1px 2px rgba(16, 24, 40, 0.06);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.02rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.1rem !important;
    border-radius: 9px !important;
    color: var(--text-secondary) !important;
    border: none !important;
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--brand-dark) !important;
    background: rgba(255,255,255,0.55) !important;
}
.stTabs [aria-selected="true"] {
    background-color: #FFFFFF !important;
    color: var(--brand) !important;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.08), 0 2px 8px rgba(16, 24, 40, 0.06) !important;
}

/* Plotly in Tabs: etwas Luft */
.js-plotly-plot { border-radius: var(--radius-sm); }

/* FOOTER */
.footer-wrap {
    margin-top: 0.85rem; padding-top: 1rem;
    border-top: 1px solid var(--border-subtle);
}
.footer-mini {
    font-size: 0.95rem; color: var(--text-secondary); line-height: 1.75;
}
.footer-mini a {
    color: #3D4450;
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s ease, color 0.15s ease;
}
.footer-mini a:hover { border-bottom-color: rgba(21, 101, 192, 0.35); color: var(--brand-dark); }
.footer-mini a:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; border-radius: 2px; }

@media (max-width: 640px) {
    .metric-grid {
        grid-template-columns: 1fr;
        gap: 0.9rem;
    }
    .kpi-grid    { grid-template-columns: repeat(2, 1fr); }
    .topbar      { flex-direction: column; padding: 1.1rem 1.15rem; border-radius: 10px; }
    .topbar-right { align-items: flex-start; }
    .topbar-title { font-size: 1.7rem; }
    .kalender-woche { grid-template-columns: repeat(4, 1fr); }
    .social-row-meta { margin-top: 0.65rem; padding-top: 0.65rem; }
    .block-container { padding-left: 0.85rem !important; padding-right: 0.85rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.92rem !important; padding: 0.5rem 0.75rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Daten laden ───────────────────────────────────────────────────────────────
# Kurze TTL + no-cache: nach GitHub-Push schnell sichtbar (ohne auf den 5-Min-Block warten).
_HTTP_NO_CACHE = {
    "Cache-Control": "no-cache, max-age=0",
    "Pragma": "no-cache",
}
_DASH_UA = {"User-Agent": "dieselpreisprognose-dashboard/1.0"}
_TK_HEADERS = {
    "User-Agent": "dieselpreisprognose-dashboard/1.0",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def _github_raw_bytes(url: str, timeout: int = 30) -> bytes:
    """raw.githubusercontent.com (Fastly) cacht aggressiv — cb= erzwingt oft einen CDN-Miss."""
    sep = "&" if "?" in url else "?"
    busted = f"{url}{sep}cb={int(time.time())}"
    r = requests.get(
        busted,
        timeout=timeout,
        headers={**_HTTP_NO_CACHE, **_DASH_UA},
    )
    r.raise_for_status()
    return r.content


def _tk_parse_diesel(v) -> float | None:
    """Tankerkönig liefert ggf. false wenn geschlossen — dann kein Float."""
    if v is None or v is False:
        return None
    try:
        x = float(v)
        if 0.3 <= x <= 5.0:
            return x
    except (TypeError, ValueError):
        pass
    return None


def _tk_diesel_prices_node(node: dict) -> float | None:
    """prices.php-Eintrag: bei status=closed keinen (veralteten) Diesel anzeigen."""
    if not isinstance(node, dict) or node.get("status") == "closed":
        return None
    return _tk_parse_diesel(node.get("diesel"))


def _tk_diesel_detail_station(st: dict | None) -> float | None:
    if not isinstance(st, dict):
        return None
    if st.get("isOpen") is False and st.get("diesel") in (None, False):
        return None
    return _tk_parse_diesel(st.get("diesel"))


def letzter_preis_aus_zeitreihe(
    df_ext: pd.DataFrame, jetzt: pd.Timestamp, max_hours: float = 120.0
) -> float | None:
    """Letzte Diesel-Beobachtung aus Parquet-Zeitreihe (Station), wenn nicht zu alt."""
    if df_ext is None or df_ext.empty:
        return None
    df = df_ext[["stunde", "preis"]].copy()
    df["stunde"] = pd.to_datetime(df["stunde"], errors="coerce")
    df["preis"] = pd.to_numeric(df["preis"], errors="coerce")
    df = df.dropna(subset=["stunde", "preis"])
    if df.empty:
        return None
    cut = jetzt - pd.Timedelta(hours=max_hours)
    sub = df[df["stunde"] >= cut]
    if sub.empty:
        sub = df
    row = sub.sort_values("stunde").iloc[-1]
    return float(row["preis"])


def letzter_preis_aus_live_log(
    df_raw: pd.DataFrame, jetzt: pd.Timestamp, max_hours: float = 96.0
) -> float | None:
    if df_raw.empty or not {"timestamp", "preis"}.issubset(df_raw.columns):
        return None
    df = df_raw[["timestamp", "preis"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["preis"] = pd.to_numeric(df["preis"], errors="coerce")
    df = df.dropna(subset=["timestamp", "preis"]).sort_values("timestamp")
    if df.empty:
        return None
    row = df.iloc[-1]
    age_h = (jetzt - pd.Timestamp(row["timestamp"])).total_seconds() / 3600.0
    if age_h > max_hours:
        return None
    return float(row["preis"])


@st.cache_data(ttl=30)
def lade_prognose():
    raw = _github_raw_bytes(JSON_URL, timeout=20)
    return json.loads(raw.decode("utf-8"))

@st.cache_data(ttl=30)
def lade_tagesprognose():
    try:
        raw = _github_raw_bytes(TAGES_URL, timeout=20)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}

@st.cache_data(ttl=120)
def lade_preisverlauf():
    # Parquet bewusst per pandas-URL (große Datei); Fallback-Preis kommt primär aus API + Live-Log-CSV.
    df = pd.read_parquet(PARQUET_URL)
    df = df[df["station_uuid"] == STATION_UUID].copy()
    df = df[df["diesel"].notna()]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").rename(columns={"date": "stunde", "diesel": "preis"})
    return df[["stunde", "preis"]]

@st.cache_data(ttl=20)
def lade_live_log():
    try:
        raw = _github_raw_bytes(LOG_URL, timeout=20)
        return pd.read_csv(
            BytesIO(raw),
            parse_dates=["timestamp"],
            on_bad_lines="skip",
        )
    except Exception:
        return pd.DataFrame(columns=["timestamp", "preis"])

@st.cache_data(ttl=15)
def lade_aktueller_preis():
    """Live-Diesel: zuerst detail.php (eine Station), dann prices.php."""
    try:
        key = st.secrets["TANKERKOENIG_KEY"]
    except Exception:
        return None
    for path, parser in (
        (
            f"https://creativecommons.tankerkoenig.de/json/detail.php?id={STATION_UUID}&apikey={key}",
            lambda js: _tk_diesel_detail_station(js.get("station")),
        ),
        (
            f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={key}",
            lambda js: _tk_diesel_prices_node((js.get("prices") or {}).get(STATION_UUID, {})),
        ),
    ):
        try:
            r = requests.get(path, timeout=12, headers=_TK_HEADERS)
            r.raise_for_status()
            d = parser(r.json())
            if d is not None:
                return d
        except Exception:
            continue
    return None

@st.cache_data(ttl=90)
def lade_prognose_log():
    try:
        raw = _github_raw_bytes(PROG_LOG_URL, timeout=20)
        df = pd.read_csv(BytesIO(raw), parse_dates=["datum"])
        # Tagesdatum immer auf 00:00 Uhr normieren (keine Sub-Tages-Zeiten aus der CSV)
        df["datum"] = pd.to_datetime(df["datum"], errors="coerce").dt.floor("D")
        for c in ("predicted_delta", "actual_delta", "richtung_korrekt"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.sort_values("datum").reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["datum", "predicted_delta", "actual_delta", "richtung_korrekt"])


def _datum_berlin_tag(ser: pd.Series) -> pd.Series:
    """Kalendertag Europe/Berlin — Auswertungstag beginnt um 00:00 Uhr Ortszeit (kein UTC-Mitternachts-Off-by-one)."""
    ts = pd.to_datetime(ser, errors="coerce")
    if ts.dt.tz is None:
        ts = ts.dt.floor("D").dt.tz_localize(BERLIN, ambiguous="infer", nonexistent="shift_forward")
    else:
        ts = ts.dt.tz_convert(BERLIN).dt.floor("D")
    return ts.dt.normalize().dt.date

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

def _richtung_laien(richtung_tage: str) -> str:
    r = (richtung_tage or "").strip().lower()
    if r in ("steigt", "steigend"):
        return "steigend"
    if r in ("fällt", "fallend"):
        return "fallend"
    if r in ("stabil", "seitwärts", "flat"):
        return "eher seitwärts"
    return "unklar"


@st.cache_data(ttl=3600)
def generiere_empfehlung(
    preis, mean_ref, richtung_tage, brent_vs_3d_pct, _prompt_version: int = 4
):
    r_plain = _richtung_laien(richtung_tage)
    prompt = f"""Du bist ein Datenanalyst. Schreibe genau 2 vollständige Sätze auf Deutsch — sachlich und etwas präziser als Alltagssmalltalk, aber für Laien verständlich (kein Fach-Kauderwelsch).

Interne Daten (Inhalt nutzen, nicht Satz für Satz abschreiben):
- Dieselpreis an dieser Tankstelle jetzt: {preis:.2f} Euro; Abstand zum Tagesmittel von gestern (gleiche Station): {(preis - mean_ref)*100:+.1f} Cent
- Prognosemodell (intern): grobe Richtung {r_plain}
- Brent: {brent_vs_3d_pct:+.1f} Prozent gegenüber dem Drei-Tage-Mittel der letzten Werktage (Referenzgröße)

Regeln für den sichtbaren Text:
- Keine Handlungsempfehlung, kein „tanken“, kein „warten“
- Kein Regionalvergleich, keine anderen Tankstellen
- Vermeide: Kernpreis, Delta, Horizont, Pipeline, Spot (als Fachwort)
- Satz 1: aktueller Literpreis und Abstand zum Mittel von gestern (mit Zahlen)
- Satz 2: **Brent** beim Namen nennen (nicht „Rohöl“ schreiben). Den Markt **über Preis/Notierung** formulieren, z. B. „der Preis für Brent …“ oder „die Brent-Notierung … im Vergleich zu …“ — **nicht** „das Rohöl steigt/fällt“.
- Satz 2 muss außerdem die Prozent-Bewegung und die grobe Modellrichtung (steigend/fallend/eher seitwärts) einordnen
- Ton: nicht platt oder kindlich; kein Konjunktiv, keine abgebrochenen Sätze
- Keine Hinweise auf fehlende Daten
- Maximal 45 Wörter gesamt; Antwort mit Punkt abschließen"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 320,
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
    """Gibt True zurück wenn die Tankstelle in dieser Stunde geöffnet ist (Annäherung an Aral-Zeiten)."""
    if wochentag == 5:   # Samstag 07–21
        return 7 <= stunde_h < 21
    elif wochentag == 6: # Sonntag 07–21
        return 7 <= stunde_h < 21
    else:                # Mo–Fr 06–21:30
        return 6 <= stunde_h < 22


def fill_diesel_3h_bins_hv(df_bin: pd.DataFrame, stunde_cap: pd.Timestamp) -> pd.DataFrame:
    """Fügt fehlende 3h-Stützstellen mit dem zuletzt bekannten Preis ein (lückenlose hv-Linie)."""
    if df_bin.empty:
        return df_bin
    df_bin = df_bin.sort_values("stunde").reset_index(drop=True)
    out: list[dict] = []
    for i in range(len(df_bin)):
        r = df_bin.iloc[i]
        out.append({"stunde": pd.Timestamp(r["stunde"]), "preis": float(r["preis"])})
        if i + 1 < len(df_bin):
            t0 = pd.Timestamp(df_bin.iloc[i]["stunde"])
            t1 = pd.Timestamp(df_bin.iloc[i + 1]["stunde"])
            y0 = float(df_bin.iloc[i]["preis"])
            nxt = t0 + pd.Timedelta(hours=3)
            while nxt < t1:
                out.append({"stunde": nxt, "preis": y0})
                nxt += pd.Timedelta(hours=3)
    df_out = pd.DataFrame(out).sort_values("stunde").reset_index(drop=True)
    t_last = pd.Timestamp(df_out.iloc[-1]["stunde"])
    y_last = float(df_out.iloc[-1]["preis"])
    cap = pd.Timestamp(stunde_cap)
    tail: list[dict] = []
    nxt = t_last + pd.Timedelta(hours=3)
    while nxt <= cap:
        tail.append({"stunde": nxt, "preis": y_last})
        nxt += pd.Timedelta(hours=3)
    if tail:
        df_out = pd.concat([df_out, pd.DataFrame(tail)], ignore_index=True)
    return df_out.sort_values("stunde").reset_index(drop=True)


def _stunde_naive_ns(series: pd.Series) -> pd.Series:
    """Gleicher dtype für merge_asof: datetime64[ns], ohne TZ (lokal wie Dashboard)."""
    t = pd.to_datetime(series, errors="coerce")
    if isinstance(t.dtype, pd.DatetimeTZDtype) or getattr(t.dtype, "tz", None) is not None:
        t = t.dt.tz_convert(BERLIN).dt.tz_localize(None)
    return t.astype("datetime64[ns]")


def diesel_hist_pad_3h_raster_fenster(
    df_hist: pd.DataFrame,
    jetzt_ts: pd.Timestamp,
    letzter_preis: float,
    t_fenster_start: pd.Timestamp,
) -> pd.DataFrame:
    """Alle 3h-Marken im Fenster [t_fenster_start, …] an Öffnungstagen auffüllen.

    Preis je Marke = letzte bekannte Messung davor (merge_asof backward), damit Stillstand
    an **jedem** Tag lückenlos gezeichnet wird — nicht nur heute. Fehlt am laufenden Tag
    noch ein früherer Messpunkt, wird mit letztem Live-Preis aufgefüllt (typ. API-Loch).
    """
    jetzt_ts = pd.Timestamp(jetzt_ts)
    t_fenster_start = pd.Timestamp(t_fenster_start)

    base = (
        df_hist[["stunde", "preis"]].copy()
        if not df_hist.empty
        else pd.DataFrame(columns=["stunde", "preis"])
    )
    df_ref = base.sort_values("stunde")
    if letzter_preis is not None and float(letzter_preis) > 0:
        df_ref = pd.concat(
            [
                df_ref,
                pd.DataFrame([{"stunde": jetzt_ts, "preis": float(letzter_preis)}]),
            ],
            ignore_index=True,
        )
    df_ref = df_ref.sort_values("stunde").drop_duplicates(subset=["stunde"], keep="last")
    if df_ref.empty:
        return df_hist

    d_first = t_fenster_start.normalize()
    d_last = jetzt_ts.normalize()
    if d_first > d_last:
        d_first = d_last

    stamps: list[pd.Timestamp] = []
    day = d_first
    while day <= d_last:
        is_today = day.normalize() == d_last
        cap = jetzt_ts.floor("3h") if is_today else day + pd.Timedelta(hours=21)
        for ts in pd.date_range(day, cap, freq="3h"):
            ts = pd.Timestamp(ts)
            if ts < t_fenster_start:
                continue
            h, wd = int(ts.hour), int(ts.dayofweek)
            if not ist_offen(h, wd):
                continue
            stamps.append(ts)
        day = day + pd.Timedelta(days=1)

    if not stamps:
        return df_hist

    stamp_df = (
        pd.DataFrame({"stunde": stamps})
        .drop_duplicates(subset=["stunde"])
        .sort_values("stunde")
        .reset_index(drop=True)
    )
    ref = df_ref.sort_values("stunde").reset_index(drop=True)
    stamp_df["stunde"] = _stunde_naive_ns(stamp_df["stunde"])
    ref["stunde"] = _stunde_naive_ns(ref["stunde"])
    ref = ref.dropna(subset=["stunde"]).sort_values("stunde").reset_index(drop=True)
    if ref.empty:
        return df_hist
    filled = pd.merge_asof(stamp_df, ref, on="stunde", direction="backward")
    lp = float(letzter_preis) if letzter_preis is not None and float(letzter_preis) > 0 else None
    if lp is not None:
        heute_n = jetzt_ts.normalize()
        mask_fill = (
            filled["preis"].isna()
            & (filled["stunde"].dt.normalize() == heute_n)
            & (filled["stunde"] <= jetzt_ts.floor("3h"))
        )
        filled.loc[mask_fill, "preis"] = lp
    filled = filled.dropna(subset=["preis"])

    if filled.empty:
        return df_hist

    merged = pd.concat([base, filled], ignore_index=True)
    merged = merged.sort_values("stunde").drop_duplicates(subset=["stunde"], keep="last")
    merged["stunde_h"] = merged["stunde"].dt.hour
    merged["wochentag"] = merged["stunde"].dt.dayofweek
    return merged.reset_index(drop=True)


def kw_sonntag_label(so_ts) -> str:
    """Woche Mo–So, Schlüssel Sonntag: KW (ISO) + Datumsbereich für Diagrammachsen."""
    so = pd.Timestamp(so_ts).normalize()
    mo = so - pd.Timedelta(days=6)
    kw = int(so.isocalendar()[1])
    return f"KW {kw} · {mo.strftime('%d.%m.')}–{so.strftime('%d.%m.')}"

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

# Roh-Messpunkte für KPI (Volatilität / Preiswechsel): keine 3h-Aggregation
df_kpi_preise = df_ext.copy()
if not df_live.empty:
    df_kpi_preise = (
        pd.concat([df_kpi_preise, df_live[["stunde", "preis"]]], ignore_index=True)
        .drop_duplicates("stunde", keep="last")
        .sort_values("stunde")
        .reset_index(drop=True)
    )

if not df_live.empty:
    binned = df_live.copy()
    binned["stunde"] = binned["stunde"].dt.floor("3h")
    binned = binned.groupby("stunde").agg(preis=("preis", "last")).reset_index()
    df_ext = pd.concat([df_ext, binned]).drop_duplicates(
        "stunde", keep="last").sort_values("stunde").reset_index(drop=True)

jetzt_ts = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live
if letzter_preis is None:
    letzter_preis = letzter_preis_aus_live_log(df_live_raw, jetzt_ts)
if letzter_preis is None:
    letzter_preis = letzter_preis_aus_zeitreihe(df_ext, jetzt_ts)
if letzter_preis is None or letzter_preis <= 0:
    letzter_preis = float(prognose.get("preis_aktuell", 0) or 0)
uhrzeit       = jetzt_ts.strftime("%H:%M")

# Tages-Prognose
richtung_tage   = tages.get("richtung", "—")
empfehlung_tage = tages.get("empfehlung", "—")

# Offline-Testkennzahlen (aus Metadaten, gespiegelt in prognose_tagesbasis.json)
ML_ACC_TEST = float(tages.get("richtung_accuracy_test") or 68.19)
ML_BASE_RICHT = float(tages.get("baseline_richtung_test") or 49.3)

# Historische Basis (7 Tage Chart-Fenster)
cutoff_7d  = jetzt_ts - pd.Timedelta(days=7)

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
        brent_vs_3d_pct,
    )
except:
    _nf = "Keine Prognose verfügbar."
    ki_text = tages.get("begruendung", _nf)

# Empfehlungs-Klasse
if "heute" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", tx["badge_fill_now"]
elif "übermorgen" in empfehlung_tage or "später" in empfehlung_tage or "warten" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "morgen", "badge-morgen", tx["badge_wait"]
elif "flexibel" in empfehlung_tage:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", tx["badge_flexible"]
else:
    card_cls, badge_cls, badge_txt = "warten", "badge-warten", tx["badge_hold"]

# ── TOPBAR ────────────────────────────────────────────────────────────────────
oeff_rows = "".join(
    f'<div class="topbar-hours-row"><b>{tag}</b> {zeiten}</div>'
    for tag, zeiten in tx["opening"]
)
st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-title">{tx["topbar_title"]}</div>
        <div class="topbar-addr">ARAL · Dürener Str. 407 · 50858 Köln · <a href="{ARAL_STATION_URL}" target="_blank" rel="noopener noreferrer">{tx["topbar_aral_link"]}</a></div>
        <div class="topbar-hours-heading">{tx["topbar_hours_heading"]}</div>
        <div class="topbar-hours">{oeff_rows}</div>
    </div>
    <div class="topbar-right">
        <span class="topbar-time">{tx["topbar_live"]} {uhrzeit}</span>
        <form class="topbar-refresh-form" method="get" action="">
            <input type="hidden" name="refresh" value="1" />
            <button type="submit" class="topbar-refresh">{tx["topbar_refresh"]}</button>
        </form>
    </div>
</div>
""", unsafe_allow_html=True)

# Refresh via Query-Parameter (Submit in der Topbar, gleiche Seite)
if st.query_params.get("refresh") == "1":
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

st.markdown(
    f'<div class="section-label section-label-first">{tx["section_glance"]}</div>',
    unsafe_allow_html=True,
)

# ── METRIKEN ──────────────────────────────────────────────────────────────────
delta_val   = letzter_preis - mean_ref
delta_cent  = delta_val * 100
delta_cls  = "delta-green" if delta_val < 0 else "delta-red"
delta_sign = "−" if delta_val < 0 else "+"

if richtung_tage == "fällt":
    tend_pfeil, tend_cls = "↓", "tendenz-down"
elif richtung_tage == "steigt":
    tend_pfeil, tend_cls = "↑", "tendenz-up"
else:
    tend_pfeil, tend_cls = "→", "tendenz-flat"

st.markdown(f"""
<div class="metric-grid">
    <div class="card">
        <div class="card-head"><div class="card-title">{tx["card_avg_yesterday"]}</div></div>
        <div class="card-main"><div class="card-value">{preis_fmt(mean_ref)} &euro;</div></div>
        <div class="card-foot"></div>
    </div>
    <div class="card">
        <div class="card-head"><div class="card-title">{tx["card_current"]} {uhrzeit}</div></div>
        <div class="card-main"><div class="card-value">{preis_fmt(letzter_preis)} &euro;</div></div>
        <div class="card-foot"><span class="{delta_cls}">{delta_sign} {abs(delta_cent):.1f} {tx["vs_avg_yesterday"]}</span></div>
    </div>
    <div class="card card--model-direction">
        <div class="card-head"><div class="card-title">{tx["card_model_dir"]}</div></div>
        <div class="card-main"><div class="tendenz-val-model {tend_cls}">{tend_pfeil}</div></div>
        <div class="card-foot card-foot--empty"></div>
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
<div class="ki-wrap">
<div class="empfehlung-card" style="border-left-color: {emp_border}">
    <div class="empfehlung-text">{ki_text}</div>
</div>
</div>
""", unsafe_allow_html=True)

TAB_LABELS = [tx["tab_price"], tx["tab_kpi"], tx["tab_perf"]]

tab_pv, tab_kpi, tab_perf = st.tabs(TAB_LABELS)

# ─── TAB 1: Preisverlauf ─────────────────────────────────────────────────────
with tab_pv:
    st.markdown(f'<div class="section-label">{tx["pv_section"]}</div>',
                unsafe_allow_html=True)
    show_brent = st.toggle(tx["pv_brent_toggle"], value=False, key="show_brent_line")
    if show_brent:
        if not df_brent.empty:
            letzter_brent = pd.to_datetime(df_brent["stunde"]).max()
            st.caption(f"{tx['pv_brent_cap']} {brent_source} · {tx['pv_brent_last']} {letzter_brent.strftime('%d.%m.%Y %H:%M')}")
        else:
            st.caption(f"{tx['pv_brent_cap']} {brent_source} · {tx['pv_brent_none']}")

    # 3h-Bins: letzter Preis je Bin (wie Live-Kachel), nicht Mittelwert — sonst Abweichung zur Kachel.
    # 3h-Raster an Öffnungstagen im 7-Tage-Fenster (API loggt oft nicht bei Preisstillstand).
    df_hist_fuer_pv = diesel_hist_pad_3h_raster_fenster(
        df_hist, jetzt_ts, letzter_preis, cutoff_7d
    )
    df_hist_bin_sparse = df_hist_fuer_pv.copy()
    df_hist_bin_sparse["stunde_bin"] = df_hist_bin_sparse["stunde"].dt.floor("3h")
    df_hist_bin_sparse = (
        df_hist_bin_sparse.groupby("stunde_bin")["preis"].last().reset_index()
        .rename(columns={"stunde_bin": "stunde"})
    )
    aktueller_bin_start = jetzt_ts.floor("3h")
    aktueller_bin_ende = aktueller_bin_start + pd.Timedelta(hours=3)
    df_hist_bin = fill_diesel_3h_bins_hv(df_hist_bin_sparse, aktueller_bin_start)

    fig = go.Figure()
    # Eine durchgehende graue hv-Linie inkl. aktuellem Bin bis Live-Preis (keine Trace-Lücke).
    if not df_hist_bin.empty:
        y_bin_end = float(df_hist_bin.iloc[-1]["preis"])
        x_die = list(df_hist_bin["stunde"]) + [aktueller_bin_ende, aktueller_bin_ende]
        y_die = list(df_hist_bin["preis"]) + [y_bin_end, letzter_preis]
        fig.add_trace(go.Scatter(
            x=x_die, y=y_die,
            mode="lines", name=tx["legend_diesel"],
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
                name=tx["legend_brent"],
                yaxis="y2",
                line=dict(color="#2E7D32", width=1.3),
            ))

    # Tages-Mittelwert (Kalendertag). Für heute: bis "jetzt".
    # Darstellung nur innerhalb der Öffnungszeiten (keine "Nacht-Linie").
    # Start/Ende werden an sichtbare 3h-Bins gekoppelt, damit nichts "verschoben" wirkt.
    df_hist_day = df_hist_all.copy()
    df_hist_day["tag"] = df_hist_day["stunde"].dt.normalize()
    if not df_hist_day.empty:
        heute_norm = jetzt_ts.normalize()
        df_past = df_hist_day[df_hist_day["tag"] < heute_norm]
        df_hist_bin_day = df_hist_bin_sparse.copy()
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
                # Schluss laut tankstelle.aral.de: Mo–Fr 21:30, Sa–So 21:00
                if wd < 5:
                    return tag_ts + pd.Timedelta(hours=21, minutes=30)
                return tag_ts + pd.Timedelta(hours=21, minutes=0)

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
                    mode="lines", name=tx["legend_day_avg"],
                    line=dict(color="#1565C0", width=2.5),
                    connectgaps=False,
                ))

    # Mitternacht-Linien (nur im gezeigten Verlaufsfenster)
    mitternacht = []
    tag = cutoff_7d.normalize()
    mitternacht_ende = jetzt_ts.normalize()
    while tag <= mitternacht_ende:
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
            title=tx["yaxis_diesel"]
        ),
        yaxis2=dict(
            overlaying="y", side="right", showgrid=False, zeroline=False,
            tickfont=dict(size=12, color="#8D6E63"),
            ticksuffix=" €",
            tickformat=".2f",
            title=tx["yaxis_brent"]
        ),
        legend=dict(orientation="h", y=-0.18, font=dict(size=13, color="#757575"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=20, t=15, b=10),
        height=380, hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#E0E0E0",
                        font=dict(color="#212529", size=13, family="Roboto")),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_kpi:
    st.markdown(f'<div class="section-label">{tx["kpi_section"]}</div>',
                unsafe_allow_html=True)

    heute_datum = jetzt_ts.normalize().date()
    tag_letzter = heute_datum - timedelta(days=1)
    # Letzte 14 Kalendertage bis einschließlich gestern (14 verschiedene Daten)
    tag_end_ts = pd.Timestamp(tag_letzter).normalize()
    cutoff_kpi = tag_end_ts - pd.Timedelta(days=13)
    cutoff_14d = cutoff_kpi

    # KPI nur aus df_kpi_preise (Parquet + Roh-Live), nicht aus 3h-gebinntem df_ext.
    # Volatilität: ganzer Tag. Preiswechsel: echte Sprünge |Δpreis|>ε (Öffnungszeiten).
    df_kpi_14 = df_kpi_preise[
        (df_kpi_preise["stunde"] >= cutoff_14d) &
        (df_kpi_preise["stunde"].dt.date < heute_datum)
    ].copy().sort_values("stunde")
    df_kpi_14["tag"] = df_kpi_14["stunde"].dt.date

    alle_kpi_tage = pd.date_range(cutoff_kpi, tag_end_ts, freq="D").normalize()

    _eps_sw = 1e-6  # EUR/l, unter typischer Tankstellen-Schrittweite; filtert Float-Rauschen
    _h = df_kpi_14["stunde"].dt.hour.to_numpy()
    _wd = df_kpi_14["stunde"].dt.dayofweek.to_numpy()
    _mo_fr = (_wd < 5) & (_h >= 6) & (_h < 22)
    _sa_so = (_wd >= 5) & (_h >= 7) & (_h < 21)
    _mask_oeff = _mo_fr | _sa_so
    df_chg_14 = df_kpi_14.loc[_mask_oeff, ["stunde", "preis"]].copy()
    df_chg_14["tag"] = df_chg_14["stunde"].dt.date
    df_chg_14["delta"] = df_chg_14.groupby("tag", group_keys=False)["preis"].diff()
    df_chg_14["ist_sprung"] = df_chg_14["delta"].notna() & (
        df_chg_14["delta"].abs() >= _eps_sw
    )
    df_tag = df_chg_14.groupby("tag", as_index=False).agg(
        n_aenderungen=("ist_sprung", "sum"),
    )
    df_vol = (
        df_kpi_14.groupby("tag", as_index=False).agg(preis=("preis", "std"))
        if not df_kpi_14.empty
        else pd.DataFrame(columns=["tag", "preis"])
    )

    df_tag["tag"] = pd.to_datetime(df_tag["tag"]).dt.normalize()
    df_tag = (
        pd.DataFrame({"tag": alle_kpi_tage})
        .merge(df_tag, on="tag", how="left")
        .assign(n_aenderungen=lambda d: d["n_aenderungen"].fillna(0).astype(int))
    )
    # Ø über alle 14 angezeigten Kalendertage (fehlende Tage = 0 Wechsel)
    aend_tag = float(df_tag["n_aenderungen"].mean()) if not df_tag.empty else 0.0

    if not df_vol.empty:
        df_vol["tag"] = pd.to_datetime(df_vol["tag"]).dt.normalize()
    df_vol_plot = (
        pd.DataFrame({"tag": alle_kpi_tage})
        .merge(df_vol, on="tag", how="left")
    )
    # Karten-Ø: alle 14 Tage; Tage ohne Messpunkte zählen als 0 ct Volatilität
    volatilitaet = (
        float(df_vol_plot["preis"].fillna(0.0).mean())
        if not df_vol_plot.empty
        else 0.0
    )

    # KPI-Cards: Ø Änderungen, Ø Volatilität
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;margin-bottom:1.25rem">
        <div class="kpi-card"><div class="kpi-val">{aend_tag:.1f}</div><div class="kpi-lbl">{tx["kpi_chg_lbl"]}</div></div>
        <div class="kpi-card"><div class="kpi-val">{volatilitaet*100:.1f}<span style="font-size:0.75rem"> ct</span></div><div class="kpi-lbl">{tx["kpi_vol_lbl"]}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Kein xaxis hier — sonst kollidiert **BASE_L mit xaxis=kpi_xaxis (TypeError).
    BASE_L = dict(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                  margin=dict(l=10, r=10, t=10, b=10),
                  legend=dict(orientation="h", y=-0.35, font=dict(size=12)))

    _kpi_tick_vals = alle_kpi_tage.tolist()
    _kpi_tick_txt = [pd.Timestamp(t).strftime("%d.%m.") for t in _kpi_tick_vals]
    kpi_xaxis = dict(
        type="date",
        gridcolor="#F5F5F5",
        tickmode="array",
        tickvals=_kpi_tick_vals,
        ticktext=_kpi_tick_txt,
        range=[
            cutoff_kpi - pd.Timedelta(hours=6),
            tag_end_ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
        ],
        hoverformat="%d.%m.%Y",
    )

    st.caption(
        tx["kpi_cap_range"].format(
            a=cutoff_kpi.strftime("%d.%m.%Y"),
            b=tag_end_ts.strftime("%d.%m.%Y"),
        )
    )
    st.caption(tx["kpi_cap_chg_def"])
    st.caption(tx["kpi_cap_kpi_src"])

    # Preiswechsel / Tag
    st.markdown(f'<div class="section-label">{tx["kpi_sec_chg"]}</div>',
                unsafe_allow_html=True)
    fig3 = go.Figure()
    if not df_tag.empty:
        fig3.add_trace(go.Scatter(
            x=df_tag["tag"], y=df_tag["n_aenderungen"],
            mode="lines", name=tx["kpi_legend_chg"], line=dict(color="#1565C0", width=1.5),
            hovertemplate=tx["kpi_hover_chg"],
        ))
    fig3.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False),
        xaxis=kpi_xaxis)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f'<div class="section-label">{tx["kpi_sec_vol"]}</div>',
                unsafe_allow_html=True)
    fig6_kpi = go.Figure()
    if not df_vol_plot.empty:
        _y_vol = df_vol_plot["preis"] * 100
        fig6_kpi.add_trace(go.Scatter(
            x=df_vol_plot["tag"], y=_y_vol,
            mode="lines", name=tx["kpi_legend_vol"],
            line=dict(color="#E65100", width=1.5),
            connectgaps=False,
            hovertemplate=tx["kpi_hover_vol"],
        ))
    fig6_kpi.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"),
        xaxis=kpi_xaxis)
    st.plotly_chart(fig6_kpi, use_container_width=True)

with tab_perf:
    st.markdown(f'<div class="section-label">{tx["perf_section"]}</div>',
                unsafe_allow_html=True)
    st.caption(
        tx["perf_cap"].format(acc=ML_ACC_TEST, base=ML_BASE_RICHT)
    )

    if df_prog_log.empty:
        st.info(tx["perf_no_log"])
    else:
        # Kalendertag & „gestern“ strikt nach Europe/Berlin (00:00 Uhr Tagesgrenze), unabhängig von jetzt_ts
        heute_date = datetime.now(BERLIN).date()
        gestern_date = heute_date - timedelta(days=1)
        heute_dt = pd.Timestamp(datetime.combine(heute_date, datetime.min.time()))
        start_laufende_woche = heute_dt - pd.Timedelta(days=int(heute_dt.dayofweek))
        # Letzte 3 vollständige Kalenderwochen (Mo–So), ohne laufende Woche
        first_day_3voll = start_laufende_woche - pd.Timedelta(weeks=3)
        last_day_3voll = start_laufende_woche - pd.Timedelta(days=1)

        df_pl = df_prog_log.copy()
        df_pl["_tag"] = _datum_berlin_tag(df_pl["datum"])
        d0 = pd.Timestamp(first_day_3voll).date()
        d1 = pd.Timestamp(last_day_3voll).date()
        df_log_3w = df_pl[
            (df_pl["_tag"] >= d0) & (df_pl["_tag"] <= d1)
        ].copy().sort_values("datum")
        min_14 = heute_date - timedelta(days=14)
        df_log_14 = df_pl[
            (df_pl["_tag"] >= min_14) & (df_pl["_tag"] <= gestern_date)
        ].copy().sort_values("datum")

        df_log_3w_ric = df_log_3w.dropna(subset=["richtung_korrekt"])
        n_tage = len(df_log_3w_ric)
        n_korrekt = int(df_log_3w_ric["richtung_korrekt"].sum()) if n_tage > 0 else 0
        acc_3w = df_log_3w_ric["richtung_korrekt"].mean() * 100 if n_tage > 0 else 0

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-val">{acc_3w:.1f}<span style="font-size:0.75rem">%</span></div>
                <div class="kpi-lbl">{tx["perf_acc_3w"]}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{n_korrekt}/{n_tage}</div>
                <div class="kpi-lbl">{tx["perf_ok_3w"]}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{ML_ACC_TEST:.1f}<span style="font-size:0.75rem">%</span></div>
                <div class="kpi-lbl">{tx["perf_acc_nb"]}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val">{ML_BASE_RICHT:.1f}<span style="font-size:0.75rem">%</span></div>
                <div class="kpi-lbl">{tx["perf_baseline"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Prognose-Trefferquote (Kalender): 4 Mo–So-Wochen; farbige Kacheln nur bei Log-Zeile (bis gestern)
        montag_4w_start = start_laufende_woche - pd.Timedelta(weeks=3)
        sonntag_woche_aktuell = start_laufende_woche + pd.Timedelta(days=6)
        st.markdown(
            f'<div class="section-label">{tx["perf_cal_title"]}</div>',
            unsafe_allow_html=True,
        )
        st.caption(tx["perf_cal_cap"])

        def rich_pfeil(delta_ct):
            if delta_ct > 0.5:
                return "↑"
            if delta_ct < -0.5:
                return "↓"
            return "→"

        fd = pd.Timestamp(montag_4w_start).date()
        # Keine leeren Kacheln für Tage nach dem letzten ausgewerteten Kalendertag (gestern)
        ld = min(pd.Timestamp(sonntag_woche_aktuell).date(), gestern_date)
        if ld < fd:
            ld = fd
        alle_tage = [fd + timedelta(days=i) for i in range((ld - fd).days + 1)]
        log_dict = {
            r["_tag"]: r
            for _, r in df_pl[df_pl["_tag"] <= gestern_date].iterrows()
            if pd.notna(r["richtung_korrekt"])
        }

        header_html = (
            '<div class="kalender-woche">'
            + "".join(
                f'<div class="kalender-header">{w}</div>'
                for w in tx["cal_weekdays"]
            )
            + "</div>"
        )
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
            erster_wt = woche[0].weekday()
            letzter_wt = woche[-1].weekday()
            woche_html = '<div class="kalender-woche">'
            for _ in range(erster_wt):
                woche_html += '<div class="tag-kachel leer"></div>'
            for tag in woche:
                if tag in log_dict:
                    row = log_dict[tag]
                    korr = int(row["richtung_korrekt"])
                    cls = "korrekt" if korr == 1 else "falsch"
                    p_ct = row["predicted_delta"] * 100
                    a_ct = row["actual_delta"] * 100
                    p_pf = rich_pfeil(p_ct)
                    a_pf = rich_pfeil(a_ct)
                    datum = tag.strftime("%d.%m")
                    woche_html += f"""<div class="tag-kachel {cls}" style="min-height:72px">
                        <span class="tag-datum">{datum}</span>
                        <span class="tag-delta">P {p_pf} {p_ct:+.1f}</span>
                        <span class="tag-delta">A {a_pf} {a_ct:+.1f}</span>
                    </div>"""
                else:
                    woche_html += '<div class="tag-kachel leer"></div>'
            for _ in range(6 - letzter_wt):
                woche_html += '<div class="tag-kachel leer"></div>'
            woche_html += "</div>"
            st.markdown(woche_html, unsafe_allow_html=True)

        # Wöchentliche Trefferquote: 3 letzte vollständige Kalenderwochen (Mo–So), Schlüssel = Wochenende So.
        sonntage_3voll = pd.to_datetime([
            start_laufende_woche - pd.Timedelta(days=15),
            start_laufende_woche - pd.Timedelta(days=8),
            start_laufende_woche - pd.Timedelta(days=1),
        ]).normalize()
        df_week = df_log_3w.dropna(subset=["richtung_korrekt"]).copy()
        if not df_week.empty:
            d = pd.to_datetime(df_week["_tag"].astype(str))
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
        st.markdown(
            f'<div class="section-label">{tx["perf_weekly_title"]}</div>',
            unsafe_allow_html=True,
        )
        fig_week = go.Figure()
        fig_week.add_trace(go.Bar(
            x=df_plot["wochenende_so"], y=df_plot["acc_pct"],
            name=tx["perf_bar_hover"], marker_color="#1565C0",
            hovertemplate=f"%{{customdata}}<br>{tx['perf_bar_hover']}: %{{y:.0f}} %<extra></extra>",
            customdata=[
                kw_sonntag_label(ts) + (f" · {n} {tx['perf_bar_days']}" if n else "")
                for ts, n in zip(df_plot["wochenende_so"], df_plot["n_tage"])
            ],
        ))
        fig_week.update_layout(
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=240,
            margin=dict(l=10, r=10, t=12, b=72),
            xaxis=dict(
                gridcolor="#F5F5F5",
                tickmode="array", tickvals=df_plot["wochenende_so"],
                ticktext=[kw_sonntag_label(ts) for ts in df_plot["wochenende_so"]],
                tickangle=0,
            ),
            yaxis=dict(gridcolor="#F5F5F5", zeroline=False, range=[0, 100], ticksuffix=" %"),
            showlegend=False
        )
        st.plotly_chart(fig_week, use_container_width=True)

        # Predicted vs. Actual — nur wenn Log-Punkte im Fenster vorhanden
        if not df_log_14.empty:
            st.markdown(
                f'<div class="section-label">{tx["perf_pred_actual_title"]}</div>',
                unsafe_allow_html=True,
            )
            # Explizit Europe/Berlin, damit Plotly die Achse nicht als UTC-Mitternacht verschiebt
            x_14 = pd.to_datetime(df_log_14["_tag"].astype(str)).dt.tz_localize(BERLIN)
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Scatter(
                x=x_14,
                y=df_log_14["predicted_delta"]*100,
                mode="lines+markers", name=tx["perf_trace_pred"],
                line=dict(color="#1565C0", width=2), marker=dict(size=5),
                hovertemplate=tx["perf_hover_pred"],
            ))
            fig_perf.add_trace(go.Scatter(
                x=x_14,
                y=df_log_14["actual_delta"]*100,
                mode="lines+markers", name=tx["perf_trace_act"],
                line=dict(color="#E65100", width=2), marker=dict(size=5),
                hovertemplate=tx["perf_hover_act"],
            ))
            fig_perf.add_hrect(y0=-0.5, y1=0.5,
                               fillcolor="#F5F5F5", opacity=0.6, line_width=0)
            fig_perf.add_hline(y=0, line_dash="dash", line_color="#CCCCCC", line_width=1)
            fig_perf.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=-0.25, font=dict(size=12)),
                xaxis=dict(
                    type="date", gridcolor="#F5F5F5",
                    tickformat="%d.%m.", dtick=86400000.0, hoverformat="%d.%m.%Y",
                ),
                yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_perf, use_container_width=True)
            st.caption(tx["perf_band_cap"])

# ── Links (nach Tabs) ───────────────────────────────────────────────────────
st.markdown(f"""
<div class="social-info-wrap">
  <div class="social-row-links">
    <div class="social-strip">
      <a href="https://github.com/felixschrader/dieselpreisprognose" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_GH}</span> {tx["social_github"]}
      </a>
      <span class="social-strip-sep">·</span>
      <a href="{SOCIAL_TEAM["felix"]["linkedin"]}" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> {SOCIAL_TEAM["felix"]["name"]}
      </a>
      <span class="social-strip-sep">·</span>
      <a href="{SOCIAL_TEAM["girandoux"]["linkedin"]}" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> {SOCIAL_TEAM["girandoux"]["name"]}
      </a>
      <span class="social-strip-sep">·</span>
      <a href="{SOCIAL_TEAM["ghislain"]["linkedin"]}" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> {SOCIAL_TEAM["ghislain"]["name"]}
      </a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer-wrap">
  <div class="footer-mini">
    {tx["footer_price"]} {tx["footer_mtsk"]}<br>
    <a href="https://data-science-institute.de/" target="_blank" rel="noopener noreferrer">DSI — Data Science Institute by Fabian Rappert</a>
    · {tx["footer_dsi"]}
  </div>
</div>
""", unsafe_allow_html=True)