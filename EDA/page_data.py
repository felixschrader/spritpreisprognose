import pandas as pd
import streamlit as st

from data_loader import load_data


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df
    needs_copy = False

    if "timestamp" in out.columns and not pd.api.types.is_datetime64_any_dtype(out["timestamp"]):
        needs_copy = True
    if "monat" not in out.columns and "timestamp" in out.columns:
        needs_copy = True
    if "stunde" not in out.columns and "timestamp" in out.columns:
        needs_copy = True
    if "tageszeit" not in out.columns and "stunde" in out.columns:
        needs_copy = True
    if "preis" not in out.columns:
        needs_copy = True

    if needs_copy:
        out = df.copy()

    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    if "monat" not in out.columns and "timestamp" in out.columns:
        out["monat"] = out["timestamp"].dt.month
    if "stunde" not in out.columns and "timestamp" in out.columns:
        out["stunde"] = out["timestamp"].dt.hour
    if "tageszeit" not in out.columns and "stunde" in out.columns:
        out["tageszeit"] = pd.cut(
            out["stunde"],
            bins=[-1, 5, 11, 17, 23],
            labels=["Nacht", "Morgen", "Mittag", "Abend"],
        ).astype(str)
    if "preis" not in out.columns:
        fuel = st.session_state.get("fuel", "diesel")
        col = f"preis_{fuel}"
        if col in out.columns:
            out["preis"] = out[col]
        elif "preis_diesel" in out.columns:
            out["preis"] = out["preis_diesel"]
    return out


def get_page_data(required_columns: set[str] | None = None) -> pd.DataFrame:
    df = st.session_state.get("data")
    if df is None:
        df = load_data()
    df = _ensure_columns(df)
    if df.empty:
        st.warning("Keine Daten fuer den aktuellen Filter verfuegbar.")
        st.stop()
    if required_columns:
        missing = required_columns.difference(df.columns)
        if missing:
            st.error(
                "Fehlende Spalten fuer diese Seite: "
                + ", ".join(sorted(missing))
            )
            st.stop()
    if st.session_state.get("data") is not df:
        st.session_state["data"] = df
    return df
