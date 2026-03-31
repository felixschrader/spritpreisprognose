import streamlit as st
from utils import sidebar_filter
from data_loader import load_data

#st.title("Prognose von Benzinpreisen")

st.header("Projektziel")

st.write("""
Diese Anwendung analysiert die Entwicklung von Benzinpreisen
und beantwortet folgende Kernfragen:

- Wie entwickeln sich Preise?
- Wann tanke ich am günstigsten?
- Welche Tankstelle ist optimal?
- Welche Faktoren beeinflussen Preise?
""")

st.header("Datenbasis")

st.write("Dataset: ml_master_dataset.parquet")

st.header("Bedienung")

st.write("""
Filter befinden sich in der Sidebar.
Mehrere Visualisierungen pro Seite.
Interaktive Auswahl möglich.
""")

# Daten laden
df = load_data()
# Sidebar Filter
filtered_df = sidebar_filter(df)

st.session_state["data"] = filtered_df

st.title("Prognose von Benzinpreisen")
st.write("Bitte Seite aus Navigation auswählen.")