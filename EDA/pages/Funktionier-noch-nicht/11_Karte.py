import streamlit as st
import pydeck as pdk

df = st.session_state["data"]

st.title("Prognose von Benzinpreisen")

st.header("Tankstellen Karte")

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=pdk.ViewState(
        latitude=df["station_latitude"].mean(),
        longitude=df["station_longitude"].mean(),
        zoom=10
    ),
    layers=[
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position='[station_longitude, station_latitude]',
            get_radius=200,
            get_fill_color='[200, 30, 0, 160]'
        )
    ],
))

st.caption("Geografische Lage der Tankstellen")