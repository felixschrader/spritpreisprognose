# Seite 5 — Beste Tankzeit
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("🏆 Wann tanke ich am besten und wo?")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Beste Stunde", df.groupby("stunde")["preis"].mean().idxmin())
col2.metric("Beste Tankstelle", df.groupby("station_name")["preis"].mean().idxmin())
col3.metric("Ø Preis", round(df["preis"].mean(),3))
col4.metric("Tankstellen", df["station_name"].nunique())

col1, col2 = st.columns(2)

with col1:
    fig = px.line(df.groupby("stunde")["preis"].mean().reset_index(),
                  x="stunde", y="preis")
    st.plotly_chart(fig)
    st.caption("Beste Uhrzeit")

with col2:
    fig2 = px.bar(df.groupby("station_name")["preis"].mean().reset_index(),
                  x="station_name", y="preis")
    st.plotly_chart(fig2)
    st.caption("Beste Tankstelle")