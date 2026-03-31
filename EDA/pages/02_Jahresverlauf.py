# Seite 2 — Jahresverlauf
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("📅 Veränderungen der Preise im Jahresverlauf")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ø Preis", round(df["preis"].mean(),3))
col2.metric("Min", round(df["preis"].min(),3))
col3.metric("Max", round(df["preis"].max(),3))
col4.metric("Monate", df["monat"].nunique())

col1, col2 = st.columns(2)

with col1:
    fig = px.line(df.groupby("monat")["preis"].mean().reset_index(),
                  x="monat", y="preis")
    st.plotly_chart(fig)
    st.caption("Durchschnittspreis pro Monat")

with col2:
    fig2 = px.box(df, x="monat", y="preis")
    st.plotly_chart(fig2)
    st.caption("Verteilung je Monat")