import requests
import pandas as pd
import io
import os
from datetime import datetime
import plotly.express as px
import pytz

berlin = pytz.timezone("Europe/Berlin")

def update_eur_usd():
    try:
        url = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()
        df.columns = ["date", "EUR_USD"]
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df = df.dropna(subset=["EUR_USD"])
    except Exception as e:
        print(f"ℹ️  Fallback auf Testdaten ({e})")
        df = pd.DataFrame({
            "date": pd.date_range(start="2024-01-01", periods=2),
            "EUR_USD": [1.085, 1.090]
        })

    os.makedirs("features", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    df.to_csv("features/eur_usd_rate.csv", index=False)

    fig = px.line(df, x="date", y="EUR_USD", title="EUR/USD Wechselkurs (EZB)")
    fig.write_html("plots/eur_usd_rate.html")

    stats = {
        "last_rate": float(df["EUR_USD"].iloc[-1]),
        "trend": "↑" if df["EUR_USD"].iloc[-1] > df["EUR_USD"].iloc[-2] else "→",
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M")
    }

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_rate={stats['last_rate']}\n")
            f.write(f"trend={stats['trend']}\n")
            f.write(f"updated={stats['updated']}\n")

    return stats


if __name__ == "__main__":
    stats = update_eur_usd()
    print(f"Kurs: {stats['last_rate']} EUR/USD | Trend: {stats['trend']} | {stats['updated']}")