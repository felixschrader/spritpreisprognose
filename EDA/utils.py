import streamlit as st

def sidebar_filter(df):

    st.sidebar.title("Filter")

    # Kraftstoff
    fuel = st.sidebar.selectbox(
        "Kraftstoff",
        ["diesel","e5","e10"]
    )

    # Marke
    brand = st.sidebar.multiselect(
        "Marke",
        df["brand"].dropna().unique()
    )

    # Tankstelle
    station = st.sidebar.multiselect(
        "Tankstelle",
        df["station_name"].dropna().unique()
    )

    # Zeitraum
    start = st.sidebar.date_input(
        "Startdatum",
        df["timestamp"].min()
    )

    end = st.sidebar.date_input(
        "Enddatum",
        df["timestamp"].max()
    )

    df = df[
        (df["timestamp"] >= str(start)) &
        (df["timestamp"] <= str(end))
    ]

    if brand:
        df = df[df["brand"].isin(brand)]

    if station:
        df = df[df["station_name"].isin(station)]

    df["preis"] = df[f"preis_{fuel}"]

    return df