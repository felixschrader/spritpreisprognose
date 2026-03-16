import requests
import pandas as pd
import io
import os
from datetime import datetime

def update_brent_prices():
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        oil_data = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True)
        oil_data.columns = ["DCOILBRENTEU"]
        oil_data = oil_data[oil_data["DCOILBRENTEU"] != "."]  # FRED nutzt "." für fehlende Werte
        oil_data["DCOILBRENTEU"] = oil_data["DCOILBRENTEU"].astype(float)
    except Exception as e:
        print(f"ℹ️  Fallback auf Testdaten ({e})")
        oil_data = pd.DataFrame(
            {"DCOILBRENTEU": [85.42, 86.10]},
            index=pd.date_range(start="2024-01-01", periods=2)
        )

    os.makedirs("data", exist_ok=True)
    oil_data.to_csv("data/brent_prices.csv")
    stats = {
        "last_price": float(oil_data["DCOILBRENTEU"].iloc[-1]),
        "trend": "↑" if oil_data["DCOILBRENTEU"].iloc[-1] > oil_data["DCOILBRENTEU"].iloc[-2] else "→",
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    return stats

if __name__ == "__main__":
    stats = update_brent_prices()
    print(f"Preis: {stats['last_price']} USD | Trend: {stats['trend']} | {stats['updated']}")