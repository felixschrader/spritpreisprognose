# dashboard.py — Spritpreisprognose ARAL Dürener Str. 407 · 50858 Köln
# Streamlit Cloud · DSI Capstone Projekt 2026

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import pytz

st.set_page_config(
    page_title="Dieselpreis · Köln",
    page_icon="gas-station-fuel-svgrepo-com.svg",
    layout="centered",
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
# Referenzpunkt wie in tankerkoenig_pipeline.py (Köln · Aral Dürener Str. 407)
STATION_LAT  = 50.919537
STATION_LON  = 6.852624
# Kölner Dom (Domplatte, grobe Referenz)
KOELNER_DOM_LAT = 50.9413
KOELNER_DOM_LON = 6.9583
ARAL_STATION_URL = "https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400"
# Leaflet: Tankstelle + Dom im Blick, Rand-Puffer (Anteil der Kartenbreite/-höhe in Pixeln)
MAP_FIT_PADDING_FRAC = 0.10
MAP_FIT_MAX_ZOOM = 18
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

# Öffnungszeiten laut tankstelle.aral.de (Stand: Oliver Rosenbach, Dürener Str. 407)
OEFFNUNG_VON = 6   # 06:00 Uhr
OEFFNUNG_BIS = 22  # konservativ für 3h-Bins / Charts (Schluss je nach Wochentag s. ist_offen)

OEFFNUNGSZEITEN = [
    ("Mo – Fr", "06:00 – 21:30"),
    ("Sa",      "07:00 – 21:00"),
    ("So",      "07:00 – 21:00"),
]

_SVG_GH = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#24292f" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/></svg>"""
_SVG_IN = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.125 2.062 2.062 0 0 1 0 4.125zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>"""

def osm_standort_embed(
    lat: float,
    lon: float,
    height: int = 200,
    dom_lat: float = KOELNER_DOM_LAT,
    dom_lon: float = KOELNER_DOM_LON,
) -> None:
    """OpenStreetMap über Leaflet: Tankstelle + Dom, fitBounds mit Rand-Puffer, Vollbild."""
    pf = float(MAP_FIT_PADDING_FRAC)
    mz = int(MAP_FIT_MAX_ZOOM)
    html = f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<style>
.osm-leaflet-wrap {{ margin:0; border-radius:12px; border:1px solid #E4E8EF; box-shadow:0 1px 2px rgba(16,24,40,0.05),0 4px 12px rgba(16,24,40,0.06); overflow:hidden; position:relative; background:#E8ECF2; }}
.osm-leaflet-fs {{ position:relative; width:100%; height:{height}px; }}
.osm-leaflet-fs:fullscreen {{ height:100vh !important; width:100% !important; border-radius:0; }}
.osm-leaflet-fs:fullscreen .osm-leaflet-inner {{ height:100vh !important; }}
.osm-fs-btn {{
  position:absolute; z-index:1000; top:8px; right:8px;
  padding:8px 14px; font-size:14px; font-weight:600; font-family:Roboto,sans-serif;
  cursor:pointer; border:1px solid #BDBDBD; border-radius:6px;
  background:#FFFFFF; color:#424242; box-shadow:0 1px 4px rgba(0,0,0,0.12);
}}
.osm-fs-btn:hover {{ background:#F5F5F5; border-color:#9E9E9E; }}
.osm-leaflet-inner {{ width:100%; height:100%; min-height:{height}px; }}
.osm-osm-attribution {{ font-size:0.9rem; color:#5C6370; margin-top:8px; font-family:Roboto,sans-serif; line-height:1.45; }}
</style>
<div class="osm-leaflet-wrap content-block-map">
  <div id="osm-leaflet-fs" class="osm-leaflet-fs">
    <button type="button" class="osm-fs-btn" id="osm-fs-btn" title="Karte im Vollbild">Vollbild</button>
    <div id="osm-leaflet-map" class="osm-leaflet-inner" role="img" aria-label="Karte Standort Tankstelle"></div>
  </div>
</div>
<div class="osm-osm-attribution">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" style="color:#616161;">OpenStreetMap</a></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
(function() {{
  var mlat = {lat}, mlon = {lon}, dlat = {dom_lat}, dlon = {dom_lon}, mapH = {height};
  var padFrac = {pf}, maxZ = {mz};
  function invalidate(m) {{ if (m) {{ setTimeout(function() {{ m.invalidateSize(true); }}, 50); }} }}
  function init() {{
    var el = document.getElementById('osm-leaflet-map');
    if (!el || typeof L === 'undefined') return;
    var map = L.map('osm-leaflet-map', {{
      zoomControl: true, scrollWheelZoom: true, attributionControl: false
    }});
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19, attribution: ''
    }}).addTo(map);
    var bounds = L.latLngBounds([[mlat, mlon], [dlat, dlon]]);
    L.marker([mlat, mlon]).bindTooltip('ARAL Tankstelle', {{ sticky: true }}).addTo(map);
    function fitWithPadding() {{
      invalidate(map);
      setTimeout(function() {{
        var s = map.getSize();
        var padX = Math.round(s.x * padFrac);
        var padY = Math.round(s.y * padFrac);
        map.fitBounds(bounds, {{
          padding: [padX, padY],
          animate: false,
          maxZoom: maxZ
        }});
      }}, 60);
    }}
    fitWithPadding();
    var fsRoot = document.getElementById('osm-leaflet-fs');
    var btn = document.getElementById('osm-fs-btn');
    btn.addEventListener('click', function() {{
      if (!document.fullscreenElement) {{
        fsRoot.requestFullscreen().catch(function() {{}});
      }} else {{
        document.exitFullscreen();
      }}
    }});
    document.addEventListener('fullscreenchange', function() {{
      var inner = document.getElementById('osm-leaflet-map');
      if (document.fullscreenElement === fsRoot) {{
        btn.textContent = 'Vollbild beenden';
        inner.style.minHeight = '100vh';
        fsRoot.style.height = '100vh';
      }} else {{
        btn.textContent = 'Vollbild';
        inner.style.minHeight = mapH + 'px';
        fsRoot.style.height = mapH + 'px';
      }}
      fitWithPadding();
    }});
  }}
  setTimeout(init, 0);
}})();
</script>
"""
    components.html(html, height=height + 36, scrolling=False)

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
.topbar-hours {
    margin-top: 12px;
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
_HTTP_NO_CACHE = {"Cache-Control": "no-cache", "Pragma": "no-cache"}


@st.cache_data(ttl=60)
def lade_prognose():
    return requests.get(JSON_URL, timeout=10, headers=_HTTP_NO_CACHE).json()

@st.cache_data(ttl=60)
def lade_tagesprognose():
    try:
        return requests.get(TAGES_URL, timeout=10, headers=_HTTP_NO_CACHE).json()
    except:
        return {}

@st.cache_data(ttl=120)
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
        # Tagesdatum immer auf 00:00 Uhr normieren (keine Sub-Tages-Zeiten aus der CSV)
        df["datum"] = pd.to_datetime(df["datum"], errors="coerce").dt.floor("D")
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
def generiere_empfehlung(preis, mean_ref, richtung_tage, brent_vs_3d_pct, _prompt_version: int = 3):
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

def kw_sonntag_label(so_ts) -> str:
    """Woche Mo–So, Schlüssel Sonntag: KW (ISO) + Datumsbereich für Diagrammachsen."""
    so = pd.Timestamp(so_ts).normalize()
    mo = so - pd.Timedelta(days=6)
    kw = int(so.isocalendar()[1])
    return f"KW {kw} · {mo.strftime('%d.%m.')}–{so.strftime('%d.%m.')}"

def baue_prognose_linie(jetzt_ts, letzter_preis, kern_preis, pred_delta_cent, hist_28d_df, df_hist_all):
    """
    Fortsetzung ab „jetzt“: pro 3h-Bin ein Faktor α aus **gestern**, wie weit der
    Bin-Mittel zwischen **Kern** (P10 der Stunden 13–20, wie in der Pipeline) und
    **Tageshoch** (max. Bin-Mittel) lag. Heute und morgen:
    preis = (kern_heute + shift) + α · (tageshoch_heute − kern_heute), shift=0 bzw. predΔ.

    Früh am Kalendertag ist (tageshoch_heute − kern) oft ~0 → ohne Fallback eine
    flache Linie; dann Referenzspanne vom Vortag (denom) verwenden.

    Für den laufenden Kalendertag: Mischung aus gestrigem Bin-Preis (gleiche 3h-Bin)
    und morgigem Modellpunkt (kern + predΔ + α·Spanne), Anteil morgen steigt über
    den Tag (ca. voll nach ~18 h), damit die Linie nicht dauerhaft zu niedrig liegt.

    Zusätzlich wird ein generisches Tagesprofil aus den letzten 28 Tagen verwendet
    (stunden/bin-typische Muster). Das dämpft Ausreißer einzelner Tage, sodass
    Morgen-/Mittagswellen plausibel bleiben und nicht unrealistisch „spiken“.

    Form-Regel: Mittags-/Nachmittagspeak liegt grundsätzlich unter Morgenpeak.
    """
    # Mittag/Nachmittag soll max. diesen Anteil vom Morgenpeak haben.
    MITTAG_VS_MORGEN_MAX_RATIO = 0.80
    KERN_H = list(range(13, 21))  # wie live_inference_tagesbasis (13–20 Uhr)
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

    gf_kern = df_gestern[df_gestern["stunde_h"].isin(KERN_H)]["preis"]
    if len(gf_kern) >= 2:
        kern_y = float(gf_kern.quantile(0.10))
    else:
        kern_y = float(df_gestern["preis"].quantile(0.10))

    df_g_bin = df_gestern.copy()
    df_g_bin["bin3"] = (df_g_bin["stunde"].dt.hour // 3) * 3
    df_g_bin = df_g_bin.groupby("bin3")["preis"].mean().reset_index().sort_values("bin3")
    if df_g_bin.empty:
        return pd.DataFrame(columns=["stunde", "preis"])

    max_y = float(df_g_bin["preis"].max())
    min_y = float(df_g_bin["preis"].min())
    denom = max_y - kern_y
    if denom < 1e-6:
        denom = max(max_y - min_y, 0.01)

    alpha_map = {}
    for _, row in df_g_bin.iterrows():
        b = int(row["bin3"])
        yb = float(row["preis"])
        alpha_map[b] = (yb - kern_y) / denom

    # Generisches Tagesprofil aus 28 Tagen (robust gegen einzelne Ausreißer)
    profile_alpha_map = {}
    profile_span_vals = []
    if hist_28d_df is not None and not hist_28d_df.empty:
        h28 = hist_28d_df[["stunde", "preis"]].copy()
        h28["stunde"] = pd.to_datetime(h28["stunde"], errors="coerce")
        h28["preis"] = pd.to_numeric(h28["preis"], errors="coerce")
        h28 = h28.dropna(subset=["stunde", "preis"]).copy()
        h28["tag"] = h28["stunde"].dt.normalize()
        h28["stunde_h"] = h28["stunde"].dt.hour
        h28["wochentag"] = h28["stunde"].dt.dayofweek
        h28 = h28[h28.apply(lambda r: ist_offen(r["stunde_h"], r["wochentag"]), axis=1)].copy()
        if not h28.empty:
            h28["bin3"] = (h28["stunde"].dt.hour // 3) * 3
            kern_by_day = h28[h28["stunde_h"].isin(KERN_H)].groupby("tag")["preis"].quantile(0.10)
            if kern_by_day.empty:
                kern_by_day = h28.groupby("tag")["preis"].quantile(0.10)
            bin_by_day = h28.groupby(["tag", "bin3"])["preis"].mean().reset_index()
            max_by_day = bin_by_day.groupby("tag")["preis"].max()
            day_df = pd.DataFrame({"kern": kern_by_day, "mx": max_by_day}).dropna()
            day_df["span"] = (day_df["mx"] - day_df["kern"]).clip(lower=0.01)
            profile_span_vals = day_df["span"].tolist()
            if not day_df.empty:
                kmap = day_df["kern"].to_dict()
                smap = day_df["span"].to_dict()
                bin_by_day["alpha"] = bin_by_day.apply(
                    lambda r: (float(r["preis"]) - float(kmap.get(r["tag"], np.nan))) / float(smap.get(r["tag"], 0.01)),
                    axis=1,
                )
                p = bin_by_day.dropna(subset=["alpha"]).groupby("bin3")["alpha"].median()
                profile_alpha_map = {int(k): float(v) for k, v in p.to_dict().items()}
    # Datenbasierte Abendregel: Kommt nach 16:00 historisch oft noch ein Anstieg?
    allow_after16_rebound = False
    close_drop_frac = 0.0
    if hist_28d_df is not None and not hist_28d_df.empty:
        hh = hist_28d_df[["stunde", "preis"]].copy()
        hh["stunde"] = pd.to_datetime(hh["stunde"], errors="coerce")
        hh["preis"] = pd.to_numeric(hh["preis"], errors="coerce")
        hh = hh.dropna(subset=["stunde", "preis"]).sort_values("stunde")
        hh["tag"] = hh["stunde"].dt.normalize()
        hh["stunde_h"] = hh["stunde"].dt.hour
        hh["wochentag"] = hh["stunde"].dt.dayofweek
        hh = hh[hh.apply(lambda r: ist_offen(r["stunde_h"], r["wochentag"]), axis=1)].copy()
        if not hh.empty:
            hh["bin3"] = (hh["stunde"].dt.hour // 3) * 3
            db = hh.groupby(["tag", "bin3"])["preis"].mean().reset_index().sort_values(["tag", "bin3"])
            post16 = db[db["bin3"] >= 15].copy()
            if not post16.empty:
                post16["d"] = post16.groupby("tag")["preis"].diff()
                # "Abendrebound" = nach 16 Uhr gab es mindestens einen relevanten Anstieg (>0.2 ct).
                day_flag = post16.groupby("tag")["d"].apply(lambda s: (s > 0.002).any())
                if len(day_flag) >= 6:
                    allow_after16_rebound = float(day_flag.mean()) >= 0.35
            # Typischer Abendschluss-Rueckgang: Schluss-Bin relativ zum Tagespeak (09-18 Uhr).
            day_peak = db[db["bin3"].between(9, 18)].groupby("tag")["preis"].max()
            day_close = db[db["bin3"] >= 18].groupby("tag")["preis"].last()
            dd = pd.DataFrame({"peak": day_peak, "close": day_close}).dropna()
            if len(dd) >= 6:
                rel = ((dd["peak"] - dd["close"]) / dd["peak"]).replace([np.inf, -np.inf], np.nan).dropna()
                if len(rel) >= 6:
                    close_drop_frac = float(np.clip(rel.median(), 0.0, 0.06))

    # Gestern + generisches Profil kombinieren
    alpha_mix = {}
    bins_all = set(alpha_map.keys()) | set(profile_alpha_map.keys())
    for b in bins_all:
        a_y = alpha_map.get(b)
        a_p = profile_alpha_map.get(b)
        if a_y is not None and a_p is not None:
            alpha_mix[b] = 0.35 * float(a_y) + 0.65 * float(a_p)
        elif a_p is not None:
            alpha_mix[b] = float(a_p)
        elif a_y is not None:
            alpha_mix[b] = float(a_y)

    if alpha_mix:
        alpha_map = alpha_mix
    default_alpha = float(np.median(list(alpha_map.values()))) if alpha_map else 0.45

    # Strukturregel: Mittag/Nachmittag darf den Morgenpeak nicht überholen.
    # Bins: Morgen = 06/09, Mittag/Nachmittag = 12/15/18
    morning_bins = [6, 9]
    noon_bins = [12, 15, 18]
    morning_vals = [alpha_map[b] for b in morning_bins if b in alpha_map]
    if morning_vals:
        morning_peak = float(np.max(morning_vals))
        noon_cap = morning_peak * MITTAG_VS_MORGEN_MAX_RATIO
        for b in noon_bins:
            if b in alpha_map:
                alpha_map[b] = min(float(alpha_map[b]), noon_cap)
    # Gestern: absoluter 3h-Bin-Mittelwert je Bin (für heute: Mischung Richtung „morgen“)
    bin_preis_gestern = {
        int(r["bin3"]): float(r["preis"]) for _, r in df_g_bin.iterrows()
    }
    fallback_bin_y = float(df_g_bin["preis"].median())

    df_today = df_hist_all[df_hist_all["stunde"].dt.normalize() == heute_norm].copy()
    if not df_today.empty:
        today_max_obs = float(df_today["preis"].max())
    else:
        today_max_obs = float(letzter_preis)

    k0 = float(kern_preis)
    m0 = float(today_max_obs)
    if k0 > m0 + 1e-4:
        k0 = min(k0, m0 - 0.005)

    # Kurz nach Mitternacht / wenig Tagesdaten: (m0−k0) ~ 0 → horizontale Prognose.
    # Dann Spanne vom Vortag (denom) nutzen; abends mit vollem Tagesrand nicht überschreiben.
    if (m0 - k0) < 0.02 and (jetzt_ts.hour < 15 or len(df_today) < 8):
        m0 = k0 + float(denom)
    # Spanne zusätzlich robust deckeln: verhindert unplausible Peak-Ausreißer.
    if profile_span_vals:
        span_cap = float(np.quantile(profile_span_vals, 0.85)) * 1.15
        span_cap = max(0.02, min(span_cap, 0.25))
        cur_span = max(0.0, m0 - k0)
        if cur_span > span_cap:
            m0 = k0 + span_cap

    pred_delta_eur = pred_delta_cent / 100.0

    start_ts = jetzt_ts.floor("3h") + timedelta(hours=3)
    ende_exklusiv = heute_norm + pd.Timedelta(days=2)
    punkte = []
    ts = start_ts
    last_today_preis = None
    today_peak_so_far = float(letzter_preis)

    while ts < ende_exklusiv:
        wd = ts.dayofweek
        h = ts.hour
        if not ist_offen(h, wd):
            ts += timedelta(hours=3)
            continue

        bin3 = (h // 3) * 3
        alpha = alpha_map.get(bin3, default_alpha)
        alpha = float(max(-0.25, min(1.15, alpha)))
        day_offset = (ts.normalize() - heute_norm).days

        if day_offset == 0:
            # Heute: stufenweise von gestrigem Bin-Niveau zum morgigen Modell-Niveau (gleiche Uhrzeit/Bin).
            # So wirkt der Tag „jung“ nicht dauerhaft zu niedrig, sondern interpoliert Richtung morgen.
            p_y = bin_preis_gestern.get(bin3, fallback_bin_y)
            p_morgen = (k0 + pred_delta_eur) + alpha * (m0 - k0)
            # Bis ca. 18 h nach Tagesbeginn voll Richtung morgiges Modell (nicht erst um Mitternacht)
            frac = min(1.0, max(0.0, (ts - heute_norm).total_seconds() / (18 * 3600.0)))
            preis = (1.0 - frac) * p_y + frac * p_morgen
            # Harte Abendregel: ab 16:00 kein weiterer Anstieg mehr (nur seitwärts/fallend).
            if h >= 16 and (last_today_preis is not None):
                preis = min(preis, last_today_preis)
            # Typischer "Abendschluss" soll sichtbar sein: gegen Tagesende Richtung historischer Schlussabschlag.
            if h >= 18 and close_drop_frac > 0 and today_peak_so_far > 0:
                target_close = today_peak_so_far * (1.0 - close_drop_frac)
                # 18 Uhr: sanft, 21 Uhr: voll Richtung Schlussniveau
                frac_close = min(1.0, max(0.0, (h - 18) / 3.0))
                preis = (1.0 - frac_close) * preis + frac_close * min(preis, target_close)
            # Zusaetzliche harte Schliessneigung: mindestens kleiner Abschlag je 3h-Schritt ab 18:00.
            if h >= 18 and (last_today_preis is not None):
                preis = min(preis, last_today_preis - 0.003)
            last_today_preis = float(preis)
            today_peak_so_far = max(today_peak_so_far, float(preis))
        elif day_offset == 1:
            preis = (k0 + pred_delta_eur) + alpha * (m0 - k0)
        else:
            ts += timedelta(hours=3)
            continue

        preis = max(0.5, min(4.0, float(preis)))
        punkte.append({"stunde": ts, "preis": round(preis, 4)})
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
        brent_vs_3d_pct,
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
        <div class="topbar-addr">ARAL · Dürener Str. 407 · 50858 Köln · <a href="{ARAL_STATION_URL}" target="_blank" rel="noopener noreferrer">bei aral.de</a></div>
        <div class="topbar-hours">{oeff_rows}</div>
    </div>
    <div class="topbar-right">
        <span class="topbar-time">Live · {uhrzeit} Uhr</span>
        <form class="topbar-refresh-form" method="get" action="">
            <input type="hidden" name="refresh" value="1" />
            <button type="submit" class="topbar-refresh">↺ Aktualisieren</button>
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
    '<div class="section-label section-label-first">Auf einen Blick</div>',
    unsafe_allow_html=True,
)

# ── METRIKEN ──────────────────────────────────────────────────────────────────
delta_val   = letzter_preis - mean_ref
delta_cent  = delta_val * 100
delta_cls  = "delta-green" if delta_val < 0 else "delta-red"
delta_sign = "−" if delta_val < 0 else "+"
unchanged_sub = ""

if not df_live_raw.empty and {"timestamp", "preis"}.issubset(df_live_raw.columns):
    try:
        df_tmp = df_live_raw[["timestamp", "preis"]].copy()
        df_tmp["timestamp"] = pd.to_datetime(df_tmp["timestamp"], errors="coerce")
        df_tmp["preis"] = pd.to_numeric(df_tmp["preis"], errors="coerce")
        df_tmp = df_tmp.dropna(subset=["timestamp", "preis"]).sort_values("timestamp")
        if not df_tmp.empty:
            last_row = df_tmp.iloc[-1]
            if abs(float(last_row["preis"]) - float(letzter_preis)) < 0.0005:
                mins = int(max(0, (jetzt_ts - pd.Timestamp(last_row["timestamp"])).total_seconds() // 60))
                # Typische Änderungsfrequenz über Tagesverlauf (stundenbasiert) aus Historie ableiten
                hist = df_ext[["stunde", "preis"]].copy()
                hist["stunde"] = pd.to_datetime(hist["stunde"], errors="coerce")
                hist["preis"] = pd.to_numeric(hist["preis"], errors="coerce")
                hist = hist.dropna(subset=["stunde", "preis"]).sort_values("stunde")
                hist = hist[hist["stunde"] >= (jetzt_ts - pd.Timedelta(days=28))]
                hist["chg"] = hist["preis"].diff().abs() > 0.0005
                events = hist[hist["chg"]].copy()
                events["mins_since_prev"] = events["stunde"].diff().dt.total_seconds() / 60.0
                events["hour"] = events["stunde"].dt.hour
                cur_h = int(jetzt_ts.hour)

                # Bevorzuge gleiche Stunde, dann Nachbarstunden (+/-1), danach globale Historie.
                typ = events.loc[events["hour"] == cur_h, "mins_since_prev"].dropna()
                if len(typ) < 4:
                    nbr_hours = {((cur_h - 1) % 24), cur_h, ((cur_h + 1) % 24)}
                    typ = events.loc[events["hour"].isin(nbr_hours), "mins_since_prev"].dropna()
                if len(typ) < 6:
                    typ = events["mins_since_prev"].dropna()
                if len(typ) > 0:
                    typ_mins = float(np.clip(typ.median(), 15, 720))
                    ratio = mins / typ_mins if typ_mins > 0 else 0.0
                    if ratio < 0.7:
                        c = "#1B5E20"   # gruen: letzte Aenderung war noch relativ frisch
                    elif ratio <= 1.05:
                        c = "#EF6C00"   # orange: nahe am typischen Wechselintervall
                    else:
                        c = "#B71C1C"   # rot: typisches Intervall erreicht/ueberschritten
                    unchanged_sub = (
                        f'<div style="margin-top:4px;font-size:0.82rem;color:{c};font-weight:600;">'
                        f'Unveraendert seit {mins} Min. · typisch hier: ~{int(round(typ_mins))} Min.'
                        '</div>'
                    )
                else:
                    unchanged_sub = (
                        '<div style="margin-top:4px;font-size:0.82rem;color:#8E959F;">'
                        f'Unveraendert seit {mins} Min.'
                        '</div>'
                    )
    except Exception:
        pass

if richtung_tage == "fällt":
    tend_pfeil, tend_cls = "↓", "tendenz-down"
elif richtung_tage == "steigt":
    tend_pfeil, tend_cls = "↑", "tendenz-up"
else:
    tend_pfeil, tend_cls = "→", "tendenz-flat"

st.markdown(f"""
<div class="metric-grid">
    <div class="card">
        <div class="card-head"><div class="card-title">Ø gestern</div></div>
        <div class="card-main"><div class="card-value">{preis_fmt(mean_ref)} &euro;</div></div>
        <div class="card-foot"></div>
    </div>
    <div class="card">
        <div class="card-head"><div class="card-title">Aktueller Preis · {uhrzeit} Uhr</div></div>
        <div class="card-main"><div class="card-value">{preis_fmt(letzter_preis)} &euro;</div></div>
        <div class="card-foot"><span class="{delta_cls}">{delta_sign} {abs(delta_cent):.1f} ct vs. Ø gestern</span>{unchanged_sub}</div>
    </div>
    <div class="card card--model-direction">
        <div class="card-head"><div class="card-title">Tagesmodell · Kernpreis-Richtung</div></div>
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
    <div class="ki-footer">
        Text mit Claude erzeugt · <a href="https://www.anthropic.com" target="_blank" rel="noopener noreferrer">Anthropic</a>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# ── STANDORT (Karte) — nach Kernkarten, vor Detail-Tabs ──────────────────────
st.markdown(
    '<div class="section-label section-label-tight-top">Standort</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="osm-map-title">ARAL Dürener Str. 407 · 50858 Köln · <a href="{ARAL_STATION_URL}" target="_blank" rel="noopener noreferrer">bei aral.de</a></div>',
    unsafe_allow_html=True,
)
osm_standort_embed(STATION_LAT, STATION_LON)

TAB_LABELS = ["Preisverlauf", "KPIs", "Modell-Performance", "EDA-Insights"]

tab_pv, tab_kpi, tab_perf, tab_eda = st.tabs(TAB_LABELS)

# ─── TAB 1: Preisverlauf ─────────────────────────────────────────────────────
with tab_pv:
    st.markdown('<div class="section-label">Preisverlauf — 7 Tage + Prognose bis morgen</div>',
                unsafe_allow_html=True)
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
                    mode="lines", name="Tages-Ø",
                    line=dict(color="#1565C0", width=2.5),
                    connectgaps=False,
                ))

    # Prognose-Linie (3h-Bins, bis Mitternacht nach „morgen“)
    if not df_prognose_bin.empty:
        # Verbindungspunkt: aktueller Preis am rechten Rand des aktuellen 3h-Bins
        df_prog_future = df_prognose_bin[df_prognose_bin["stunde"] >= aktueller_bin_ende].copy()
        df_prog_plot = pd.concat([
            pd.DataFrame([{"stunde": aktueller_bin_ende, "preis": letzter_preis}]),
            df_prog_future
        ]).reset_index(drop=True)
        fig.add_trace(go.Scatter(
            x=df_prog_plot["stunde"], y=df_prog_plot["preis"],
            mode="lines", name="Prognose",
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
    prognose_ende_mitternacht = jetzt_ts.normalize() + pd.Timedelta(days=2)
    while tag <= prognose_ende_mitternacht:
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

with tab_kpi:
    st.markdown('<div class="section-label">Analyse — letzte 14 Tage (ohne heute)</div>',
                unsafe_allow_html=True)

    heute_datum = jetzt_ts.normalize().date()
    tag_letzter = heute_datum - timedelta(days=1)
    # Letzte 14 Kalendertage bis einschließlich gestern (14 verschiedene Daten)
    tag_end_ts = pd.Timestamp(tag_letzter).normalize()
    cutoff_kpi = tag_end_ts - pd.Timedelta(days=13)
    cutoff_14d = cutoff_kpi

    # Nur vollständige Tage (heute ausgeschlossen)
    df_14 = df_hist[
        (df_hist["stunde"] >= cutoff_14d) &
        (df_hist["stunde"].dt.date < heute_datum)
    ].copy().sort_values("stunde")
    df_14["tag"] = df_14["stunde"].dt.date
    # Delta nur innerhalb eines Kalendertags (sonst verbindet diff() den letzten Wert vom Vortag)
    df_14["delta"] = df_14.groupby("tag", group_keys=False)["preis"].diff()
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
    df_tag["tag"] = pd.to_datetime(df_tag["tag"]).dt.normalize()
    df_tag = df_tag[df_tag["tag"] >= cutoff_kpi].copy()
    # Fehlende Kalendertage im KPI-Fenster auffüllen (sonst fallen Tage ohne Messpunkte/Änderungen weg)
    alle_kpi_tage = pd.date_range(cutoff_kpi, tag_end_ts, freq="D").normalize()
    df_tag = (
        pd.DataFrame({"tag": alle_kpi_tage})
        .merge(df_tag, on="tag", how="left")
        .assign(n_aenderungen=lambda d: d["n_aenderungen"].fillna(0).astype(int))
    )

    if not df_vol.empty:
        df_vol["tag_v"] = pd.to_datetime(df_vol["tag_v"]).dt.normalize()
        df_vol = df_vol[df_vol["tag_v"] >= cutoff_kpi].copy()

    if not df_mc_delta.empty:
        df_mc_delta["tag"] = pd.to_datetime(df_mc_delta["tag"]).dt.normalize()
        df_mc_delta = df_mc_delta[df_mc_delta["tag"] >= cutoff_kpi].copy()

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
        f"Zeitraum **{cutoff_kpi.strftime('%d.%m.%Y')}** bis **{tag_end_ts.strftime('%d.%m.%Y')}** "
        "(ohne heute) — gleicher Fenster für alle drei Tagesdiagramme."
    )

    # Änderungen/Tag
    st.markdown('<div class="section-label">Änderungen pro Tag — täglich</div>',
                unsafe_allow_html=True)
    fig3 = go.Figure()
    if not df_tag.empty:
        fig3.add_trace(go.Scatter(
            x=df_tag["tag"], y=df_tag["n_aenderungen"],
            mode="lines", name="Ändg/Tag", line=dict(color="#1565C0", width=1.5),
            hovertemplate="%{x|%d.%m.%Y}<br>Anzahl: %{y}<extra></extra>",
        ))
    fig3.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False),
        xaxis=kpi_xaxis)
    st.plotly_chart(fig3, use_container_width=True)

    # Volatilität (ganzer Tag, inkl. Morning-Spike)
    st.markdown('<div class="section-label">Tägliche Preisvolatilität — ganzer Tag</div>',
                unsafe_allow_html=True)
    fig6_kpi = go.Figure()
    if not df_vol.empty:
        fig6_kpi.add_trace(go.Scatter(
            x=df_vol["tag_v"], y=df_vol["preis"] * 100,
            mode="lines", name="Volatilität",
            line=dict(color="#E65100", width=1.5),
            fill="tozeroy", fillcolor="rgba(230,81,0,0.08)",
            hovertemplate="%{x|%d.%m.%Y}<br>σ: %{y:.1f} ct<extra></extra>",
        ))
    fig6_kpi.update_layout(**BASE_L, height=200,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"),
        xaxis=kpi_xaxis)
    st.plotly_chart(fig6_kpi, use_container_width=True)

    # Morning-Spike vs. Closing Abstand (heute ausgeschlossen)
    st.markdown('<div class="section-label">Abstand Morning-Spike − Closing — täglich</div>',
                unsafe_allow_html=True)
    fig4 = go.Figure()
    if not df_mc_delta.empty:
        fig4.add_trace(go.Scatter(
            x=df_mc_delta["tag"], y=df_mc_delta["abstand_ct"],
            mode="lines+markers", name="Morning − Closing",
            line=dict(color="#6A1B9A", width=1.5), marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(106,27,154,0.08)",
            hovertemplate="%{x|%d.%m.%Y}<br>Abstand: %{y:.1f} ct<extra></extra>",
        ))
    fig4.update_layout(**BASE_L, height=220,
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct", rangemode="tozero"),
        xaxis=kpi_xaxis)
    st.plotly_chart(fig4, use_container_width=True)

with tab_perf:
    st.markdown('<div class="section-label">Retrograde Bewertung — Tages-Prognose</div>',
                unsafe_allow_html=True)
    st.caption("""**Zielvariable:** Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage.
Kernpreis = p10 der Stundenbins 13–20 Uhr.
**Richtung korrekt** = Predicted und Actual auf gleicher Seite der ±0.5ct Schwelle.
**MAE** = durchschnittliche Abweichung Predicted vs. Actual in Cent.""")

    if df_prog_log.empty:
        st.info("Noch keine Log-Daten verfügbar.")
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
        df_log_14 = df_pl[df_pl["_tag"] >= min_14].copy().sort_values("datum")

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

        # Prognose-Trefferquote (Kalender): 4 Mo–So-Wochen; farbige Kacheln nur bei Log-Zeile (bis gestern)
        montag_4w_start = start_laufende_woche - pd.Timedelta(weeks=3)
        sonntag_woche_aktuell = start_laufende_woche + pd.Timedelta(days=6)
        st.markdown(
            '<div class="section-label">Prognose-Trefferquote — letzte 4 Kalenderwochen (inkl. laufende Woche)</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Grün = Richtung korrekt · Rot = falsch · P = predicted Δ · A = actual Δ · Schwelle: ±0.5 ct "
            "(nur Tage mit Log-Eintrag)"
        )

        def rich_pfeil(delta_ct):
            if delta_ct > 0.5:
                return "↑"
            if delta_ct < -0.5:
                return "↓"
            return "→"

        fd = pd.Timestamp(montag_4w_start).date()
        ld = pd.Timestamp(sonntag_woche_aktuell).date()
        alle_tage = [fd + timedelta(days=i) for i in range((ld - fd).days + 1)]
        log_dict = {
            r["_tag"]: r
            for _, r in df_pl[df_pl["_tag"] <= gestern_date].iterrows()
        }

        header_html = (
            '<div class="kalender-woche">'
            + "".join(
                f'<div class="kalender-header">{w}</div>'
                for w in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
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
        df_week = df_log_3w.copy()
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
            '<div class="section-label">Wöchentliche Trefferquote — 3 vollständige Kalenderwochen (Mo–So)</div>',
            unsafe_allow_html=True,
        )
        fig_week = go.Figure()
        fig_week.add_trace(go.Bar(
            x=df_plot["wochenende_so"], y=df_plot["acc_pct"],
            name="Trefferquote", marker_color="#1565C0",
            hovertemplate="%{customdata}<br>Trefferquote: %{y:.0f} %<extra></extra>",
            customdata=[
                kw_sonntag_label(ts) + (f" · {n} Tage" if n else "")
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
                '<div class="section-label">Predicted vs. Actual Delta — letzte 14 Tage (Cent)</div>',
                unsafe_allow_html=True,
            )
            # Explizit Europe/Berlin, damit Plotly die Achse nicht als UTC-Mitternacht verschiebt
            x_14 = pd.to_datetime(df_log_14["_tag"].astype(str)).dt.tz_localize(BERLIN)
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Scatter(
                x=x_14,
                y=df_log_14["predicted_delta"]*100,
                mode="lines+markers", name="Predicted",
                line=dict(color="#1565C0", width=2), marker=dict(size=5),
                hovertemplate="%{x|%d.%m.%Y}<br>Predicted: %{y:.1f} ct<extra></extra>",
            ))
            fig_perf.add_trace(go.Scatter(
                x=x_14,
                y=df_log_14["actual_delta"]*100,
                mode="lines+markers", name="Actual",
                line=dict(color="#E65100", width=2), marker=dict(size=5),
                hovertemplate="%{x|%d.%m.%Y}<br>Actual: %{y:.1f} ct<extra></extra>",
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
            st.caption("Grauer Bereich = ±0.5 ct Stabilitätsschwelle")

# ─── TAB 4: EDA-Insights ────────────────────────────────────────────────────
with tab_eda:
    st.markdown(
        '<div class="section-label">EDA-Insights — Explorative Analyse</div>',
        unsafe_allow_html=True,
    )

    df_eda = df_hist_all.copy()
    if df_eda.empty:
        st.info("Keine EDA-Daten verfuegbar.")
    else:
        df_eda["tag"] = df_eda["stunde"].dt.normalize()
        df_eda["stunde_h"] = df_eda["stunde"].dt.hour
        df_eda["wochentag"] = df_eda["stunde"].dt.day_name()
        weekday_order = [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ]
        weekday_label = {
            "Monday": "Mo", "Tuesday": "Di", "Wednesday": "Mi", "Thursday": "Do",
            "Friday": "Fr", "Saturday": "Sa", "Sunday": "So"
        }
        df_eda["wochentag"] = pd.Categorical(df_eda["wochentag"], categories=weekday_order, ordered=True)

        window_days = st.slider("EDA-Zeitraum (Tage)", min_value=14, max_value=180, value=60, step=7)
        cutoff_eda = jetzt_ts.normalize() - pd.Timedelta(days=window_days)
        df_eda = df_eda[df_eda["stunde"] >= cutoff_eda].copy()
        if df_eda.empty:
            st.warning("Keine Daten im gewaehlten EDA-Zeitraum.")
            st.stop()

        mean_7d = float(df_eda["preis"].mean())
        min_h = int(df_eda.groupby("stunde_h")["preis"].mean().idxmin())
        max_h = int(df_eda.groupby("stunde_h")["preis"].mean().idxmax())
        vol_ct = float(df_eda["preis"].std() * 100.0)

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin-bottom:1rem">
            <div class="kpi-card"><div class="kpi-val">{mean_7d:.3f}<span style="font-size:0.75rem"> €</span></div><div class="kpi-lbl">Ø Preis ({window_days} Tage)</div></div>
            <div class="kpi-card"><div class="kpi-val">{min_h:02d}:00</div><div class="kpi-lbl">Guenstigste Stunde</div></div>
            <div class="kpi-card"><div class="kpi-val">{max_h:02d}:00</div><div class="kpi-lbl">Teuerste Stunde</div></div>
            <div class="kpi-card"><div class="kpi-val">{vol_ct:.1f}<span style="font-size:0.75rem"> ct</span></div><div class="kpi-lbl">Volatilitaet (Stdabw.)</div></div>
        </div>
        """, unsafe_allow_html=True)

        sub_t1, sub_t2, sub_t3 = st.tabs(["Zeitmuster", "Verteilung", "Wochenvergleich"])

        with sub_t1:
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Durchschnittspreis nach Stunde")
                df_hour = df_eda.groupby("stunde_h", observed=False)["preis"].mean().reset_index()
                fig_hour = go.Figure()
                fig_hour.add_trace(go.Scatter(
                    x=df_hour["stunde_h"], y=df_hour["preis"],
                    mode="lines", line=dict(color="#1565C0", width=2),
                    hovertemplate="Stunde %{x}:00<br>Preis %{y:.3f} €<extra></extra>",
                    name="Preis",
                ))
                fig_hour.update_layout(
                    height=300, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(gridcolor="#F5F5F5"),
                    yaxis=dict(gridcolor="#F5F5F5", tickformat=".3f"),
                    showlegend=False,
                )
                st.plotly_chart(fig_hour, use_container_width=True)

            with col_b:
                st.caption("Tagesmittel (Trend)")
                df_day = df_eda.groupby("tag", observed=False)["preis"].mean().reset_index()
                fig_day = go.Figure()
                fig_day.add_trace(go.Scatter(
                    x=df_day["tag"], y=df_day["preis"],
                    mode="lines", line=dict(color="#E65100", width=2),
                    hovertemplate="%{x|%d.%m.%Y}<br>Preis %{y:.3f} €<extra></extra>",
                    name="Tages-Ø",
                ))
                fig_day.update_layout(
                    height=300, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(gridcolor="#F5F5F5"),
                    yaxis=dict(gridcolor="#F5F5F5", tickformat=".3f"),
                    showlegend=False,
                )
                st.plotly_chart(fig_day, use_container_width=True)

        with sub_t2:
            col_c, col_d = st.columns(2)
            with col_c:
                st.caption("Preisverteilung pro Stunde (Boxplot)")
                fig_box = go.Figure()
                for h in sorted(df_eda["stunde_h"].dropna().unique()):
                    vals = df_eda.loc[df_eda["stunde_h"] == h, "preis"]
                    fig_box.add_trace(go.Box(
                        y=vals,
                        name=f"{int(h):02d}",
                        boxpoints=False,
                        marker_color="#1565C0",
                        line=dict(width=1),
                        showlegend=False,
                    ))
                fig_box.update_layout(
                    height=320, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(title="Stunde", gridcolor="#F5F5F5"),
                    yaxis=dict(title="Preis", gridcolor="#F5F5F5", tickformat=".3f"),
                )
                st.plotly_chart(fig_box, use_container_width=True)

            with col_d:
                st.caption("Histogramm (Preisverteilung)")
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(
                    x=df_eda["preis"], nbinsx=40, marker_color="#E65100", opacity=0.85
                ))
                fig_hist.update_layout(
                    height=320, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(title="Preis", gridcolor="#F5F5F5", tickformat=".3f"),
                    yaxis=dict(title="Anzahl", gridcolor="#F5F5F5"),
                    bargap=0.03,
                )
                st.plotly_chart(fig_hist, use_container_width=True)

        with sub_t3:
            col_e, col_f = st.columns(2)
            with col_e:
                st.caption("Durchschnitt nach Wochentag")
                df_wd = df_eda.groupby("wochentag", observed=False)["preis"].mean().reset_index()
                df_wd["wd_short"] = df_wd["wochentag"].map(weekday_label)
                fig_wd = go.Figure()
                fig_wd.add_trace(go.Bar(
                    x=df_wd["wd_short"], y=df_wd["preis"], marker_color="#1565C0"
                ))
                fig_wd.update_layout(
                    height=300, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(title="", gridcolor="#F5F5F5"),
                    yaxis=dict(title="Preis", gridcolor="#F5F5F5", tickformat=".3f"),
                    showlegend=False,
                )
                st.plotly_chart(fig_wd, use_container_width=True)

            with col_f:
                st.caption("Heatmap: Wochentag x Stunde")
                piv = (
                    df_eda.groupby(["wochentag", "stunde_h"], observed=False)["preis"]
                    .mean()
                    .reset_index()
                    .pivot(index="wochentag", columns="stunde_h", values="preis")
                    .reindex(weekday_order)
                )
                fig_heat = go.Figure(data=go.Heatmap(
                    z=piv.values,
                    x=[int(c) for c in piv.columns],
                    y=[weekday_label.get(str(i), str(i)) for i in piv.index],
                    colorscale="Blues",
                    colorbar=dict(title="Preis"),
                    hovertemplate="Tag %{y}<br>Stunde %{x}:00<br>Preis %{z:.3f} €<extra></extra>",
                ))
                fig_heat.update_layout(
                    height=300, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(title="Stunde", gridcolor="#F5F5F5"),
                    yaxis=dict(title="", gridcolor="#F5F5F5"),
                )
                st.plotly_chart(fig_heat, use_container_width=True)

# ── Social & Methodik (nach Tabs, vor Footer) ───────────────────────────────
st.markdown(f"""
<div class="social-info-wrap">
  <div class="social-row-links">
    <div class="social-strip">
      <a href="https://github.com/felixschrader/spritpreisprognose" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_GH}</span> GitHub
      </a>
      <span class="social-strip-sep">·</span>
      <a href="https://www.linkedin.com/in/felixschrader/" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> Felix Schrader
      </a>
      <span class="social-strip-sep">·</span>
      <a href="https://www.linkedin.com/in/girandoux-fandio-08628bb9/" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> Girandoux Fandio Nganwajop
      </a>
      <span class="social-strip-sep">·</span>
      <a href="https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo" target="_blank" rel="noopener noreferrer">
        <span class="social-ico">{_SVG_IN}</span> Ghislain Wamo
      </a>
    </div>
  </div>
  <div class="social-row-meta">
    <details class="header-details" id="meth-dash">
      <summary>Methodik & Projekt</summary>
      <div class="header-details-body">
        <p>Modell: Random Forest Regressor (scikit-learn)
        · Zielvariable: Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage
        · Richtungs-Accuracy Test-Set: 67.9% · Baseline: 38.6%
        · Schwelle &quot;stabil&quot;: ±0.5 Cent · Trainingsperiode: 2019–2023</p>
        <p><strong>Prognose &amp; Übersicht:</strong>
        Das Modell nutzt den <strong>letzten abgeschlossenen Kerntag</strong> (in der Regel <strong>gestern</strong>). Die Pfeil-Richtung gilt für die <strong>Kernpreis-Ebene</strong> (gleitender 3-Tage-Kernpreis im Training), nicht für den Spot-Cent gegenüber „jetzt“.
        Die <strong>orange Linie</strong> im Chart setzt die Modell-<strong>Richtung</strong> für den <strong>nächsten Öffnungstag</strong> so um, dass pro Uhrzeit-Bin der Abstand zwischen <strong>Kernpreis (P10, 13–20 Uhr)</strong> und <strong>Tageshoch</strong> wie gestern skaliert wird — nicht über das Min/Max der 3h-Bins.</p>
        <p><strong>Daten-Updates (GitHub Actions):</strong>
        Die <strong>Kurzprognose</strong> wird <strong>stündlich</strong> erzeugt.
        Die <strong>Tagesprognose</strong> (Modellrichtung, orange Linie) wird <strong>einmal täglich</strong> um <strong>09:00&nbsp;UTC</strong> gebaut (z.&nbsp;B. <strong>10:00&nbsp;Uhr MEZ</strong>); dazwischen gibt es dafür oft <strong>keinen neuen Stand</strong> auf GitHub.
        <strong>„Aktualisieren“</strong> im Dashboard leert nur den App-Cache. Wenn die Tageswerte „hängen“, die Action im Repo unter <em>Actions → Run workflow</em> manuell starten oder auf den nächsten Lauf warten.</p>
        <p><strong>Technik:</strong>
        ML-Stack: scikit-learn (Random Forest wie im ersten Absatz). Daten: Tankerkönig / MTS-K; tägliche Pipeline über GitHub Actions; Dashboard auf Streamlit Community Cloud; Standortkarte mit OpenStreetMap (Leaflet). Weitere technische Details und Repo-Aufbau: <a href="https://github.com/felixschrader/spritpreisprognose" target="_blank" rel="noopener noreferrer">README im GitHub-Repository</a>.</p>
        <p><strong>KI bei der Entwicklung:</strong>
        <a href="https://cursor.com" target="_blank" rel="noopener noreferrer">Cursor</a> (Editor) und <a href="https://www.anthropic.com/claude-code" target="_blank" rel="noopener noreferrer">Claude Code</a> wurden unterstützend genutzt — z.&nbsp;B. für Code-Entwurf, Refactoring und Erklärungen im Projekt. Fachliche Entscheidungen, Tests und die Verantwortung für das Ergebnis liegen beim Team.</p>
        <p><strong>KI-Text:</strong> der Kurztext darüber wird mit <a href="https://www.anthropic.com" target="_blank" rel="noopener noreferrer">Claude</a> aus Preis, Mittelwert gestern, Modellrichtung und Brent-Referenz formuliert (Brent als Marktbegriff, ohne Regionalvergleich).</p>
        <p>Dieses Projekt entstand im Rahmen der sechsmonatigen Weiterbildung Data Science; die Abschlussarbeit wurde in der Zeit vom 16. bis 27. März 2026 erstellt.
        Es wendet erlernte Tools und Denkweisen bewusst in der Praxis an.
        Das Dashboard ist ein MVP im Sinne eines Prototyps und offen für eine Weiterentwicklung, die weitere Zusammenhänge in der Preisfindung von Kraftstoffpreisen einbeziehen kann.</p>
      </div>
    </details>
  </div>
</div>
""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer-wrap">
  <div class="footer-mini">
    Preisinformationen:
    <a href="https://tankerkoenig.de" target="_blank" rel="noopener noreferrer">Tankerkönig</a>
    · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>
    · Quelle: MTS-K (Markttransparenzstelle für Kraftstoffe)<br>
    <a href="https://data-science-institute.de/" target="_blank" rel="noopener noreferrer">DSI — Data Science Institute by Fabian Rappert</a>
    · Capstone Projekt 2026
  </div>
</div>
""", unsafe_allow_html=True)