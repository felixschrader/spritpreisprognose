

import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    df = pd.read_parquet("ml_master_dataset.parquet")
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df