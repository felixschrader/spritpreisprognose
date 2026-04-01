# UI strings for scripts/dashboard.py (Deutsch / English)

TANKERKOENIG_URL = "https://www.tankerkoenig.de"
TANKERKOENIG_CC_URL = "https://creativecommons.tankerkoenig.de"

# Team (Social-Leiste im Dashboard — Namen/Links zentral)
SOCIAL_TEAM = {
    "felix": {
        "name": "Felix Schrader",
        "linkedin": "https://www.linkedin.com/in/felixschrader/",
    },
    "girandoux": {
        "name": "Girandoux Fandio Nganwajop",
        "linkedin": "https://www.linkedin.com/in/girandoux-fandio-08628bb9/",
    },
    "ghislain": {
        "name": "Ghislain Djifag Wamo",
        "linkedin": (
            "https://www.linkedin.com/search/results/all/"
            "?keywords=Ghislain%20Djifag%20Wamo"
        ),
    },
}


def messages(lang: str) -> dict:
    return MESSAGES["en"] if lang == "en" else MESSAGES["de"]


def methodology_html(lang: str, ml_acc: float, ml_base: float, ml_delta: float) -> str:
    if lang == "en":
        return f"""
        <p>Model: Random Forest Regressor (scikit-learn)
        · Target: change in rolling 3-day core price, 2-day horizon
        · <strong>Offline test (notebook, sign):</strong> directional accuracy <strong>{ml_acc:.1f} %</strong>
        · naive “always zero” baseline: <strong>{ml_base:.1f} %</strong> (= share of test days with target ≤ 0; not a fixed 50 % coin flip)
        · model edge: <strong>+{ml_delta:.1f}</strong> percentage points
        · “flat” band in dashboard log: ±0.5 ct · training window: 2019–2023</p>
        <p><strong>Statistics:</strong> The baseline reflects the <em>target distribution</em> in the test set (period in metadata). Skewed targets → low baselines; balanced targets → near 50 %. Retro KPIs in the tab use ±0.5 ct bucketing — see README (Evaluation).</p>
        <p><strong>Forecast &amp; overview:</strong>
        Anchor is the <strong>core price of the last completed day</strong> — usually <strong>yesterday</strong>. Direction refers to the <strong>core-price level</strong> (3-day smoothing as in training), not the spot price “right now”.
        The <strong>orange line</strong> applies the model <strong>direction</strong> for the <strong>next opening day</strong> so that per hour bin the gap between <strong>core price (P10, 1pm–8pm)</strong> and <strong>daily high</strong> scales like yesterday — not from min/max of 3h bins alone.</p>
        <p><strong>Data updates (GitHub Actions):</strong>
        The <strong>short-term forecast</strong> updates <strong>hourly</strong>.
        The <strong>daily forecast</strong> (model direction, orange line) is built <strong>once per day</strong> at <strong>09:00 UTC</strong> (e.g. <strong>10:00 CET</strong>); until then there may be <strong>no new</strong> daily values on GitHub.
        <strong>“Refresh”</strong> in the app only clears the app cache. If daily values look stale, run the workflow manually under <em>Actions → Run workflow</em> or wait for the next run.</p>
        <p><strong>Stack:</strong>
        ML: scikit-learn (Random Forest as above). Data:
        <a href="{TANKERKOENIG_URL}" target="_blank" rel="noopener noreferrer">Tankerkönig</a> / MTS-K; daily pipeline via GitHub Actions; app on Streamlit Community Cloud; map with OpenStreetMap (Leaflet). More detail: <a href="https://github.com/felixschrader/dieselpreisprognose" target="_blank" rel="noopener noreferrer">README on GitHub</a>.</p>
        <p><strong>AI in development:</strong>
        <a href="https://cursor.com" target="_blank" rel="noopener noreferrer">Cursor</a> and <a href="https://www.anthropic.com/claude-code" target="_blank" rel="noopener noreferrer">Claude Code</a> were used primarily for dashboard implementation, Plotly styling, CI/CD configuration, and editorial drafting. Domain analysis, feature design, target-definition, model comparison, evaluation methodology, and accountability remain with the team.</p>
        <p><strong>AI copy:</strong> the short text above is generated with <a href="https://www.anthropic.com" target="_blank" rel="noopener noreferrer">Claude</a> from price, yesterday’s average, model direction, and Brent context (Brent as a market reference, no regional station comparison).</p>
        <p>This project was created in the six-month Data Science professional programme; the capstone was built 16–27 March 2026.
        The dashboard is an MVP prototype and open to extension with further drivers of retail fuel pricing.</p>
        """
    return f"""
        <p>Modell: Random Forest Regressor (scikit-learn)
        · Zielvariable: Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage
        · <strong>Offline-Test (Notebook, Vorzeichen):</strong> Richtungs-Accuracy <strong>{ml_acc:.1f} %</strong>
        · naive Baseline „immer 0“: <strong>{ml_base:.1f} %</strong> (= Anteil Tage mit Ziel ≤ 0 im Test; kein fester 50-%-Zufallswert)
        · Vorteil Modell: <strong>+{ml_delta:.1f}</strong> Prozentpunkte
        · Schwelle &quot;stabil&quot; (Dashboard-Log): ±0.5 Cent · Trainingsperiode: 2019–2023</p>
        <p><strong>Statistische Einordnung:</strong> Die Baseline spiegelt die <em>Verteilung der Zielvariable</em> im Test (Zeitraum siehe Metadaten). Schiefe Verteilungen ergeben niedrige Baselines; ausgewogene Ziele ergeben Werte nahe 50 %. Retrograde KPIs im Tab nutzen eine ±0,5-ct-Klassierung — siehe README (Evaluation).</p>
        <p><strong>Prognose &amp; Übersicht:</strong>
        Basis ist der <strong>Kernpreis des letzten abgeschlossenen Tages</strong> — praktisch meist <strong>gestern</strong>. Die Richtung bezieht sich auf die <strong>Kernpreis-Ebene</strong> (3-Tage-Glättung wie im Training), nicht auf den Minutenpreis „gerade jetzt“.
        Die <strong>orange Linie</strong> im Chart setzt die Modell-<strong>Richtung</strong> für den <strong>nächsten Öffnungstag</strong> so um, dass pro Uhrzeit-Bin der Abstand zwischen <strong>Kernpreis (P10, 13–20 Uhr)</strong> und <strong>Tageshoch</strong> wie gestern skaliert wird — nicht über das Min/Max der 3h-Bins.</p>
        <p><strong>Daten-Updates (GitHub Actions):</strong>
        Die <strong>Kurzprognose</strong> wird <strong>stündlich</strong> erzeugt.
        Die <strong>Tagesprognose</strong> (Modellrichtung, orange Linie) wird <strong>einmal täglich</strong> um <strong>09:00&nbsp;UTC</strong> gebaut (z.&nbsp;B. <strong>10:00&nbsp;Uhr MEZ</strong>); dazwischen gibt es dafür oft <strong>keinen neuen Stand</strong> auf GitHub.
        <strong>„Aktualisieren“</strong> im Dashboard leert nur den App-Cache. Wenn die Tageswerte „hängen“, die Action im Repo unter <em>Actions → Run workflow</em> manuell starten oder auf den nächsten Lauf warten.</p>
        <p><strong>Technik:</strong>
        ML-Stack: scikit-learn (Random Forest wie im ersten Absatz). Daten:
        <a href="{TANKERKOENIG_URL}" target="_blank" rel="noopener noreferrer">Tankerkönig</a> / MTS-K; tägliche Pipeline über GitHub Actions; Dashboard auf Streamlit Community Cloud; Standortkarte mit OpenStreetMap (Leaflet). Weitere technische Details und Repo-Aufbau: <a href="https://github.com/felixschrader/dieselpreisprognose" target="_blank" rel="noopener noreferrer">README im GitHub-Repository</a>.</p>
        <p><strong>KI bei der Entwicklung:</strong>
        <a href="https://cursor.com" target="_blank" rel="noopener noreferrer">Cursor</a> und <a href="https://www.anthropic.com/claude-code" target="_blank" rel="noopener noreferrer">Claude Code</a> wurden primär für Dashboard-Implementierung, Plotly-Styling, CI/CD-Konfiguration und Textredaktion eingesetzt. Domänenanalyse, Feature-Design, Zielvariablen-Wahl, Modellvergleich, Evaluation-Methodik und die inhaltliche Verantwortung liegen beim Team.</p>
        <p><strong>KI-Text:</strong> der Kurztext darüber wird mit <a href="https://www.anthropic.com" target="_blank" rel="noopener noreferrer">Claude</a> aus Preis, Mittelwert gestern, Modellrichtung und Brent-Referenz formuliert (Brent als Marktbegriff, ohne Regionalvergleich).</p>
        <p>Dieses Projekt entstand im Rahmen der sechsmonatigen Weiterbildung Data Science; die Abschlussarbeit wurde in der Zeit vom 16. bis 27. März 2026 erstellt.
        Es wendet erlernte Tools und Denkweisen bewusst in der Praxis an.
        Das Dashboard ist ein MVP im Sinne eines Prototyps und offen für eine Weiterentwicklung, die weitere Zusammenhänge in der Preisfindung von Kraftstoffpreisen einbeziehen kann.</p>
        """


