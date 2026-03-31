# -------------------------------------------------------
# Import nötige Bibliotheken
# -------------------------------------------------------
import warnings
import sys
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import joblib

# -------------------------------------------------------
# BLOCK 1: Streamlit Konfiguration
# -------------------------------------------------------

st.set_page_config(
    page_title="Prognose von Benzinpreisen",
    page_icon="⛽",
    layout="wide"
)

# -------------------------------------------------------
# BLOCK 2: Daten laden
# -------------------------------------------------------

@st.cache_data
def load_data():
    df = pd.read_parquet("ml_master_dataset.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

df = load_data()

# -------------------------------------------------------
# BLOCK 3: Titel für alle Seiten
# -------------------------------------------------------

st.header("⛽ Spritpreis Prognose ")
st.markdown("<hr style='margin:3px 0;'>", unsafe_allow_html=True)

# -------------------------------------------------------
# BLOCK 4: Sidebar Titel
# -------------------------------------------------------

st.sidebar.subheader("⛽ Fuel Analytics Platform")
st.sidebar.caption("Interactive Fuel Price Dashboard")

# -------------------------------------------------------
# BLOCK 5: Navigation
# -------------------------------------------------------

seite_0 = st.Page("pages/01_Projektbeschreibung.py", title="Dashboard", icon="🏠")
seite_1 = st.Page("pages/02_Jahresverlauf.py", title="Jahresverlauf", icon="📅")
seite_2 = st.Page("pages/03_Tagesverlauf.py", title="Tagesverlauf", icon="⏰")
seite_3 = st.Page("pages/04_Markenvergleich.py", title="Marken", icon="⛽")
seite_4 = st.Page("pages/05_Beste_Tankzeit.py", title="Beste Tankzeit", icon="🏆")
seite_5 = st.Page("pages/06_Einflussfaktoren.py", title="Einfluss", icon="🌤")
seite_6 = st.Page("pages/07_Treppendiagramm.py", title="Treppendiagramm", icon="📈")
seite_7 = st.Page("pages/08_Brent_Analyse.py", title="Brent", icon="🛢")
seite_8 = st.Page("pages/09_Zusammenhaenge.py", title="Zusammenhänge", icon="🔗")
seite_9 = st.Page("pages/10_Tankstellenvergleich.py", title="Tankstellen", icon="📍")

pg = st.navigation([
    seite_0,
    seite_1,
    seite_2,
    seite_3,
    seite_4,
    seite_5,
    seite_6,
    seite_7,
    seite_8,
    seite_9
], position="top")

st.sidebar.markdown("<hr style='margin:3px 0;'>", unsafe_allow_html=True)

# -------------------------------------------------------
# BLOCK 6: Filters
# -------------------------------------------------------

st.sidebar.subheader("Filter")

# ---------------------------
# Kraftstoff Filter
# ---------------------------

fuel = st.sidebar.selectbox(
    "Kraftstoff",
    ["diesel", "e5", "e10"]
)

# ---------------------------
# Marke Filter
# ---------------------------

brand_options = ["Alle"] + sorted(df["brand"].dropna().unique().tolist())

brand_selected = st.sidebar.multiselect(
    "Marke",
    brand_options,
    default=["Alle"]
)

if "Alle" in brand_selected:
    brand_filter = df["brand"].unique()
else:
    brand_filter = brand_selected

# ---------------------------
# Tankstelle Filter
# ---------------------------

station_options = ["Alle"] + sorted(df["station_name"].dropna().unique().tolist())

station_selected = st.sidebar.multiselect(
    "Tankstelle",
    station_options,
    default=["Alle"]
)

if "Alle" in station_selected:
    station_filter = df["station_name"].unique()
else:
    station_filter = station_selected

# ---------------------------
# Zeitraum Filter
# ---------------------------

date_range = st.sidebar.date_input(
    "Zeitraum",
    [df["timestamp"].min(), df["timestamp"].max()]
)

st.sidebar.markdown("<hr style='margin:3px 0;'>", unsafe_allow_html=True)

# -------------------------------------------------------
# BLOCK 7: Daten filtern
# -------------------------------------------------------

filtered_df = df[
    (df["brand"].isin(brand_filter)) &
    (df["station_name"].isin(station_filter)) &
    (df["timestamp"].between(
        pd.to_datetime(date_range[0]),
        pd.to_datetime(date_range[1])
    ))
]

# Kraftstoff Preis setzen
filtered_df["preis"] = filtered_df[f"preis_{fuel}"]

# -------------------------------------------------------
# BLOCK 8: Session State
# -------------------------------------------------------

st.session_state["data"] = filtered_df

# -------------------------------------------------------
# BLOCK 9: Seite starten
# -------------------------------------------------------

pg.run()
























# Hauptdatei Streamlit App
# import streamlit as st
# from data_loader import load_data
# from utils import sidebar_filter
# import os

# st.set_page_config(
#     page_title="Prognose von Benzinpreisen",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # CSS laden
# with open("style.css") as f:
#     st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# # Logo
# #st.sidebar.image("assets/logo.png", width=180)

# # Daten laden
# df = load_data()

# # Sidebar Filter
# filtered_df = sidebar_filter(df)

# st.session_state["data"] = filtered_df

# st.title("Prognose von Benzinpreisen")
# st.write("Bitte Seite aus Navigation auswählen.")