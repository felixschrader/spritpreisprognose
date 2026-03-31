# Seite 9 — Zusammenhänge
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("🔗 Preisveränderung & Beziehungen")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temp Corr", round(df["preis"].corr(df["temp_avg"]),2))
col2.metric("Regen Corr", round(df["preis"].corr(df["niederschlag_mm"]),2))
col3.metric("CO2 Corr", round(df["preis"].corr(df["co2_preis_eur_t"]),2))
col4.metric("EUR/USD Corr", round(df["preis"].corr(df["eur_usd"]),2))

col1, col2 = st.columns(2)

with col1:
    fig = px.scatter(df, x="temp_avg", y="preis")
    st.plotly_chart(fig)
    st.caption("Temperatur")

with col2:
    fig2 = px.scatter(df, x="niederschlag_mm", y="preis")
    st.plotly_chart(fig2)
    st.caption("Regen")