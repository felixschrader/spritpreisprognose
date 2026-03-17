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
│       ├── update_brent_prices.yml   # GitHub Actions: Brent-Update 2x täglich
│       └── update_eur_usd.yml        # GitHub Actions: EUR/USD-Update 2x täglich
├── data/
│   ├── brent_futures_daily.csv       # Brent Futures, täglich seit 2014 (auto-update)
│   ├── brent_futures_intraday_1h.csv # Brent Futures, stündlich letzte 60 Tage (auto-update)
│   └── eur_usd_rate.csv              # EUR/USD Referenzkurs, täglich (auto-update)
├── export/                           # Exportierte Auswertungen
├── papers/                           # Fachliteratur & Referenzen
├── brent_price.py                    # Brent-Datenabruf (Yahoo Finance BZ=F)
├── eur_usd_rate.py                   # EUR/USD-Datenabruf (EZB API)
├── tankstelle_analyse.ipynb          # Hauptanalyse (EDA, Zeitreihen, ML)
├── .env.example                      # Vorlage für API-Keys (nie .env committen!)
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
cp .env.example .env
# .env mit API-Keys befüllen (siehe unten)
```

**Benötigte Umgebungsvariablen (`.env`):**

```
SLACK_WEBHOOK=https://hooks.slack.com/...   # Für GitHub Actions Benachrichtigungen
```

> Tankerkönig API-Key unter [tankerkoenig.de](https://creativecommons.tankerkoenig.de/) beantragen und in `.env` eintragen.

---

## Verwendung

```bash
# Jupyter Notebook starten
jupyter notebook tankstelle_analyse.ipynb

# Brent-Preise manuell abrufen & CSVs aktualisieren
python brent_price.py

# EUR/USD-Kurs manuell abrufen & CSV aktualisieren
python eur_usd_rate.py
```

---

## Daten

### Tankerkönig
Die Kraftstoffpreisdaten stammen von der **Tankerkönig Open Data API** (Lizenz: CC BY 4.0) und werden lokal auf einem externen Laufwerk vorgehalten. Rohdaten sind nicht im Repository enthalten — zu groß und nicht öffentlich weiterverteilbar.

### Brent Rohölpreis
Brent Crude Oil Last Day Financial Futures (`BZ=F`) von Yahoo Finance via `yfinance`:
- **`data/brent_futures_daily.csv`** — tägliche Schlusskurse seit 2014, Spalte `brent_futures_usd`
- **`data/brent_futures_intraday_1h.csv`** — stündliche Kurse der letzten 60 Tage, Spalte `brent_futures_usd_1h`

Warum Futures statt Spot-Preis? Offizielle Spot-Daten (EIA, FRED) haben bis zu einer Woche Veröffentlichungsverzug. Tankstellen orientieren sich an Markterwartungen — Futures sind tagesaktuell und bilden das besser ab.

### EUR/USD
Offizieller EZB-Referenzkurs via ECB Statistical Data Warehouse API:
- **`data/eur_usd_rate.csv`** — tägliche Kurse, Spalte `eur_usd`

Rohöl wird global in USD gehandelt. Der EUR/USD-Kurs beeinflusst direkt den Einkaufspreis für europäische Raffinieren — und damit die Tankstellenpreise.

---

## Automatisierung

Die Marktdaten werden automatisch via **GitHub Actions** aktualisiert und direkt auf `main` gepusht:

| Workflow | Skript | Zeitplan | Daten |
|----------|--------|----------|-------|
| `update_brent_prices.yml` | `brent_price.py` | 8:00 + 20:00 Uhr MEZ | `brent_futures_daily.csv`, `brent_futures_intraday_1h.csv` |
| `update_eur_usd.yml` | `eur_usd_rate.py` | 9:00 + 21:00 Uhr MEZ | `eur_usd_rate.csv` |

Nach jedem Lauf wird eine Slack-Benachrichtigung mit aktuellem Kurs/Preis und Trend verschickt. Der Workflow pusht immer direkt auf `main` — Feature-Branches enthalten keine Datendateien, um Merge-Konflikte zu vermeiden.

---

## Ergebnisse

*Werden nach Abschluss der Analyse ergänzt.*

---

## Lizenz

MIT License — Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo, 2026