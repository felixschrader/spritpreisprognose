# Seite 4 — Markenvergleich
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("⛽ Welche Marke ist günstiger?")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Marken", df["brand"].nunique())
col2.metric("Günstigste", df.groupby("brand")["preis"].mean().idxmin())
col3.metric("Teuerste", df.groupby("brand")["preis"].mean().idxmax())
col4.metric("Ø Preis", round(df["preis"].mean(),3))

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(df.groupby("brand")["preis"].mean().reset_index(),
                 x="brand", y="preis")
    st.plotly_chart(fig)
    st.caption("Durchschnittspreis je Marke")

with col2:
    fig2 = px.box(df, x="brand", y="preis")
    st.plotly_chart(fig2)
    st.caption("Preisverteilung")