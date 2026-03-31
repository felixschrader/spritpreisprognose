# DSI Capstone Project 2026 - Fuel Price Forecast MVP

> Capstone project in the 6-month Data Science training program at the Data Science Institute ([DSI](https://data-science-institute.de/)).
>
> Team: Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo

[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-blue)](https://github.com/felixschrader/spritpreisprognose)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit_Cloud-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/Data-CC_BY_4.0-green)](https://creativecommons.org/licenses/by/4.0/)

---

## 1) Context

This project was built as a practical capstone in a constrained setting: the full training program runs over six months, but the MVP implementation window for this prototype was about two weeks.

The goal was to deliver a robust and operational short-term forecast for one local station first, with a design that can be extended later to:
- other stations,
- local competitor-aware setups,
- additional fuel types (E5/E10).

The current production focus is Diesel at ARAL Duerener Str. 407, Cologne.

---

## 2) Target Group

Primary users of the MVP are:
- drivers with short-term fueling decisions,
- project stakeholders evaluating model usefulness in practice,
- technical reviewers interested in end-to-end ML deployment under time constraints.

---

## 3) Core Question

How can we build a robust, interpretable short-term fuel price forecast despite:
- strong intraday pricing cycles,
- local competitive reaction patterns,
- noisy high-frequency raw price data?

---

## 4) Methodology (argumentation chain)

### 4.1 Why a core-price proxy?

Raw station prices are highly volatile intraday. For a stable target signal, we define a **core price** that is comparable across days with less noise.

### 4.2 Core-price definition

1. Aggregate raw price events into hourly bins (median per hour).
2. Keep the empirically most stable window: **13:00-20:00**.
3. Use **P10** across that window as daily core price proxy.

Rationale:
- This suppresses morning spike artifacts.
- It remains conservative for daily buying opportunities.
- It supports temporal comparability for modeling.

### 4.3 Market structure signals used

Besides station-level dynamics, we model:
- **Pass-through behavior** (oil/currency effects to local core price),
- **Residual persistence** (station vs market-relative component).

We do not claim a final causal proof of Rockets-and-Feathers in this MVP. The current analysis is framed as evidence patterns to be refined in future work.

---

## 5) Architecture and model production

### 5.1 ETL and EDA foundation

- ETL ingests Tankerkoenig data, updates curated parquet/csv assets, and keeps historical continuity.
- EDA was used to identify stable time windows, cycle patterns, and robust target candidates.

### 5.2 ML pipeline

- Feature sets combine lagged core-price deltas, market context, and external drivers.
- A staged experimental process compares alternative horizons/shifts and target definitions.

### 5.3 Target-variable selection (iterative search)

The target was selected via iterative testing (grid-like search across horizon and shift choices).
Final choice:

`roll3_shift2`:  
`rolling_mean(core_price, 3).shift(-2) - rolling_mean(core_price, 3)`

This setup gave the best balance between directional signal quality and robustness for MVP constraints.

### 5.4 Feature engineering

Main feature groups:
- lagged station core-price signals,
- market-relative residuals,
- external variables (Brent, EUR/USD, calendar, weather, CO2/tax context),
- simple regime indicators (e.g., days since last increase).

### 5.5 Train/test split

Temporal split is used (no random shuffle), preserving causal order and avoiding leakage from future observations.

### 5.6 Model selection

The final production model is a **Random Forest Regressor** on the selected target.
Competing model families were benchmarked, but RF provided the best practical trade-off for this MVP.

### 5.7 Evaluation (MVP level)

Reference metrics from the current setup:
- Directional accuracy (test): ~67.9%
- MAE (test): ~0.89 cent
- R2 (test): ~0.30

### 5.8 Model persistence

Trained artifacts are stored in `data/ml/` and consumed by inference scripts and dashboard components.

---

## 6) Automation with GitHub Actions

All recurring data/model updates are automated via GitHub Actions.
Cron schedules are configured in **UTC**.

| Workflow | Purpose | Schedule (UTC) |
|---|---|---|
| `update_tankstellen.yml` | Update station price history | daily `04:00` |
| `live_inference.yml` | Hourly short-term inference | hourly at `:15` |
| `live_inference_tagesbasis.yml` | Daily day-basis inference | daily `09:00` |
| `update_brent_prices.yml` | Brent updates | every 2h at `:00` |
| `update_eur_usd.yml` | EUR/USD updates | every 2h at `:10` |
| `update_wetter.yml` | Weather update | daily `04:30` |
| `update_co2_abgabe.yml` | CO2 levy update | Tuesdays `06:00` |
| `update_feiertage.yml` | Holiday update | yearly Jan 1, `06:00` |
| `update_schulferien.yml` | School holiday update | yearly Jan 2, `07:00` |
| `backfill.yml` | Manual historical backfill | manual trigger only |

---

## 7) Streamlit dashboard implementation

The dashboard is implemented in Streamlit (`scripts/dashboard.py`) and includes:
- model outputs and confidence-oriented KPI panels,
- short-term forecast visualization,
- generated recommendation text via Anthropic API,
- map integration using OpenStreetMap,
- custom styling/theme for presentation-oriented readability.

## 8) Project structure

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

## 9) Tech stack

### Core components
- Python
- pandas / numpy
- scikit-learn
- Streamlit
- Plotly
- GitHub Actions

### APIs and external services
- Tankerkoenig / MTS-K
- Anthropic API (text generation)
- OpenStreetMap

---

## 10) Local run

```bash
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose
pip install -r requirements.txt

# optional: local secrets
echo "TANKERKOENIG_KEY=your_key" > .env
echo "ANTHROPIC_API_KEY=your_key" >> .env

# dashboard
streamlit run scripts/dashboard.py

# daily inference (manual run)
python scripts/inference/live_inference_tagesbasis.py
```

---

## Team

| Name | Role |
|---|---|
| Felix Schrader | Infrastructure, Data Engineering, ML, Automation |
| Girandoux Fandio Nganwajop | ETL, EDA, Data Engineering |
| Ghislain Wamo | Data Architecture, Dashboard |

