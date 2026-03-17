# Spritpreisprognose

Analyse und Prognose von Kraftstoffpreisen an deutschen Tankstellen — Abschlussprojekt der [Data Science Institute](https://data-science-institute.de/) Weiterbildung (6 Monate Data Science).

---

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Projektstruktur](#projektstruktur)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Daten](#daten)
- [Automatisierung](#automatisierung)
- [Ergebnisse](#ergebnisse)
- [Lizenz](#lizenz)

---

## Überblick

Dieses Projekt untersucht die Preisentwicklung von Kraftstoffen (E10, Diesel) an deutschen Tankstellen. Ziel ist es, Muster in den Preisschwankungen zu erkennen und eine Prognose für zukünftige Preise zu erstellen — inklusive eines Live-Dashboards zur Abfragezeit.

**Methoden:**
- Explorative Datenanalyse (EDA)
- Zeitreihenanalyse
- Prognosemodellierung (ML)
- Live-Prognose via Streamlit-Dashboard

**Datenquellen:**

| Quelle | Inhalt | Frequenz | Zugang |
|--------|--------|----------|--------|
| [Tankerkönig Open Data API](https://creativecommons.tankerkoenig.de/) | Kraftstoffpreise deutscher Tankstellen | täglich (historisch ab 2014) | kostenlos, API-Key nötig |
| [Yahoo Finance (BZ=F)](https://finance.yahoo.com/quote/BZ=F) | Brent Crude Oil Futures — täglich seit 2014 | täglich | kostenlos, kein Key |
| [Yahoo Finance (BZ=F)](https://finance.yahoo.com/quote/BZ=F) | Brent Crude Oil Futures — stündlich | stündlich, letzte 60 Tage | kostenlos, kein Key |
| [EZB Statistical Data Warehouse](https://data-api.ecb.europa.eu) | EUR/USD Referenzkurs | täglich | kostenlos, kein Key |

---

## Projektstruktur
```
spritpreisprognose/
├── .github/
│   └── workflows/
│       ├── update_tankstellen.yml    # GitHub Actions: Tankstellen-Update täglich 5:00 Uhr
│       ├── update_brent_prices.yml   # GitHub Actions: Brent-Update 2x täglich
│       └── update_eur_usd.yml        # GitHub Actions: EUR/USD-Update 2x täglich
├── data/
│   ├── tankstellen_preise.parquet    # Kraftstoffpreise, 2,4 Mio. Zeilen ab 2014 (auto-update)
│   ├── tankstellen_stationen.parquet # 30 Tankstellen im 5 km-Umkreis Köln (auto-update)
│   ├── brent_futures_daily.csv       # Brent Futures, täglich seit 2014 (auto-update)
│   ├── brent_futures_intraday_1h.csv # Brent Futures, stündlich letzte 60 Tage (auto-update)
│   └── eur_usd_rate.csv              # EUR/USD Referenzkurs, täglich (auto-update)
├── papers/                           # Fachliteratur & Referenzen
├── brent_price.py                    # Brent-Datenabruf (Yahoo Finance BZ=F)
├── eur_usd_rate.py                   # EUR/USD-Datenabruf (EZB API)
├── tankerkoenig_pipeline.py          # ETL-Pipeline: Tankerkönig CSV → Parquet
├── .env.template                     # Vorlage für API-Keys (nie .env committen!)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Team

| Name | GitHub | Schwerpunkt |
|------|--------|-------------|
| Felix Schrader | [@felixschrader](https://github.com/felixschrader) | ML, Infrastruktur |
| Girandoux Fandio Nganwajop | [@Girandoux](https://github.com/Girandoux) | — |
| Ghislain Wamo | [@GhislainWamo](https://github.com/GhislainWamo) | — |

---

## Installation
```bash
# Repo klonen
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen einrichten
cp .env.template .env
# .env mit eigenen Keys befüllen
```

**Benötigte Umgebungsvariablen (`.env`):**
```
SLACK_WEBHOOK=https://hooks.slack.com/...   # Für GitHub Actions Benachrichtigungen
```

---

## Verwendung
```bash
# Brent-Preise manuell abrufen & CSVs aktualisieren
python brent_price.py

# EUR/USD-Kurs manuell abrufen & CSV aktualisieren
python eur_usd_rate.py

# Tankstellen-Pipeline manuell ausführen
python tankerkoenig_pipeline.py --update --no-pull
```

---

## Daten

### Tankerkönig — Kraftstoffpreise

Die historischen Preisdaten werden täglich über ein passwortgeschütztes Git-Repository
von Tankerkönig bezogen und als Parquet-Datei im Repository abgelegt.

**`data/tankstellen_preise.parquet`** — 2,4 Mio. Zeilen, Juni 2014 bis heute

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `date` | datetime64 | Zeitstempel der Preisänderung |
| `station_uuid` | string | Eindeutige Tankstellen-ID |
| `diesel` | float32 | Dieselpreis in EUR |
| `e5` | float32 | Super E5-Preis in EUR |
| `e10` | float32 | Super E10-Preis in EUR |

**`data/tankstellen_stationen.parquet`** — 30 Tankstellen im 5 km-Umkreis um Köln (Referenz: Aral Dürener Str. 407)

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `uuid` | string | Eindeutige ID, Foreign Key zu `tankstellen_preise` |
| `name` | string | Name der Tankstelle |
| `brand` | string | Marke (z.B. ARAL, SHELL, STAR) |
| `street` | string | Straße |
| `house_number` | string | Hausnummer |
| `post_code` | string | Postleitzahl |
| `city` | string | Stadt |
| `latitude` | float64 | Geographische Breite |
| `longitude` | float64 | Geographische Länge |
| `distanz_km` | float64 | Entfernung zur Referenz-Tankstelle in km |
| `stadt` | string | Städtezuordnung |

#### Daten laden
```python
import pandas as pd

# Preisdaten
df = pd.read_parquet("data/tankstellen_preise.parquet")

# Stationsdaten
df_stationen = pd.read_parquet("data/tankstellen_stationen.parquet")

# Beides verknüpfen
df_merged = df.merge(df_stationen, left_on="station_uuid", right_on="uuid")
```

> Parquet ist ein spaltenorientiertes Binärformat das gegenüber CSV deutlich kompakter
> und schneller zu lesen ist — bei 2,4 Mio. Zeilen ein relevanter Unterschied.
> Voraussetzung: `pyarrow` (bereits in `requirements.txt` enthalten).

### Brent Rohölpreis

Brent Crude Oil Last Day Financial Futures (`BZ=F`) von Yahoo Finance via `yfinance`:
- **`data/brent_futures_daily.csv`** — tägliche Schlusskurse seit 2014, Spalte `brent_futures_usd`
- **`data/brent_futures_intraday_1h.csv`** — stündliche Kurse der letzten 60 Tage, Spalte `brent_futures_usd_1h`

Warum Futures statt Spot-Preis? Offizielle Spot-Daten (EIA, FRED) haben bis zu einer Woche
Veröffentlichungsverzug. Tankstellen orientieren sich an Markterwartungen — Futures sind
tagesaktuell und bilden das besser ab.

### EUR/USD

Offizieller EZB-Referenzkurs via ECB Statistical Data Warehouse API:
- **`data/eur_usd_rate.csv`** — tägliche Kurse, Spalte `eur_usd`

Rohöl wird global in USD gehandelt. Der EUR/USD-Kurs beeinflusst direkt den Einkaufspreis
für europäische Raffinerien — und damit die Tankstellenpreise.

---

## Automatisierung

Die Daten werden vollautomatisch via **GitHub Actions** aktualisiert und direkt auf `main`
gepusht. Nach jedem Lauf wird eine Slack-Benachrichtigung mit Status und Kennzahlen
verschickt. Feature-Branches enthalten keine Datendateien, um Merge-Konflikte zu vermeiden.

| Workflow | Skript | Zeitplan | Aktualisierte Dateien |
|----------|--------|----------|-----------------------|
| `update_tankstellen.yml` | `tankerkoenig_pipeline.py` | täglich 5:00 Uhr MEZ | `tankstellen_preise.parquet`, `tankstellen_stationen.parquet` |
| `update_brent_prices.yml` | `brent_price.py` | 8:00 + 20:00 Uhr MEZ | `brent_futures_daily.csv`, `brent_futures_intraday_1h.csv` |
| `update_eur_usd.yml` | `eur_usd_rate.py` | 9:00 + 21:00 Uhr MEZ | `eur_usd_rate.csv` |

### Technische Details

Der Tankerkönig-Workflow nutzt zwei Git-Optimierungen um den Download auf wenige MB zu
begrenzen, anstatt das gesamte Archiv (mehrere GB) zu übertragen:

- **`--depth 1`** — lädt nur den aktuellsten Commit, keine History
- **`--filter=blob:none` + Sparse Checkout** — überträgt zunächst nur die Verzeichnisstruktur
  und materialisiert anschließend exakt die zwei benötigten Tages-CSVs sowie die Stammdaten

Alle drei Workflows teilen denselben pip-Cache (identischer Hash über `requirements.txt`),
sodass Pakete nicht bei jedem Lauf neu installiert werden müssen.

---

## Ergebnisse

*Werden nach Abschluss der Analyse ergänzt.*

---

## Lizenz

**Code** (`.py`, `.yml`, Notebooks): [MIT License](https://opensource.org/licenses/MIT) — Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo, 2026

**Daten** (`data/`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — abgeleitet aus [Tankerkönig Open Data](https://creativecommons.tankerkoenig.de/), lizenziert unter CC BY-NC-SA 4.0