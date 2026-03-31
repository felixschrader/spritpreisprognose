# KI-Prompt: Abschlusspräsentation (DSI Capstone 2026)

Kopiere den folgenden Block in dein bevorzugtes KI-Tool (ChatGPT, Claude, Gemini, etc.) und ergänze ggf. Slot-Dauer und persönliche Präferenzen in eckigen Klammern.

---

```
Du bist ein erfahrener Präsentationscoach und Fachexperte für Data Science / ML-Produktentwicklung.

Aufgabe: Erstelle eine strukturierte Abschlusspräsentation (Folien + Sprechernotizen) für ein DSI-Capstone-Projekt.

## Projektkontext
- Programm: 6-monatiges Data-Science-Weiterbildungsprogramm am Data Science Institute (DSI), Berlin. Link Institut: https://data-science-institute.de/
- Projekttyp: MVP / Prototyp mit produktionsnaher Automatisierung
- Umsetzungsfenster für den Prototyp: ca. 2 Wochen (bewusst knapp; Fokus auf Robustheit, Deployability, Erklärbarkeit)
- Team: Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo
- Live-Dashboard (Streamlit): https://spritpreisprognose.streamlit.app
- Repository: https://github.com/felixschrader/spritpreisprognose

## Literatur (einheitlich im README)
- Wissenschaft: Bacon (1991) Rockets & Feathers; Frondel et al. (2021) deutsche Märkte
- Datenrecht: Tankerkönig / MTS-K unter CC BY 4.0
- Ordner `papers/` (PDFs mit Titel/Autor/Jahr im README): u. a. Schwarz (2022) Branchenuntersuchung Kraftstoffmarkt; Wilhelm (2019) Price Matching and Edgeworth Cycles (SSRN 2708630); Legner (2014) Freilaw; Golem-Artikel ML/Benzinpreise; Devoteam Expert Views — vollständige Tabelle siehe README Abschnitt „Literatur“

## Zielgruppe der Präsentation
- Fahrer:innen / kurzfristige Kaufentscheidungen (Nutzenstory)
- Stakeholder, die praktischen Mehrwert und Risiken einschätzen
- technisches Publikum, das End-to-End-ML (Daten → Modell → Deployment) erwartet

## Kernfrage (Leitfrage)
Wie lässt sich eine robuste, nachvollziehbare Kurzfristprognose für Kraftstoffpreise bauen, obwohl Rohdaten intraday stark verrauscht sind, Tageszyklen dominieren und lokale Wettbewerbsdynamik die Preisbildung mitprägt?

## Argumentationskette (Methodik)
1) Problem: Rohpreise (hochfrequent) sind für Modellierung als „exakter Minutenpreis“ ungeeignet → zu viel Rauschen, starke Zyklen.
2) Lösung: Definition eines täglichen Kernpreis-Proxys:
   - Stundenaggregation (Median pro Stunde)
   - stabiles Fenster 13:00–20:00 Uhr
   - P10 über dieses Fenster als konservativer Tages-Proxy
3) Zusätzliche ökonomische Struktur (ohne Overclaim):
   - Pass-through (Öl/Währung → lokaler Kernpreis)
   - Residuum-Persistenz (Station vs. Markt)
   - Kein finaler kausaler Nachweis von Rockets-and-Feathers im MVP; Evidenzmuster, vertiefbar.
4) Zielvariable: iterative Suche über Horizont/Shift; finales Beispiel roll3_shift2 auf rollierendem 3-Tage-Kernpreis mit Shift.
5) Modell: Random Forest Regressor als robuster MVP-Kompromiss; zeitlicher Train/Test-Split.
6) Evaluation: Richtungsgenauigkeit, MAE, R² — als Entscheidungsunterstützung, nicht als „perfekter Punktpreis pro Minute“.
7) Produktion: GitHub Actions für Datenupdates und Inference; Artefakte in data/ml/; Dashboard in Streamlit; Textgenerierung optional via Anthropic; Kartenkontext OpenStreetMap.

## Was bewusst nicht im MVP-Anspruch enthalten ist
- Vollständige Abbildung von Edgeworth-Zyklen / detaillierte lokale Reaktionsketten aller Konkurrenten
- Margen-/Kundenbindungsmodellierung
- Perspektivisch: weitere Kraftstoffe (E5/E10), weitere Stationen, erweiterte Wettbewerbslogik

## Deliverables von dir
- Folienstruktur mit klaren Überschriften (Deutsch)
- Pro Folie: 3–5 Stichpunkte + 2–4 Sätze Sprechertext
- Eine kurze „Executive Summary“-Folie am Anfang
- Eine „Demo/Hinweis“-Folie mit Link zum Streamlit-Dashboard
- Abschluss: Ausblick + Q&A-Vorschläge

## Stilvorgaben
- Sprache: Deutsch, sachlich, präsentationstauglich, nicht übertrieben marketinglastig
- Dauer: [10 Minuten Vortrag / oder: ___ Minuten] — daran die Folienanzahl anpassen
- Keine erfundenen Kennzahlen; wenn Zahlen genannt werden, nur als Beispiel aus dem Projekt (Richtung Test z. B. ~68 %, naive Baseline „immer 0“ entspricht dem Anteil Tage mit Ziel ≤ 0 im Test — oft ~49 %, nicht fest 50 %; MAE Test ~0,9 ct, R² ~0,39) und als „MVP-Stand“ kennzeichnen

Bitte liefere das Ergebnis als nummerierte Folienliste mit Sprechernotizen.
```

---

*Diese Datei gehört zum Repository und kann bei Bedarf angepasst werden (Dauer, Ton, zusätzliche Quellen aus `papers/`).*
