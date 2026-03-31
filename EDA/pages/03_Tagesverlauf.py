# Seite 3 — Tagesverlauf
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("⏰ Historische Darstellungen im Tagesverlauf")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ø Preis", round(df["preis"].mean(),3))
col2.metric("Min Stunde", df.groupby("stunde")["preis"].mean().idxmin())
col3.metric("Max Stunde", df.groupby("stunde")["preis"].mean().idxmax())
col4.metric("Stunden", df["stunde"].nunique())

col1, col2 = st.columns(2)

with col1:
    fig = px.line(df.groupby("stunde")["preis"].mean().reset_index(),
                  x="stunde", y="preis")
    st.plotly_chart(fig)
    st.caption("Preis pro Stunde")

with col2:
    fig2 = px.bar(df.groupby("tageszeit")["preis"].mean().reset_index(),
                  x="tageszeit", y="preis")
    st.plotly_chart(fig2)
    st.caption("Preis nach Tageszeit")