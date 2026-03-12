# Spritpreisprognose

Analyse und Prognose von Kraftstoffpreisen an deutschen Tankstellen — Abschlussprojekt der DSI-Weiterbildung.

---

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Projektstruktur](#projektstruktur)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Daten](#daten)
- [Ergebnisse](#ergebnisse)
- [Lizenz](#lizenz)

---

## Überblick

Dieses Projekt untersucht die Preisentwicklung von Kraftstoffen (z. B. E10, Diesel) an deutschen Tankstellen. Ziel ist es, Muster in den Preisschwankungen zu erkennen und eine Prognose für zukünftige Preise zu erstellen.

**Methoden:**
- Explorative Datenanalyse (EDA)
- Zeitreihenanalyse
- Prognosemodellierung

**Datenquelle:** [Tankerkönig API](https://creativecommons.tankerkoenig.de/) (Open Data)

---

## Projektstruktur

```
spritpreisprognose/
├── data/
│   ├── raw/          # Rohdaten (nicht im Repo)
│   └── processed/    # Bereinigte Daten
├── notebooks/
│   └── tankstelle_analyse.ipynb   # Hauptanalyse
├── src/              # Python-Module (optional)
├── outputs/          # Plots & Exports
├── .env.example      # Vorlage für API Keys
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Installation

```bash
# Repo klonen
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose

# Virtuelle Umgebung erstellen & aktivieren
python -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen einrichten
cp .env.example .env
# .env mit API Key befüllen
```

---

## Verwendung

```bash
# Jupyter Notebook starten
jupyter notebook notebooks/tankstelle_analyse.ipynb
```

---

## Daten

Die Preisdaten stammen von der **Tankerkönig Open Data API** und stehen unter der Creative-Commons-Lizenz CC BY 4.0.

> Rohdaten sind nicht im Repository enthalten. API-Key unter [tankerkoenig.de](https://creativecommons.tankerkoenig.de/) beantragen und in `.env` eintragen.

---

## Ergebnisse

*Werden nach Abschluss der Analyse ergänzt.*

---

## Lizenz

MIT License — Felix Schrader, 2026
