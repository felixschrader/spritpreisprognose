import pandas as pd
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_CANDIDATES = [
    BASE_DIR / "ml_master_dataset.parquet",
    BASE_DIR.parent / "ml_master_dataset.parquet",
]

@st.cache_data
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

    df = pd.read_parquet(data_path)
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df