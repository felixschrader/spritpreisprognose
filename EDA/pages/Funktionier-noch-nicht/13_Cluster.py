import streamlit as st
from sklearn.cluster import KMeans
import plotly.express as px

df = st.session_state["data"]

st.title("Prognose von Benzinpreisen")

st.header("Cluster Analyse Tankstellen")

cluster_df = df.groupby("station_name")["preis"].mean().reset_index()

kmeans = KMeans(n_clusters=3)
cluster_df["cluster"] = kmeans.fit_predict(
    cluster_df[["preis"]]
)

fig = px.scatter(
    cluster_df,
    x="station_name",
    y="preis",
    color="cluster"
)

st.plotly_chart(fig)

st.caption("Cluster günstige vs teure Tankstellen")