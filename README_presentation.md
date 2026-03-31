# DSI Capstone Project 2026 - MVP Kraftstoffpreisprognose

> Capstone-Projekt im 6-monatigen Data-Science-Weiterbildungsprogramm des Data Science Institute ([DSI](https://data-science-institute.de/)).
>
> Team: Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo

[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-blue)](https://github.com/felixschrader/spritpreisprognose)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit_Cloud-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/Data-CC_BY_4.0-green)](https://creativecommons.org/licenses/by/4.0/)

---

## Executive Summary

Dieses Capstone liefert ein produktionsnahes **MVP für die kurzfristige Dieselpreisprognose** an einer lokalen Station in Köln.
Die Umsetzung erfolgte bewusst unter engen Rahmenbedingungen (ca. zwei Wochen Umsetzungszeit) und war auf drei Ergebnisse optimiert:
- ein robustes und nachvollziehbares Prognosesignal,
- reproduzierbare Automatisierung von Daten bis Inference,
- ein Dashboard, das Ergebnisse auch für nicht-technische Stakeholder verständlich macht.

Die zentrale methodische Entscheidung war, **nicht** mit rohen Intraday-Preisen zu modellieren, sondern mit einem **täglichen Kernpreis-Proxy**.
Das reduziert Rauschen aus starken Tageszyklen und erzeugt ein stabileres Zielsignal.

Die Architektur ist bereits auf Erweiterungen vorbereitet:
- weitere Stationen,
- lokal wettbewerbssensitive Setups,
- zusätzliche Kraftstoffarten (E5/E10),
- vertiefte Marktmechanik-Analysen (z. B. Edgeworth-Zyklen).

---

## 1) Kontext

Dieses Projekt wurde als praxisnahes Capstone unter klaren Constraints umgesetzt: Das Gesamtprogramm läuft sechs Monate, das konkrete MVP-Umsetzungsfenster für diesen Prototyp lag jedoch bei etwa zwei Wochen.

Ziel war eine robuste und operationalisierbare Kurzfristprognose für zunächst eine lokale Station, mit einer Architektur, die später erweitert werden kann auf:
- weitere Stationen,
- lokale Wettbewerbsdynamik,
- zusätzliche Kraftstoffarten (E5/E10).

Aktueller Produktionsfokus: Diesel an der ARAL Dürener Str. 407, Köln.

---

## 2) Zielgruppe

Primäre Nutzergruppen des MVP sind:
- Fahrer:innen mit kurzfristigen Tankentscheidungen,
- Projektstakeholder, die den praktischen Nutzen des Modells bewerten,
- technische Reviewer mit Fokus auf End-to-End-ML unter Zeitdruck.

---

## 3) Kernfrage

Wie bauen wir eine robuste, nachvollziehbare Kurzfristprognose, obwohl:
- starke Intraday-Preiszylken auftreten,
- lokale Wettbewerbsreaktionen die Dynamik prägen,
- hochfrequente Rohdaten stark verrauscht sind?

---

## 3.1) Was das MVP bereits liefert

- Eine operationale End-to-End-Pipeline von Rohdaten-Update bis Live-Ausgabe im Dashboard.
- Richtungsorientierte Prognosequalität klar über naiven Richtungs-Baselines.
- Transparente Modellentscheidungen, die sich sauber präsentieren und begründen lassen.
- Eine modulare Skriptarchitektur (`inference`, `features`, `pipeline`) für spätere Skalierung.

---

## 4) Methodik (Argumentationskette)

### 4.1 Warum ein Kernpreis-Proxy?

Rohpreise sind intraday sehr volatil. Für ein stabiles Zielsignal definieren wir einen **Kernpreis**, der über Tage besser vergleichbar und weniger verrauscht ist.

### 4.2 Kernpreis-Definition

1. Aggregation der Rohpreis-Events in Stunden-Bins (Median pro Stunde).
2. Fokus auf das empirisch stabilste Zeitfenster: **13:00-20:00**.
3. Verwendung von **P10** in diesem Fenster als täglicher Kernpreis-Proxy.

Begründung:
- Unterdrückt Artefakte von Morgenspikes.
- Bleibt konservativ im Hinblick auf tägliche Kaufzeitpunkte.
- Verbessert die zeitliche Vergleichbarkeit für das Modell.

### 4.3 Verwendete Marktstruktur-Signale

Neben stationsspezifischer Dynamik modellieren wir:
- **Pass-through-Verhalten** (Öl-/Währungsimpulse auf den lokalen Kernpreis),
- **Residuum-Persistenz** (stationsrelativer Anteil gegenüber dem Markt).

Wir beanspruchen im MVP keinen finalen kausalen Nachweis von Rockets-and-Feathers.
Stattdessen berichten wir belastbare Evidenzmuster als strukturierte Hypothesen für nächste Iterationen.

---

## 5) Architektur und Modellproduktion

### 5.1 ETL- und EDA-Fundament

- ETL ingestiert Tankerkoenig-Daten, aktualisiert kuratierte Parquet/CSV-Artefakte und sichert historische Kontinuität.
- EDA identifiziert stabile Zeitfenster, Zyklusmuster und robuste Zielkandidaten.

### 5.2 ML-Pipeline

- Feature-Sets kombinieren gelaggte Kernpreis-Deltas, Marktkontext und externe Treiber.
- Ein stufenweiser Experimentprozess vergleicht alternative Horizonte/Shifts und Zieldefinitionen.

### 5.3 Zielvariablen-Auswahl (iterative Suche)

Die Zielvariable wurde iterativ ausgewählt (grid-ähnliche Suche über Horizonte und Shift-Optionen).
Finale Wahl:

`roll3_shift2`:  
`rolling_mean(core_price, 3).shift(-2) - rolling_mean(core_price, 3)`

Dieses Setup lieferte im MVP den besten Kompromiss aus Richtungsqualität und Robustheit.

### 5.4 Feature Engineering

Hauptgruppen:
- gelaggte stationsbezogene Kernpreis-Signale,
- marktrelative Residuen,
- externe Variablen (Brent, EUR/USD, Kalender, Wetter, CO2-/Steuerkontext),
- einfache Regime-Indikatoren (z. B. Tage seit letzter Erhöhung).

### 5.5 Train/Test-Split

Wir nutzen einen zeitlichen Split (kein zufälliges Shuffle), um kausale Reihenfolge zu erhalten und Leakage aus Zukunftsdaten zu vermeiden.

### 5.6 Modellauswahl

Das finale Produktionsmodell ist ein **Random Forest Regressor** auf der gewählten Zielvariable.
Verglichene Modellfamilien wurden benchmarkt, RF lieferte im MVP den besten praktischen Trade-off.

### 5.7 Evaluation (MVP-Stand)

Referenzmetriken im aktuellen Setup:
- Richtungsgenauigkeit (Test): ~67,9%
- MAE (Test): ~0,89 Cent
- R2 (Test): ~0,30

Interpretation für die Präsentation:
- Das Modell ist **kein** „perfekter Preisvorhersager“.
- Es ist ein robuster Entscheidungsunterstützer unter realistischen Projektbedingungen.

### 5.8 Modell-Persistenz

Trainierte Artefakte werden in `data/ml/` gespeichert und von Inference-Skripten sowie Dashboard-Komponenten verwendet.

---

## 6) Automatisierung mit GitHub Actions

Alle wiederkehrenden Daten-/Modellupdates laufen automatisiert über GitHub Actions.
Cron-Zeiten sind in **UTC** konfiguriert.

| Workflow | Zweck | Zeitplan (UTC) |
|---|---|---|
| `update_tankstellen.yml` | Update Stationspreishistorie | täglich `04:00` |
| `live_inference.yml` | Stündliche Kurzfrist-Inference | stündlich um `:15` |
| `live_inference_tagesbasis.yml` | Tägliche Tagesbasis-Inference | täglich `09:00` |
| `update_brent_prices.yml` | Brent-Updates | alle 2h um `:00` |
| `update_eur_usd.yml` | EUR/USD-Updates | alle 2h um `:10` |
| `update_wetter.yml` | Wetter-Update | täglich `04:30` |
| `update_co2_abgabe.yml` | CO2-Abgabe-Update | dienstags `06:00` |
| `update_feiertage.yml` | Feiertags-Update | jährlich 1. Jan, `06:00` |
| `update_schulferien.yml` | Schulferien-Update | jährlich 2. Jan, `07:00` |
| `backfill.yml` | Manuelles historisches Backfill | nur manueller Trigger |

---

## 7) Streamlit-Dashboard-Implementierung

Das Dashboard ist in Streamlit (`scripts/dashboard.py`) umgesetzt und enthält:
- Modellausgaben und KPI-Panels mit Entscheidungsfokus,
- Visualisierung der Kurzfristprognose,
- generierte Empfehlungstexte via Anthropic API,
- Kartenintegration mit OpenStreetMap,
- ein angepasstes Theme für präsentationsnahe Lesbarkeit.

Die Trennung von Automatisierung, Inference und UI hält das MVP wartbar und erweiterbar.

---

## 8) Projektstruktur

```text
spritpreisprognose/
├── data/
│   ├── tankstellen_preise.parquet
│   ├── tankstellen_stationen.parquet
│   ├── brent_futures_daily.csv
│   ├── eur_usd_rate.csv
│   ├── feiertage.csv
│   ├── schulferien.csv
│   ├── wetter_koeln.csv
│   └── ml/
│       ├── prognose_aktuell.json
│       ├── prognose_tagesbasis.json
│       ├── modell_rf_markt_aral_duerener.pkl
│       └── modell_metadaten_markt_aral_duerener.json
├── scripts/
│   ├── dashboard.py
│   ├── README.md
│   ├── inference/
│   │   ├── live_inference.py
│   │   └── live_inference_tagesbasis.py
│   ├── features/
│   │   ├── brent_price.py
│   │   ├── eur_usd_rate.py
│   │   ├── wetter_koeln.py
│   │   ├── feiertage.py
│   │   ├── schulferien.py
│   │   ├── co2_abgabe.py
│   │   ├── energiesteuer.py
│   │   └── externe_effekte.py
│   └── pipeline/
│       ├── tankerkoenig_pipeline.py
│       └── backfill_prognose_log.py
├── notebooks/
│   └── Machine_Learning_Tagesbasis.ipynb
├── .github/workflows/
└── requirements.txt
```

---

## 9) Tech-Stack

### Kernkomponenten
- Python
- pandas / numpy
- scikit-learn
- Streamlit
- Plotly
- GitHub Actions

### APIs und externe Services
- Tankerkoenig / MTS-K
- Anthropic API (text generation)
- OpenStreetMap

---

## 10) Lokaler Start

```bash
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose
pip install -r requirements.txt

# optional: lokale Secrets
echo "TANKERKOENIG_KEY=your_key" > .env
echo "ANTHROPIC_API_KEY=your_key" >> .env

# Dashboard
streamlit run scripts/dashboard.py

# Tages-Inference (manuell)
python scripts/inference/live_inference_tagesbasis.py
```

---

## Team

| Name | Rolle |
|---|---|
| Felix Schrader | Infrastruktur, Data Engineering, ML, Automatisierung |
| Girandoux Fandio Nganwajop | ETL, EDA, Data Engineering |
| Ghislain Wamo | Datenarchitektur, Dashboard |

---

## Hinweise für die Abschlusspräsentation

- Betont die **Entscheidungskette** (Problem -> Kernpreis-Proxy -> Target-Suche -> Modell -> Deployment), nicht nur die Metriken.
- Trennt klar zwischen **aktueller MVP-Scope** und **nächsten Ausbaustufen**.
- Positioniert das Ergebnis als robusten Prototyp mit produktionsnaher Automatisierung, nicht als fertige Marktsimulation.
