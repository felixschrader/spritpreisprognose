# Speaker Card - DSI Live Call (10:00, Deutsch)

Nutze das als Live-Spickzettel (zweiter Screen).

---

## 0:00-0:30 - Einstieg

**Sagen:**
"Wir zeigen heute unser Capstone-MVP zur kurzfristigen Dieselpreisprognose fuer eine lokale Station in Koeln.  
Unser Fokus ist die Entscheidungskette von verrauschten Daten zu einem robusten ML-Signal und einer nutzbaren Live-Darstellung."

**Ziel:** Rahmen setzen, Sicherheit ausstrahlen.

---

## 0:30-1:50 - Kontext + Problem

**Sagen:**
"Das Umsetzungsfenster fuer den Prototyp lag bei etwa zwei Wochen.  
Deshalb haben wir auf Robustheit und Produktionsfaehigkeit optimiert, nicht auf theoretische Vollstaendigkeit.  
Rohpreise sind stark verrauscht durch Tageszyklen und lokale Wettbewerbsreaktionen."

**Ankerbegriffe:** 2-Wochen-MVP, Rauschen, lokale Konkurrenz.

---

## 1:50-3:30 - ML-Einfuehrung: Kernpreis-Idee (dein Hauptteil)

**Sagen:**
"Statt die rohen Minutenpreise direkt zu modellieren, definieren wir einen taeglichen Kernpreis-Proxy.  
Wir aggregieren stuendlich, nutzen das stabile Fenster 13:00-20:00 und nehmen P10 als konservativen Tages-Proxy."

**Einzeiler:** "Weniger Rauschen, bessere Vergleichbarkeit, besseres Zielsignal."

---

## 3:30-4:50 - Target-Design (iterative Suche)

**Sagen:**
"Wir haben mehrere Horizont- und Shift-Varianten systematisch getestet und die Zielvariable mit dem besten Kompromiss aus Signalqualitaet und Robustheit gewaehlt.  
Final: rollierendes 3-Tage-Delta mit 2-Tage-Shift."

**Bei Rueckfrage warum:** "Diese Definition war in unserem Datensetting stabiler als einfache Tagesdeltas."

---

## 4:50-6:20 - Modell + Evaluation

**Sagen:**
"Als finales Modell nutzen wir Random Forest als robusten MVP-Kompromiss.  
Der Train/Test-Split ist zeitlich, um Leakage zu vermeiden.  
Die Metriken verstehen wir als Entscheidungshilfe, nicht als exakten Punktpreis fuer jede Minute."

**Kurzmetriken parat:** Richtung ~67,9%, MAE ~0,89 ct, R2 ~0,30.

---

## 6:20-7:30 - Uebergabe an Teamkolleg:in

**Uebergabesatz:**
"Ich uebergebe jetzt an [Name] fuer den operativen Teil: automatisierte Updates, Inference-Pipeline und Dashboard-Integration."

---

## 7:30-8:50 - Block Teamkolleg:in (du: Zeitwache)

**Deine Aufgabe:** Auf Zeit achten.  
Wenn noetig bei 8:40 sagen: "Dann direkt zum Schlussfazit."

---

## 8:50-10:00 - Abschluss + Fragen

**Sagen:**
"Das Ergebnis ist ein robustes MVP unter realistischen Zeitbedingungen, mit klarer Skalierungslogik: mehr Stationen, E5/E10 und staerkere Wettbewerbsdynamik.  
Wir freuen uns auf Fragen zur Modelllogik oder zur produktiven Architektur."

---

## 20-Sekunden-Notfallkuerzung (wenn ihr hinter der Zeit seid)

"Kernbotschaft: Wir haben verrauschte Intraday-Preise in ein robustes Kernpreis-Ziel ueberfuehrt, die Zielvariable iterativ bestimmt und das Ganze end-to-end mit Automatisierung und Dashboard produktionsnah umgesetzt."

---

## Schnelle Q&A-Antworten

- **Warum Random Forest?**  
  "Bester praktischer Kompromiss im MVP: robust, ausreichend interpretierbar, gute Richtungsqualitaet."

- **Warum P10 und 13:00-20:00?**  
  "Empirisch das stabilste Fenster; reduziert Morgenspike-Rauschen und verbessert Vergleichbarkeit."

- **Ist das ein finales Marktmodell?**  
  "Nein, es ist ein MVP-Entscheidungsunterstuetzungssystem mit produktionsnaher Automatisierung."
