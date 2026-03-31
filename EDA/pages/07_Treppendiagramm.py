# Seite 7 — Treppendiagramm
import streamlit as st
import plotly.express as px

df = st.session_state["data"]

#st.title("Prognose von Benzinpreisen")

st.header("📈 Tagesverlauf als Treppendiagramm")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Min Stunde", df.groupby("stunde")["preis"].mean().idxmin())
col2.metric("Max Stunde", df.groupby("stunde")["preis"].mean().idxmax())
col3.metric("Ø Preis", round(df["preis"].mean(),3))
col4.metric("Messpunkte", len(df))

hourly = df.groupby("stunde")["preis"].mean().reset_index()

fig = px.line(hourly, x="stunde", y="preis", line_shape="hv")
st.plotly_chart(fig)
st.caption("Treppendiagramm")