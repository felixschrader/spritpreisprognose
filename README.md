# Dieselpreisprognose

**MVP / Prototyp** — Capstone im Data-Science-Programm am [DSI Berlin](https://data-science-institute.de/). Umsetzung in einem **kurzen, festen Zeitfenster** (ca. zwei Wochen).

**Kontext:** eine Referenz-Tankstelle (Köln, Diesel), tägliche und stündliche Prognose-JSON, Streamlit-Dashboard.

**Metriken vs. Baseline:** Richtungs-Trefferquote auf dem Test-Split und Vergleich zur naiven Baseline („immer steigend“) stehen in den **ML-Metadaten** (`data/ml/`, z. B. `modell_metadaten_*.json`) und im Dashboard unter **Prognose-Performance**. Details der Definitionen im Code und im Notebook.

**Wo der ML-Code liegt**

| Bereich | Pfad |
|--------|------|
| Training / Experimente | `notebooks/Machine_Learning_Tagesbasis_ml_master_station.ipynb` |
| Tägliche Inferenz | `scripts/inference/live_inference_tagesbasis.py` |
| Stündliche Inferenz | `scripts/inference/live_inference.py` |
| Features & Pipeline | `scripts/features/`, `scripts/pipeline/` |
| Artefakte | `data/ml/` |

**KI:** Für **Dashboard-Implementierung** und **Refactoring** wurden KI-gestützte Editoren genutzt. **Inhaltliche und methodische Entscheidungen** liegen beim **Team**.

---

[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dieselpreisprognose.streamlit.app)

| | |
|--|--|
| Dashboard | [dieselpreisprognose.streamlit.app](https://dieselpreisprognose.streamlit.app) |
| Repo | [github.com/felixschrader/dieselpreisprognose](https://github.com/felixschrader/dieselpreisprognose) |

---

## Lokal

```bash
pip install -r requirements.txt
# optional: .env mit TANKERKOENIG_KEY, ggf. ANTHROPIC_API_KEY
streamlit run scripts/dashboard.py
```

Weitere Skripte: siehe [`scripts/README.md`](scripts/README.md).

## Lizenz

Quellcode: [MIT](LICENSE).
