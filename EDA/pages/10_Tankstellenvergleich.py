# Seite 10 — Tankstellenvergleich
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("📍 Tankstellenvergleich im Umkreis von 5 km")

near = df[df["distanz_km"] <= 5]

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tankstellen", near["station_name"].nunique())
col2.metric("Günstigste", near.groupby("station_name")["preis"].mean().idxmin())
col3.metric("Ø Preis", round(near["preis"].mean(),3))
col4.metric("Radius", "5 km")

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(near.groupby("station_name")["preis"].mean().reset_index(),
                 x="station_name", y="preis")
    st.plotly_chart(fig)
    st.caption("Vergleich Tankstellen")

with col2:
    fig2 = px.box(near, x="station_name", y="preis")
    st.plotly_chart(fig2)
    st.caption("Preisverteilung")