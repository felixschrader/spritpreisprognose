# DSI Capstone Project 2026 — MVP Kraftstoffpreisprognose (Diesel)

## Live-Dashboard

[![Streamlit — Live-App](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dieselpreisprognose.streamlit.app)

### Team auf LinkedIn

[![LinkedIn Felix](https://img.shields.io/badge/LinkedIn-Felix_Schrader-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/felixschrader/)
[![LinkedIn Girandoux](https://img.shields.io/badge/LinkedIn-Girandoux_Fandio-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/girandoux-fandio-08628bb9/)
[![LinkedIn Ghislain](https://img.shields.io/badge/LinkedIn-Ghislain_Wamo-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo)

> Capstone-Projekt im 6-monatigen Data-Science-Weiterbildungsprogramm am **Data Science Institute** ([DSI](https://data-science-institute.de/)) · Standort der Weiterbildung: **Berlin**  
> **Team:** Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo  
> **Referenz-Tankstelle:** ARAL · Dürener Str. 407 · 50858 Köln — [**Seite bei Aral**](https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400) · Rohpreise & Historie: [Tankerkönig](https://www.tankerkoenig.de) / MTS-K

[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github)](https://github.com/felixschrader/spritpreisprognose)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/felixschrader/spritpreisprognose/actions)

---

## Machine Learning — Detailanalyse (Notebook)

Für **Feature Engineering, Modellvergleich, Zielvariablen-Tests und SHAP** liegt die ausführliche Arbeitsgrundlage im Notebook:

**[notebooks/Machine_Learning_Tagesbasis.ipynb](https://github.com/felixschrader/spritpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb)**

---

## 1) Kontext

Dieses Projekt entstand als praxisnahes Capstone unter klaren Rahmenbedingungen: Das Gesamtprogramm läuft sechs Monate, das **konkrete MVP-Umsetzungsfenster** für diesen Prototyp lag bei etwa **zwei Wochen**.

Ziel war eine **robuste und operationalisierbare Kurzfristprognose** für zunächst **eine lokale Station**, mit einer Architektur, die später erweitert werden kann auf weitere Stationen, lokale Wettbewerbsdynamik und weitere Kraftstoffarten (E5/E10).

**Aktueller Produktionsfokus:** Diesel an der **ARAL Dürener Str. 407, 50858 Köln** — [Stationsseite Aral](https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400).

---

## 2) Zielgruppe

- Fahrer:innen mit kurzfristigen Tankentscheidungen  
- Projektstakeholder zur Bewertung des praktischen Nutzens  
- technische Reviewer mit Interesse an End-to-End-ML unter Zeitdruck  

---

## 3) Kernfrage

Wie lässt sich eine **robuste, nachvollziehbare Kurzfristprognose** aufbauen, obwohl starke Intraday-Preiszyklen, lokale Wettbewerbsreaktionen und hochfrequente Rohdaten das Signal überlagern?

---

## 4) Methodik (Argumentationskette)

### 4.1 Warum ein Kernpreis-Proxy?

Rohpreise sind intraday sehr volatil. Für ein stabiles Zielsignal definieren wir einen **Kernpreis**, der über Tage besser vergleichbar und weniger verrauscht ist.

### 4.2 Kernpreis-Definition

1. Aggregation der Rohpreis-Events in **Stunden-Bins** (Median pro Stunde).  
2. Fokus auf das empirisch stabilste Zeitfenster: **13:00–20:00** Uhr.  
3. **P10 (10. Perzentil):** Aus allen Stundenwerten in diesem Fenster wird der Wert genommen, unter dem **10 %** der Beobachtungen liegen und **90 %** darüber — vereinfacht: ein **eher niedriger, konservativer Referenzpreis** für den Tag, der nicht von einzelnen Spitzen nach oben dominiert wird und für Nicht-Techniker als „eher günstiger Tagesanker“ interpretierbar ist.

**Begründung:** Unterdrückt Morgenspike-Artefakte, bleibt konservativ für Tankzeitpunkte und verbessert die zeitliche Vergleichbarkeit für das Modell.

### 4.3 Marktstruktur-Signale

- **Pass-through-Verhalten** (Öl-/Währungsimpulse auf den lokalen Kernpreis).  
- **Residuum-Persistenz** (Abweichung der Station gegenüber einem Markt-Referenzsignal).  
- **Markt-Kontext:** Als Proxy für den **NRW-Markt** wurden **alle ARAL-Stationen in NRW** (im Metadaten-Setup: **585 Stationen**) in die Analyse einbezogen — die eigene Station wird relativ zu diesem Markt gefasst.

Im MVP wird **kein finaler kausaler Nachweis** von Rockets-and-Feathers beansprucht; die Auswertung bleibt als **Evidenzmuster** formuliert.

---

## 5) Architektur und Modellproduktion

### 5.1 ETL und EDA

- ETL ingestiert Tankerkönig-Daten, aktualisiert kuratierte Parquet/CSV-Artefakte und sichert historische Kontinuität.  
- EDA dient der Identifikation stabiler Zeitfenster, Zyklusmuster und robuster Zielkandidaten.

### 5.2 ML-Pipeline (Überblick)

- Feature-Sets kombinieren gelaggte Kernpreis-Signale, Marktkontext und externe Treiber.  
- Ein stufenweiser Experimentprozess vergleicht alternative Horizonte, Shifts und Zieldefinitionen.

### 5.3 Zielvariable (iterativ gewählt)

Gesucht wurde eine Zielgröße, die **Richtungsänderungen** des geglätteten Kernpreises über mehrere Tage abbildet, ohne auf reine Tages-Rohdeltas zu kollabieren.

**Festlegung im Projekt:** Differenz aus einem **gleitenden 3-Tage-Mittel** des Kernpreises (`roll3`) und dem **gleichen Mittel zwei Schritte voraus** in der **täglichen** Preisreihe (`shift(-2)` in pandas — typischerweise **zwei Kalendertage**, sofern die Reihe lückenlos je Kalendertag geführt wird; es handelt sich **nicht** um eine eigene „Handelskalender“-Logik wie an der Börse). Intuition: Es wird prognostiziert, wie sich das **kurzfristig geglättete Preisniveau** nach dem gewählten Horizont gegenüber dem **jeweiligen Referenztag in der Reihe** verändert — **nicht** der Minutenpreis an der Zapfsäule.

**Praxis:** Ausgangspunkt ist der **Kernpreis des letzten geschlossenen Tages** — praktisch **gestern**. Die Aussage gilt für die **Kernpreis-Ebene**, nicht für den Minutenpreis „gerade jetzt“.

*(Formalisierung in den Modell-Metadaten und im Notebook; dort auch Vergleich mit einfacheren Zieldefinitionen.)*

### 5.4 Feature Engineering und Feature-Auswahl

- **Engineering:** u. a. gelaggte Kernpreis-Deltas, marktrelative Größen, Brent/Währung/Kalender/Wetter/Steuer-Kontext, einfache Regime-Indikatoren (z. B. Tage seit letzter Erhöhung/Senkung).  
- **Auswahl / Modellvergleich:** Im Notebook wurden **lineare Modelle (Ridge)**, **Random Forest**, **XGBoost** sowie **neuronale Ansätze (u. a. LSTM, CNN, Transformer)** geprüft; für das MVP wurde **Random Forest** nach Hyperparameter-Tuning (u. a. RandomizedSearch, zeitliche Kreuzvalidierung) als bester Kompromiss aus Stabilität, Interpretierbarkeit und Out-of-Sample-Performance gewählt. **SHAP** dient der Einordnung der Einflussstärken.  
- **Finale Feature-Liste** (Auszug aus den trainierten Metadaten): `brent_delta2`, `delta_kern_lag1/2`, `delta_markt_lag1/2`, `residuum_lag1`, `tage_seit_erhoehung`, `tage_seit_senkung`, `wochentag`, `ist_montag`, `markt_std` — Details und Varianten siehe **[Notebook](https://github.com/felixschrader/spritpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb)**.

### 5.5 Train/Test-Split

Zeitlicher Split (kein zufälliges Shuffle), um kausale Reihenfolge zu wahren und Leakage zu vermeiden.

### 5.6 Modellauswahl

**Random Forest Regressor** (getunt) auf der gewählten Zielvariable.

### 5.7 Evaluation (MVP-Stand)

Orientierung an den gespeicherten Modell-Metadaten (kann leicht von Lauf zu Lauf variieren), u. a. Richtungsgenauigkeit Test, MAE, R² — als **Entscheidungshilfe**, nicht als Garantie für einen exakten Minutenpreis.

**Baseline „Richtung“ (statistische Einordnung, Notebook / Metadaten):**  
Verglichen wird die **Vorzeichen-Übereinstimmung** zwischen Zielvariable *y* und Vorhersage *y_pred* (Klassifikations-Accuracy auf den binären Labels „y positiv?“ / „y_pred positiv?“, wie `sklearn.metrics.accuracy_score` auf `(y>0)` und `(y_pred>0)`). Die **naive Referenz** „immer 0 vorhersagen“ liefert dabei eine Trefferquote, die **exakt dem Anteil der Testtage mit y ≤ 0** entspricht — nicht einem festen 50-%-Zufallswert. Schiefe Verteilungen der Zielgröße (z. B. viele positive *y* im Test) ergeben daher **niedrige** Baselines; eine **annähernd symmetrische** Zielverteilung ergibt Baselines **nahe 50 %**. Das ist **plausibel** und spiegelt die **Stichprobe**, nicht einen Fehler der Metrik.  
Zusätzlich: **Korridor-Metrik** (Richtung stimmt und \(|\,y-\hat{y}\,|\) unter Schwelle, z. B. 0,5 ct) sowie Auswertungen nur bei **relevantem** \(|y|\) (siehe Notebook) — jeweils **andere** Fragestellungen als die reine Vorzeichen-Accuracy.

**Dashboard (Retrograde):** Die Log-Auswertung nutzt für „Richtung korrekt“ eine **±0,5-ct-Klassierung** von Predicted/Actual; das ist bewusst **laienfreundlicher** und **nicht identisch** mit der strengen Vorzeichen-Metrik im Notebook — beide sind konsistent dokumentiert, aber **nicht** dieselbe Zahl.

### 5.8 Modell-Persistenz

Trainierte Artefakte liegen unter `data/ml/` und werden von Inference-Skripten und dem Dashboard genutzt.

---

## 6) Automatisierung (GitHub Actions)

Datenaktualisierung, Feature-Berechnung und Inferenz laufen über **GitHub Actions** (Workflows unter [`.github/workflows/`](https://github.com/felixschrader/spritpreisprognose/tree/main/.github/workflows)).  
Dazu gehören u. a. **Tankstellen-/Preishistorie**, **Brent & EUR/USD**, **Wetter**, **Feiertage/Schulferien**, **CO₂-Abgabe** sowie **stündliche und tägliche Inference**. Konkrete Cron-Zeiten sind in den YAML-Dateien hinterlegt.

---

## 7) Streamlit-Dashboard

Implementiert in `scripts/dashboard.py` u. a. mit KPIs, Prognosevisualisierung, erklärenden Texten (**Anthropic API**), Kartenkontext (**OpenStreetMap**) und angepasstem Theme.

---

## 8) Projektstruktur (Auszug)

```text
spritpreisprognose/
├── data/
│   └── ml/                    # Modelle, Metadaten, Prognose-JSON
├── scripts/
│   ├── dashboard.py
│   ├── inference/
│   ├── features/
│   └── pipeline/
├── notebooks/
│   └── Machine_Learning_Tagesbasis.ipynb
├── papers/
└── requirements.txt
```

---

## 9) Tech-Stack und Schnittstellen (Auszug)

- **Python:** pandas, numpy, **scikit-learn**, Streamlit, Plotly, joblib  
- **Öl / FX:** **Yahoo Finance** (`yfinance`, Brent), **EZB-Daten-API** (EUR/USD)  
- **Tankstellenpreise:** **Tankerkönig** ([creativecommons.tankerkoenig.de](https://creativecommons.tankerkoenig.de) JSON-API, Key nötig)  
- **Kalender:** [feiertage-api.de](https://feiertage-api.de), [OpenHolidays API](https://openholidaysapi.org) (Schulferien)  
- **Wetter:** **DWD** OpenData  
- **CO₂-Abgabe:** u. a. **DEHSt** (Scraping/Parsing je nach Jahr)  
- **LLM:** **Anthropic** (Empfehlungstexte im Dashboard)  
- **Karte:** **OpenStreetMap** / Leaflet  
- **CI:** **GitHub Actions**

---

## 10) Literatur

**Wissenschaftliche Grundlagen** und **Begleitdokumente** — in **einer Tabelle**: zitierte Fachliteratur, Datengrundlage Tankerkönig (mit Link) sowie alle PDFs aus [`papers/`](papers/).

| Art | Titel / Quelle | Autor / Herausgeber | Jahr | Link & Kurzinfo |
|-----|----------------|---------------------|------|-----------------|
| Fachliteratur | *Rockets and Feathers: The Asymmetric Speed of Adjustment…* | Bacon, R.W. | 1991 | Klassische RF-Literatur (Energy Economics). |
| Fachliteratur | *Rockets and Feathers in German Gasoline Markets* | Frondel, Horvath, Sommer | 2021 | Ruhr Economic Papers. |
| Datengrundlage | Tankerkönig / MTS-K | — | — | [**tankerkoenig.de**](https://www.tankerkoenig.de) · offene Daten unter [**CC BY 4.0**](https://creativecommons.org/licenses/by/4.0/). |
| PDF | *Benzinpreise vorhersagen: Effizientes, maschinelles Lernen für Sparfüchse* | Golem.de | 2026 | Medienartikel zu ML und Benzinpreisen. |
| PDF | *Branchenuntersuchung Kraftstoffmarkt* | Schwarz, Moritz | 2022 | Branchenbericht Kraftstoffmarkt. |
| PDF | *Die Preisbindung im Oligopol* / Freilaw (Kraftstoffsektor) | Legner, Sarah | 2014 | Freilaw 1/2014. |
| PDF | *Mittels Deep Learning Benzinpreise vorhersagen* | Devoteam | k. A. | Expert View / Blog. |
| PDF | *Price Matching and Edgeworth Cycles* | Wilhelm, Sascha | 2019 | SSRN 2708630; u. a. Tankerkönig-Daten. |
| PDF | *Wie sich die Benzinpreise in Deutschland entwickeln* | Devoteam | k. A. | Expert View / Blog. |

---

## 11) Lokaler Start

```bash
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose
pip install -r requirements.txt

echo "TANKERKOENIG_KEY=dein_key" > .env
echo "ANTHROPIC_API_KEY=dein_key" >> .env

streamlit run scripts/dashboard.py
python scripts/inference/live_inference_tagesbasis.py
```

---

## Team

| Name | Rolle | LinkedIn |
|------|-------|----------|
| Felix Schrader | Infrastruktur, Data Engineering, ML, Automatisierung | [Profil](https://www.linkedin.com/in/felixschrader/) |
| Girandoux Fandio Nganwajop | ETL, EDA, Data Engineering | [Profil](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) |
| Ghislain Wamo | Datenarchitektur, Dashboard | [Suche](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo) |

---

*DSI Weiterbildung 2026 · Berlin*
