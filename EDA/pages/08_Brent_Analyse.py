# Seite 8 — Brent Analyse
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("🛢 Brent Preis Analyse")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Brent Ø", round(df["brent_futures_usd"].mean(),2))
col2.metric("Brent Max", round(df["brent_futures_usd"].max(),2))
col3.metric("Brent Min", round(df["brent_futures_usd"].min(),2))
col4.metric("Korrelation", round(df["preis"].corr(df["brent_futures_usd"]),2))

col1, col2 = st.columns(2)

with col1:
    fig = px.line(df, x="timestamp", y="brent_futures_usd")
    st.plotly_chart(fig)
    st.caption("Brent Verlauf")

with col2:
    fig2 = px.scatter(df, x="brent_futures_usd", y="preis")
    st.plotly_chart(fig2)
    st.caption("Brent vs Preis")