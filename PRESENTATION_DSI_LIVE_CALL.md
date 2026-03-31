# Abschlusspräsentation — DSI Live Call

**Termin:** Donnerstag, 10:50 Uhr (Live Call mit Teamkolleg:in)  
**Projekt:** Spritpreisprognose — MVP Kurzfristprognose Diesel (Köln)  
**Ziel:** In **genau 10 Minuten** den ML-Ansatz klar und verständlich präsentieren.

---

## Zeitbudget (fix: 10 Minuten)

| Block | Min. | Inhalt |
|-------|------|--------|
| Einstieg | 0:40 | Kontext + Ziel in einem Satz |
| Problem & Datenrealität | 1:20 | Warum Rohpreise schwierig sind |
| ML-Idee: Kernpreis-Proxy | 1:40 | 13:00–20:00, P10, Nutzen |
| Target-Design (iterative Suche) | 1:20 | Horizon/Shift-Logik |
| Modell & Evaluation | 2:00 | RF + zentrale Kennzahlen |
| Produktion (kurz) | 1:20 | Actions, Inference, Artefakte |
| Dashboard (1 Screen) | 1:00 | Was Nutzer sehen |
| Schluss | 1:00 | MVP-Status + Ausblick + Frage |
| **Gesamt** | **10:00** | ohne Zeitpuffer |

**Sprechregel:** Bei 8:30 schon bei „Produktion“ sein, sonst Folie Dashboard nur 20 Sekunden.

---

## Rollen (2 Personen, ML-Fokus für dich)

**Person A (du):** ML-Einführung, Methodik, Kernpreis, Target-Design, Modell-Evaluation  
**Person B:** ETL/Automation, Dashboard-Demo, Ausblick

*Tauscht die Blöcke bei Bedarf — wichtig ist, dass jede:r mindestens einen eigenen Block hat.*

---

## Folienstruktur (10-Minuten-Version, ML-zuerst)

### Folie 1 — Titel
- **Titel:** Kurzfristige Dieselpreisprognose — MVP mit ML & Streamlit  
- **Untertitel:** Capstone Project 2026 · Data Science Institute  
- **Team:** [Namen]  
- **Station:** ARAL Dürener Str. 407, Köln  

### Folie 2 — Kontext
- 6-monatiges DSI-Programm; **Umsetzungsfenster für den Prototyp: ca. 2 Wochen**  
- Ziel: **robuste, erklärbare** Kurzfristprognose, nicht „perfektes“ Marktmodell  
- Fokus aktuell: **Diesel** — perspektivisch andere Kraftstoffe / Stationen  

### Folie 3 — Problem
- Rohpreise: starke **Tageszyklen**, lokale Konkurrenz, viel Rauschen  
- Frage: Wie bekommen wir ein **stabiles Zielsignal** und ein **nutzbares** Forecasting?  

### Folie 4 — Lösungsidee: Kernpreis (1 Satz)
- Stundenweise Aggregation → Fenster **13:00–20:00** (stabiler) → **P10** als Tages-Kernpreis-Proxy  
- *Kernaussage:* Vergleichbar über Tage, weniger Spike-Rauschen  

### Folie 5 — ML-Einführung (dein Kernslide)
- Problem in ML-Sprache: verrauschtes Signal, nichtstationäres Verhalten, starke Intraday-Muster
- Unser Lösungsweg: robustes Target statt roher Preisvorhersage
- Modellziel: nutzbare Richtungs-/Trendunterstützung statt exaktem Punktwert für jede Minute

### Folie 6 — Modellierung (kurz)
- Zielvariable iterativ gesucht (Horizont / Shift): z. B. **roll3_shift2** auf dem Kernpreis  
- Modell: **Random Forest** (guter Kompromiss für MVP)  
- Split: **zeitlich** (kein zufälliges Mischen)  

### Folie 7 — Ergebnisse (ehrlich)
- Beispiel-Kennzahlen aus dem Projekt nennen (Richtungstreu, MAE, R²) — **als Entscheidungshilfe**, nicht als „exakter Preis morgen“  
- Optional: ein Satz zu Pass-through / Residuum als **Struktursignale**, ohne Overclaim  

### Folie 8 — Produktion & Automation
- **GitHub Actions:** Datenupdates (Tankstellen, Brent, FX, Wetter, Kalender, …) + **Inference**  
- Artefakte in `data/ml/`, Skripte in `scripts/inference`, `scripts/features`, `scripts/pipeline`  

### Folie 9 — Dashboard (Streamlit)
- KPIs, Prognose, Performance-Ansicht  
- **Anthropic** für erklärenden Text (optional erwähnen)  
- **OpenStreetMap** für Kartenkontext  

### Folie 10 — Was wir bewusst nicht modelliert haben
- z. B. vollständige **Edgeworth-Zyklen** / detaillierte Wettbewerbsreaktionen / Margen — **Ausblick**  

### Folie 11 — Ausblick & Danke
- Mehr Kraftstoffe, mehr Stationen, stärkere Wettbewerbslogik  
- Danke + **Fragen**  

---

## Sprechertext (kurz, 10-Minuten-tauglich)

**Einleitung (A, 20-30s):**  
„Wir zeigen heute unser Capstone: eine **Kurzfristprognose für Diesel** an einer konkreten Station in Köln. Wichtig ist uns die **Kette von Daten über ein robustes Zielsignal bis zur live nutzbaren Oberfläche** — im Rahmen eines MVP.“

**ML-Einstieg (A, 45s):**  
„ML-seitig war unsere Hauptfrage: Wie vermeiden wir, dass das Modell nur Intraday-Rauschen lernt? Deshalb haben wir zuerst ein robusteres Zielsignal definiert.“

**Kernpreis (A, 45s):**  
„Statt jedes Sekundenpreis-Rauschen zu modellieren, nutzen wir einen **Kernpreis-Proxy**: stabilisiertes Tagesfenster und P10, damit das Modell **über Tage vergleichbar** bleibt.“

**Target + Modell (A, 60-75s):**  
„Die Zielvariable haben wir **iterativ** gegen alternative Horizonte getestet. Als Modell nutzen wir einen **Random Forest** — gut interpretierbar und robust genug für den Prototyp.“

**Produktion (B, 40-50s):**  
„Das läuft nicht nur lokal: **GitHub Actions** aktualisiert Daten und schreibt Prognosen regelmäßig ins Repo — das Dashboard liest diese Artefakte ein.“

**Abschluss (A, 30s):**  
„Wir positionieren das bewusst als **MVP mit klarer Erweiterungslogik** — nächste Schritte wären weitere Kraftstoffe und stärkere lokale Wettbewerbsmodellierung.“

---

## Checkliste am Mittwoch Abend

- [ ] Streamlit-App einmal frisch öffnen (kein Secret-Fehler)  
- [ ] Ein **Backup-Screenshot** der wichtigsten Dashboard-Ansicht (falls Live-Demo hakt)  
- [ ] Klären: Wer teilt Bildschirm? Wer moderiert Chat/Fragen?  
- [ ] Link zum Repo / zur App in Chat bereitlegen  

---

## Link zur ausführlicheren Doku

- Technische README: `README.md`  
- Präsentations-Variante mit Executive Summary: `README_presentation.md`  

---

*Viel Erfolg beim DSI Live Call.*
