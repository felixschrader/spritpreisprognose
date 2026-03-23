# =============================================================================
# brent_price.py
# Lädt Brent-Rohölpreise (Futures) von Yahoo Finance und speichert sie als CSV.
#
# Quelle: Yahoo Finance — Brent Crude Oil Last Day Financial Futures (BZ=F)
# Börse:  NY Mercantile (NYMEX), cash-settled (Abrechnung in Cash, kein echtes Öl)
# Einheit: USD/Barrel
#
# Zwei Datensätze:
#   - Tagesdaten:  historisch seit 2014-01-01, unbegrenzt verfügbar
#   - Intraday:    stündlich, maximal letzte 60 Tage (Yahoo Finance Limit)
#
# Warum Futures statt Spot-Preis?
#   Futures sind tagesaktuell und enthalten bereits Markterwartungen.
#   Tankstellen orientieren sich an Markterwartungen, nicht am gestrigen Spot.
#   Offizielle Spot-Daten (EIA, FRED) haben außerdem oft 1 Woche Verzögerung.
# =============================================================================

import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import pytz


# =============================================================================
# Konfiguration
# =============================================================================

CSV_DAILY    = "data/brent_futures_daily.csv"
CSV_INTRADAY = "data/brent_futures_intraday_1h.csv"
HISTORY_START = "2014-01-01"


# =============================================================================
# 1) TAGESDATEN
# =============================================================================

def fetch_daily(start: str) -> pd.DataFrame:
    """
    Holt tägliche Schlusskurse (Close) von Yahoo Finance ab einem bestimmten Datum.
    Gibt einen DataFrame zurück: Datum als Index, Preis als Spalte.
    """
    ticker = yf.Ticker("BZ=F")
    raw = ticker.history(start=start, interval="1d", auto_adjust=True)

    if raw.empty:
        raise ValueError("yfinance hat keine Tagesdaten zurückgegeben.")

    df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "period"
    df = df.rename(columns={"Close": "brent_futures_usd"})
    df = df.dropna()

    return df


def update_daily() -> dict:
    """
    Aktualisiert die Tages-CSV — hängt nur neue Daten an, überschreibt nichts.

    Logik:
    - CSV existiert bereits → nur ab letztem Datenpunkt nachladen (append)
    - CSV existiert noch nicht → kompletter Download seit HISTORY_START
    """
    os.makedirs("data", exist_ok=True)

    if os.path.exists(CSV_DAILY):
        df_existing = pd.read_csv(CSV_DAILY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]
        fetch_start = last_ts.strftime("%Y-%m-%d")
    else:
        df_existing = None
        fetch_start = HISTORY_START

    try:
        df_new = fetch_daily(start=fetch_start)
    except Exception as e:
        print(f"❌ yfinance täglich fehlgeschlagen: {e}")
        return {}

    if df_existing is not None:
        df_append = df_new[df_new.index > df_existing.index[-1]]

        if df_append.empty:
            print("ℹ️  Tagesdaten: keine neuen Daten.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            print(f"✅ yfinance täglich (BZ=F): {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        df = df_new
        print(f"✅ yfinance täglich (BZ=F): {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    df.to_csv(CSV_DAILY)
    print(f"📄 CSV gespeichert: {CSV_DAILY}")

    last = float(df["brent_futures_usd"].iloc[-1])
    # FIX: Längencheck vor iloc[-2] — schlägt sonst fehl wenn nur 1 Zeile vorhanden
    prev = float(df["brent_futures_usd"].iloc[-2]) if len(df) > 1 else last
    trend = "↑" if last > prev else ("↓" if last < prev else "→")
    berlin = pytz.timezone("Europe/Berlin")

    return {
        "last_price": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }


# =============================================================================
# 2) INTRADAY (stündlich)
# =============================================================================

def fetch_intraday() -> pd.DataFrame:
    """
    Holt stündliche Schlusskurse der letzten 60 Tage von Yahoo Finance.
    60 Tage ist das Maximum das Yahoo Finance für stündliche Daten erlaubt.
    """
    ticker = yf.Ticker("BZ=F")
    raw = ticker.history(period="60d", interval="1h", auto_adjust=True)

    if raw.empty:
        raise ValueError("yfinance hat keine Intraday-Daten zurückgegeben.")

    df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "period"
    df = df.rename(columns={"Close": "brent_futures_usd_1h"})
    df = df.dropna()

    return df


def update_intraday() -> dict:
    """
    Aktualisiert die Intraday-CSV — hängt nur neue Stunden an, überschreibt nichts.
    """
    os.makedirs("data", exist_ok=True)

    try:
        df_new = fetch_intraday()
    except Exception as e:
        print(f"❌ yfinance stündlich fehlgeschlagen: {e}")
        return {}

    if os.path.exists(CSV_INTRADAY):
        df_existing = pd.read_csv(CSV_INTRADAY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]
        df_append = df_new[df_new.index > last_ts]

        if df_append.empty:
            print("ℹ️  Intraday: keine neuen Daten.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            print(f"✅ yfinance stündlich (BZ=F): {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        df = df_new
        print(f"✅ yfinance stündlich (BZ=F): {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    df.to_csv(CSV_INTRADAY)
    print(f"📄 CSV gespeichert: {CSV_INTRADAY}")

    last = float(df["brent_futures_usd_1h"].iloc[-1])
    # FIX: Längencheck vor iloc[-2]
    prev = float(df["brent_futures_usd_1h"].iloc[-2]) if len(df) > 1 else last
    trend = "↑" if last > prev else ("↓" if last < prev else "→")
    berlin = pytz.timezone("Europe/Berlin")

    return {
        "last_price": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y %H:%M"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("─── Tagesdaten (yfinance BZ=F) ───")
    stats_daily = update_daily()
    if stats_daily:
        print(f"🛢  Brent täglich:   {stats_daily['last_price']:.2f} USD {stats_daily['trend']} "
              f"(Stand: {stats_daily['last_date']}) | {stats_daily['rows']} Zeilen")

    print("\n─── Intraday stündlich (yfinance BZ=F) ───")
    stats_intraday = update_intraday()
    if stats_intraday:
        print(f"🛢  Brent stündlich: {stats_intraday['last_price']:.2f} USD {stats_intraday['trend']} "
              f"(Stand: {stats_intraday['last_date']}) | {stats_intraday['rows']} Zeilen")

    if "GITHUB_OUTPUT" in os.environ and stats_daily:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_price={stats_daily['last_price']}\n")
            f.write(f"trend={stats_daily['trend']}\n")
            f.write(f"updated={stats_daily['updated']}\n")