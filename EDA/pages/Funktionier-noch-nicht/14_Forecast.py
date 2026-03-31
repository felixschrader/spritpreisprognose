import streamlit as st
from prophet import Prophet
import plotly.express as px

df = st.session_state["data"]

st.title("Prognose von Benzinpreisen")

st.header("Forecast mit Prophet")

data = df[["timestamp","preis"]].rename(
    columns={"timestamp":"ds","preis":"y"}
)

model = Prophet()
model.fit(data)

future = model.make_future_dataframe(periods=48, freq="H")
forecast = model.predict(future)

fig = px.line(
    forecast,
    x="ds",
    y="yhat",
    title="Preisvorhersage"
)

st.plotly_chart(fig)

st.caption("Forecast basierend auf historischen Daten")