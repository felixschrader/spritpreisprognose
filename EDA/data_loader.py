import pandas as pd
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_CANDIDATES = [
    BASE_DIR / "ml_master_dataset.parquet",
    BASE_DIR.parent / "ml_master_dataset.parquet",
]
LOAD_COLUMNS = [
    "timestamp",
    "brand",
    "station_name",
    "preis_diesel",
    "preis_e5",
    "preis_e10",
    "monat",
    "stunde",
    "tageszeit",
    "ist_wochenende",
    "sonnenstunden",
    "schulferien_name",
    "brent_futures_usd",
    "temp_avg",
    "niederschlag_mm",
    "co2_preis_eur_t",
    "eur_usd",
    "distanz_km",
]
OPTIONAL_CATEGORY_COLUMNS = ["brand", "station_name", "tageszeit", "schulferien_name"]

@st.cache_data(ttl=3600, max_entries=1)
def load_data():
    data_path = next((p for p in DATA_CANDIDATES if p.exists()), None)
    if data_path is None:
        candidate_text = "\n".join(f"- `{p}`" for p in DATA_CANDIDATES)
        st.error(
            "Datendatei `ml_master_dataset.parquet` wurde nicht gefunden.\n\n"
            "Gepruefte Pfade:\n"
            f"{candidate_text}"
        )
        st.stop()

    try:
        df = pd.read_parquet(data_path, columns=LOAD_COLUMNS)
    except Exception:
        # Fallback for schema drifts: load full file if selected columns are unavailable.
        df = pd.read_parquet(data_path)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in OPTIONAL_CATEGORY_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")
    for col in df.select_dtypes(include=["float64"]).columns:
        if col != "timestamp":
            df[col] = df[col].astype("float32")

    return df