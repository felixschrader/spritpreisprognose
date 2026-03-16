# Spritpreisprognose

Analyse und Prognose von Kraftstoffpreisen an deutschen Tankstellen — Abschlussprojekt der [Data Science Institute](https://data-science-institute.de/) Weiterbildung (6 Monate Data Science).

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

**Datenquellen:**
- [Tankerkönig API](https://creativecommons.tankerkoenig.de/) (Open Data) — Kraftstoffpreise deutscher Tankstellen
- [FRED API](https://fred.stlouisfed.org/) — Brent-Rohölpreis (DCOILBRENTEU)

---

## Projektstruktur
```
spritpreisprognose/
├── .github/
│   └── workflows/
│       └── update_brent_prices.yml   # GitHub Actions: tägliches Brent-Update
├── data/
│   ├── raw/          # Rohdaten (nicht im Repo)
│   ├── processed/    # Bereinigte Daten
│   └── brent_prices.csv              # Automatisch aktualisiert via GitHub Actions
├── notebooks/
│   └── tankstelle_analyse.ipynb      # Hauptanalyse
├── plots/
│   └── brent_prices.html             # Interaktiver Brent-Preisverlauf
├── src/              # Python-Module (optional)
├── brent_price.py                    # Brent-Datenabruf & Verarbeitung
├── .env.example      # Vorlage für API Keys
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Team

| Name | GitHub |
|------|--------|
| Felix Schrader | [@felixschrader](https://github.com/felixschrader) |
| Girandoux Fandio Nganwajop | [@Girandoux](https://github.com/Girandoux) |
| Ghislain Wamo | [@GhislainWamo](https://github.com/GhislainWamo) |

---

## Installation
```bash
# Repo klonen
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose

# Virtuelle Umgebung erstellen & aktivieren
python -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen einrichten
cp .env.example .env
# .env mit API Keys befüllen
```

---

## Verwendung
```bash
# Jupyter Notebook starten
jupyter notebook notebooks/tankstelle_analyse.ipynb

# Brent-Preise manuell abrufen
python brent_price.py
```

---

## Daten

Die Kraftstoffpreisdaten stammen von der **Tankerkönig Open Data API** (CC BY 4.0). Der Brent-Rohölpreis wird täglich automatisch via GitHub Actions von der FRED API abgerufen.

> Rohdaten sind nicht im Repository enthalten. Tankerkönig API-Key unter [tankerkoenig.de](https://creativecommons.tankerkoenig.de/) beantragen und in `.env` eintragen.

---

## Ergebnisse

*Werden nach Abschluss der Analyse ergänzt.*

---

## Lizenz

MIT License — Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo, 2026