import streamlit as st

st.title("Prognose von Benzinpreisen")

st.header("ML Übersicht")

st.write("""
Geeignete Modelle:

- Prophet (Zeitreihe)
- Random Forest
- XGBoost
- LSTM
- SARIMA

Features:

- Zeit
- Brent
- Wetter
- Feiertage
- CO2 Preis

Ziel:

Preisvorhersage nächste Stunden
""")