MESSAGES = {
    "de": {
        "topbar_title": "Dieselpreisprognose",
        "topbar_live": "Live ·",
        "topbar_refresh": "↺ Aktualisieren",
        "topbar_aral_link": "bei aral.de",
        "section_glance": "Auf einen Blick",
        "card_avg_yesterday": "Ø gestern",
        "card_current": "Aktueller Preis ·",
        "card_model_dir": "Tagesmodell · Kernpreis-Richtung",
        "vs_avg_yesterday": "ct vs. Ø gestern",
        "unchanged_tpl": "Unveraendert seit {mins} Min. · typisch hier: ~{typ} Min.",
        "unchanged_short": "Unveraendert seit {mins} Min.",
        "badge_fill_now": "Jetzt tanken",
        "badge_wait": "Warten",
        "badge_flexible": "Flexibel",
        "badge_hold": "Abwarten",
        "ki_footer": "Text mit Claude erzeugt ·",
        "section_location": "Standort",
        "map_station_line": "ARAL Dürener Str. 407 · 50858 Köln ·",
        "map_fs": "Vollbild",
        "map_fs_exit": "Vollbild beenden",
        "map_marker": "ARAL Tankstelle",
        "map_aria": "Karte Standort Tankstelle",
        "tab_price": "Preisverlauf",
        "tab_kpi": "KPIs",
        "tab_perf": "Modell-Performance",
        "tab_eda": "EDA-Insights",
        "pv_section": "Preisverlauf — 7 Tage + Prognose bis morgen",
        "pv_brent_toggle": "Brent-Preis anzeigen",
        "pv_brent_cap": "Brent-Quelle:",
        "pv_brent_last": "Letzter Stand:",
        "pv_brent_none": "Keine Daten verfügbar",
        "legend_diesel": "Preisverlauf Diesel",
        "legend_brent": "Brent in Euro pro Barrel",
        "legend_day_avg": "Tages-Ø",
        "legend_forecast": "Prognose",
        "yaxis_diesel": "Preisverlauf Diesel",
        "yaxis_brent": "Brent in Euro pro Barrel",
        "kpi_section": "Analyse — letzte 14 Tage (ohne heute)",
        "kpi_chg_lbl": "Ø Änderungen/Tag (14T)",
        "kpi_vol_lbl": "Ø Volatilität/Tag (14T)",
        "kpi_mc_lbl": "Ø Morning−Closing (14T)",
        "kpi_avg_price_lbl": "Ø Preis ({d} Tage)",
        "kpi_cheap_h": "Guenstigste Stunde",
        "kpi_exp_h": "Teuerste Stunde",
        "kpi_vol_std": "Volatilitaet (Stdabw.)",
        "kpi_cap_range": "Zeitraum **{a}** bis **{b}** (ohne heute) — gleicher Fenster für alle drei Tagesdiagramme.",
        "kpi_sec_chg": "Änderungen pro Tag — täglich",
        "kpi_sec_vol": "Tägliche Preisvolatilität — ganzer Tag",
        "kpi_sec_mc": "Abstand Morning-Spike − Closing — täglich",
        "kpi_legend_chg": "Ändg/Tag",
        "kpi_hover_chg": "%{x|%d.%m.%Y}<br>Anzahl: %{y}<extra></extra>",
        "kpi_legend_vol": "Volatilität",
        "kpi_hover_vol": "%{x|%d.%m.%Y}<br>σ: %{y:.1f} ct<extra></extra>",
        "kpi_legend_mc": "Morning − Closing",
        "kpi_hover_mc": "%{x|%d.%m.%Y}<br>Abstand: %{y:.1f} ct<extra></extra>",
        "perf_section": "Retrograde Bewertung — Tages-Prognose",
        "perf_cap": """**Zielvariable:** Δ gleitender 3-Tage-Kernpreis, Horizont 2 Tage.
Kernpreis = p10 der Stundenbins 13–20 Uhr.
**Richtung korrekt (hier)** = Predicted und Actual auf **derselben Seite** der **±0,5‑ct-Schwelle** (drei Klassen: auf / ab / Band) — **nicht** identisch mit der strengen Vorzeichen-Accuracy im Notebook (dort: y>0 vs. y_pred>0, ohne Band).
**MAE** = durchschnittliche Abweichung Predicted vs. Actual in Cent.
**Test-Set im Notebook** (Vorzeichen, siehe README): Modell **{acc:.1f} %**, naive Baseline „immer 0“ **{base:.1f} %** (= Anteil Testtage mit y ≤ 0).""",
        "perf_no_log": "Noch keine Log-Daten verfügbar.",
        "perf_acc_3w": "Richtungs-Acc. (3W)",
        "perf_ok_3w": "Korrekt / 3W",
        "perf_mae_3w": "MAE (3W)",
        "perf_acc_nb": "Acc. Test-Set (NB)",
        "perf_baseline": "Baseline Richtung",
        "perf_cal_title": "Prognose-Trefferquote — letzte 4 Kalenderwochen (inkl. laufende Woche)",
        "perf_cal_cap": "Grün = Richtung korrekt · Rot = falsch · P = predicted Δ · A = actual Δ · Schwelle: ±0.5 ct (nur Tage mit Log-Eintrag)",
        "cal_weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "perf_weekly_title": "Wöchentliche Trefferquote — 3 vollständige Kalenderwochen (Mo–So)",
        "perf_pred_actual_title": "Predicted vs. Actual Delta — letzte 14 Tage (Cent)",
        "perf_trace_pred": "Prognose",
        "perf_trace_act": "Ist",
        "perf_hover_pred": "%{x|%d.%m.%Y}<br>Prognose: %{y:.1f} ct<extra></extra>",
        "perf_hover_act": "%{x|%d.%m.%Y}<br>Ist: %{y:.1f} ct<extra></extra>",
        "perf_band_cap": "Grauer Bereich = ±0,5 ct Stabilitätsschwelle",
        "perf_bar_hover": "Trefferquote",
        "perf_bar_days": "Tage",
        "eda_main_title": "EDA-Insights — Explorative Analyse",
        "eda_no": "Keine EDA-Daten verfuegbar.",
        "eda_slider": "EDA-Zeitraum (Tage)",
        "eda_empty": "Keine Daten im gewaehlten EDA-Zeitraum.",
        "eda_t1": "Zeitmuster",
        "eda_t2": "Verteilung",
        "eda_t3": "Wochenvergleich",
        "eda_cap_hour": "Durchschnittspreis nach Stunde",
        "eda_cap_day": "Tagesmittel (Trend)",
        "eda_cap_box": "Preisverteilung pro Stunde (Boxplot)",
        "eda_cap_hist": "Histogramm (Preisverteilung)",
        "eda_cap_wd": "Durchschnitt nach Wochentag",
        "eda_cap_heat": "Heatmap: Wochentag x Stunde",
        "eda_axis_hour": "Stunde",
        "eda_axis_day": "Tag",
        "eda_axis_price": "Preis",
        "eda_axis_count": "Anzahl",
        "eda_hover_price": "Preis",
        "eda_hover_hour": "Stunde %{x}:00<br>Preis %{y:.3f} €<extra></extra>",
        "eda_hover_day": "%{x|%d.%m.%Y}<br>Preis %{y:.3f} €<extra></extra>",
        "eda_hover_heat": "Tag %{y}<br>Stunde %{x}:00<br>Preis %{z:.3f} €<extra></extra>",
        "eda_trace_price": "Preis",
        "meth_summary": "Methodik & Projekt",
        "social_github": "GitHub",
        "footer_price": "Preisinformationen:",
        "footer_cc": "Quelle: MTS-K (Markttransparenzstelle für Kraftstoffe)",
        "footer_dsi": "Capstone Projekt 2026",
        "opening": [
            ("Mo – Fr", "06:00 – 21:30"),
            ("Sa", "07:00 – 21:00"),
            ("So", "07:00 – 21:00"),
        ],
    },
    "en": {
        "topbar_title": "Diesel price forecast",
        "topbar_live": "Live ·",
        "topbar_refresh": "↺ Refresh",
        "topbar_aral_link": "on aral.de",
        "section_glance": "At a glance",
        "card_avg_yesterday": "Avg yesterday",
        "card_current": "Current price ·",
        "card_model_dir": "Daily model · core-price direction",
        "vs_avg_yesterday": "ct vs. avg yesterday",
        "unchanged_tpl": "Unchanged for {mins} min · typical here: ~{typ} min.",
        "unchanged_short": "Unchanged for {mins} min.",
        "badge_fill_now": "Refuel now",
        "badge_wait": "Wait",
        "badge_flexible": "Flexible",
        "badge_hold": "Hold off",
        "ki_footer": "Text generated with Claude ·",
        "section_location": "Location",
        "map_station_line": "ARAL Dürener Str. 407 · 50858 Cologne ·",
        "map_fs": "Fullscreen",
        "map_fs_exit": "Exit fullscreen",
        "map_marker": "ARAL station",
        "map_aria": "Map: station location",
        "tab_price": "Price chart",
        "tab_kpi": "KPIs",
        "tab_perf": "Model performance",
        "tab_eda": "EDA insights",
        "pv_section": "Price — 7 days + forecast through tomorrow",
        "pv_brent_toggle": "Show Brent price",
        "pv_brent_cap": "Brent source:",
        "pv_brent_last": "Last update:",
        "pv_brent_none": "No data available",
        "legend_diesel": "Diesel price",
        "legend_brent": "Brent (EUR per barrel)",
        "legend_day_avg": "Daily average",
        "legend_forecast": "Forecast",
        "yaxis_diesel": "Diesel price",
        "yaxis_brent": "Brent (EUR/bbl)",
        "kpi_section": "Analysis — last 14 days (excl. today)",
        "kpi_chg_lbl": "Avg changes/day (14d)",
        "kpi_vol_lbl": "Avg volatility/day (14d)",
        "kpi_mc_lbl": "Avg morning−closing (14d)",
        "kpi_avg_price_lbl": "Avg price ({d} days)",
        "kpi_cheap_h": "Cheapest hour",
        "kpi_exp_h": "Priciest hour",
        "kpi_vol_std": "Volatility (stdev)",
        "kpi_cap_range": "Period **{a}** to **{b}** (excluding today) — same window for all three daily charts.",
        "kpi_sec_chg": "Changes per day",
        "kpi_sec_vol": "Daily price volatility — full day",
        "kpi_sec_mc": "Morning spike − closing gap — daily",
        "kpi_legend_chg": "Chg/day",
        "kpi_hover_chg": "%{x|%d.%m.%Y}<br>Count: %{y}<extra></extra>",
        "kpi_legend_vol": "Volatility",
        "kpi_hover_vol": "%{x|%d.%m.%Y}<br>σ: %{y:.1f} ct<extra></extra>",
        "kpi_legend_mc": "Morning − closing",
        "kpi_hover_mc": "%{x|%d.%m.%Y}<br>Gap: %{y:.1f} ct<extra></extra>",
        "perf_section": "Retrospective — daily forecast",
        "perf_cap": """**Target:** change in rolling 3-day core price, 2-day horizon.
Core price = P10 of hourly bins 1pm–8pm.
**Direction correct (here)** = predicted and actual on the **same side** of the **±0.5 ct band** (three classes) — **not** the strict sign accuracy in the notebook (y>0 vs. y_pred>0, no band).
**MAE** = mean absolute error of predicted vs. actual in cents.
**Notebook test set** (sign, see README): model **{acc:.1f} %**, naive “always zero” baseline **{base:.1f} %** (= share of test days with y ≤ 0).""",
        "perf_no_log": "No log data available yet.",
        "perf_acc_3w": "Dir. accuracy (3W)",
        "perf_ok_3w": "Correct / 3W",
        "perf_mae_3w": "MAE (3W)",
        "perf_acc_nb": "Test acc. (NB)",
        "perf_baseline": "Direction baseline",
        "perf_cal_title": "Forecast hit rate — last 4 calendar weeks (incl. current week)",
        "perf_cal_cap": "Green = direction correct · Red = wrong · P = predicted Δ · A = actual Δ · band: ±0.5 ct (logged days only)",
        "cal_weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "perf_weekly_title": "Weekly hit rate — 3 full calendar weeks (Mon–Sun)",
        "perf_pred_actual_title": "Predicted vs. actual delta — last 14 days (cents)",
        "perf_trace_pred": "Predicted",
        "perf_trace_act": "Actual",
        "perf_hover_pred": "%{x|%d.%m.%Y}<br>Predicted: %{y:.1f} ct<extra></extra>",
        "perf_hover_act": "%{x|%d.%m.%Y}<br>Actual: %{y:.1f} ct<extra></extra>",
        "perf_band_cap": "Grey band = ±0.5 ct stability band",
        "perf_bar_hover": "Hit rate",
        "perf_bar_days": "days",
        "eda_main_title": "EDA insights — exploratory analysis",
        "eda_no": "No EDA data available.",
        "eda_slider": "EDA window (days)",
        "eda_empty": "No data in the selected EDA window.",
        "eda_t1": "Time patterns",
        "eda_t2": "Distribution",
        "eda_t3": "Week comparison",
        "eda_cap_hour": "Average price by hour",
        "eda_cap_day": "Daily mean (trend)",
        "eda_cap_box": "Price distribution by hour (box plot)",
        "eda_cap_hist": "Histogram (price distribution)",
        "eda_cap_wd": "Average by weekday",
        "eda_cap_heat": "Heatmap: weekday × hour",
        "eda_axis_hour": "Hour",
        "eda_axis_day": "Date",
        "eda_axis_price": "Price",
        "eda_axis_count": "Count",
        "eda_hover_price": "Price",
        "eda_hover_hour": "Hour %{x}:00<br>Price %{y:.3f} €<extra></extra>",
        "eda_hover_day": "%{x|%d.%m.%Y}<br>Price %{y:.3f} €<extra></extra>",
        "eda_hover_heat": "Day %{y}<br>Hour %{x}:00<br>Price %{z:.3f} €<extra></extra>",
        "eda_trace_price": "Price",
        "meth_summary": "Methodology & project",
        "social_github": "GitHub",
        "footer_price": "Price data:",
        "footer_cc": "Source: MTS-K (German fuel market transparency)",
        "footer_dsi": "Capstone project 2026",
        "opening": [
            ("Mon – Fri", "06:00 – 21:30"),
            ("Sat", "07:00 – 21:00"),
            ("Sun", "07:00 – 21:00"),
        ],
        "weekday_short": {
            "Monday": "Mon",
            "Tuesday": "Tue",
            "Wednesday": "Wed",
            "Thursday": "Thu",
            "Friday": "Fri",
            "Saturday": "Sat",
            "Sunday": "Sun",
        },
    },
}
