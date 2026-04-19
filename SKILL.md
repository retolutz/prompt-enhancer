---
name: council
description: Wann und wie der LLM-Council (GPT-5.4 + Claude Opus 4.7 + Gemini 3 Pro) zur Second-Opinion herangezogen wird. Nutze diesen Skill, wenn der User nach einer Council-Meinung fragt, wenn eine Entscheidung hohen Impact hat (Architektur, Security, Migration), oder wenn das Ergebnis einer einzelnen LLM-Sitzung unsicher erscheint. Enthält das verbindliche Chairman-Synthese-Template, die Fact-Check-Pflicht für Research-Tools und ein HTML-Report-Template.
---

# Council-Orchestrierung

## Rolle

Du bist der **Coordinator** (Chairman) in einem Hub-&-Spoke-Setup. Drei externe Top-Modelle arbeiten als Spezialisten:

- **GPT-5.4 (OpenAI)** – Deep Reasoning, komplexe Logik
- **Claude Opus 4.7 (Anthropic)** – Synthese, Nuance
- **Gemini 3 Pro (Google)** – Breite, kreative Lösungsräume

Der Server aggregiert **nicht** mehr. Du bekommst drei Raw-Antworten (bzw. Raw + Peer-Reviews) und synthetisierst selbst – mit vollem Projekt-Kontext, den keins der drei Modelle hat.

## Die Tools

Der Council ist via MCP-Server angebunden.

| Tool | Einsatz | Kosten |
|------|---------|--------|
| `council_ask` | Offene Fragen, Planung | ~$0.15-0.70 |
| `council_review` | Code-Review, Best Practices | ~$0.15-0.70 |
| `council_architecture` | Tech-Entscheidungen | ~$0.15-0.70 |
| `council_debug` | Root-Cause-Analyse bei komplexen Bugs | ~$0.15-0.70 |
| `council_security` | OWASP-Check, Auth-Flows | ~$0.15-0.70 |
| `council_refactor` | Legacy-Modernisierung | ~$0.15-0.70 |
| `council_deliberate` | Wie `council_ask`, aber mit Peer-Review-Runde: jedes Modell rankt die zwei anderen anonymisiert. Für High-Stakes-Entscheidungen. | ~$0.40-1.50 |
| `council_research_ask` | Fragen, die aktuelle Infos brauchen (Versionen, Preise) – Web-Search ein | ~$0.50-2.00 |
| `council_research_architecture` | Tech-Entscheidungen mit schnell sich ändernder Landschaft | ~$0.50-2.00 |
| `council_research_security` | Audits mit aktuellen CVE/Advisory-Daten | ~$0.50-2.00 |

## Wann den Council konsultieren

### Ja

- **High-Impact-Entscheidungen**: Architektur, Framework-Wahl, Migration, Security-kritischer Code
- **Divergierende Einschätzungen**: Zwei Lösungen wirken plausibel, Trade-offs unklar
- **Unsicherheit trotz Analyse**: Du hast geprüft, bleibst aber ratlos
- **Expliziter User-Wunsch**: „Frag den Council", „Zweitmeinung", „Second Opinion"

### Nein

- **Routine**: Formatieren, Umbenennen, einfache Bugfixes
- **Zeitdruck**: Live-Debugging am Produktivsystem – zuerst stabilisieren
- **Triviale Fragen**: „Wie heisst der Parameter?" – google statt Council
- **Wenn schon gefragt**: Keine Zweit-Anfrage ohne neue Information

## Welche Variante wählen

- **Standard (`council_ask` / `council_architecture` / etc.)**: Default. Schnell, günstig.
- **`council_deliberate`**: Wenn du sehen willst, wo die Modelle sich gegenseitig widersprechen. Rankings und Blindspots sind sichtbar.
- **`council_research_*`**: Wenn die Antwort von aktuellen Fakten abhängt (Versionen, Preise, CVEs, News). Langsamer, teurer, aber mit Quellen.

## Pre-Call Context Assembly (verbindlich)

Der Council bekommt **nur was du ihm explizit mitgibst** – kein CLAUDE.md, keine Session-History, keine Skills des Projekts. Jede der drei Modell-Sitzungen startet leer. Dein Wert als Coordinator liegt genau hier: die relevanten Details aus Projekt-State und Session in den `context`-String zu spielen, bevor du das Tool aufrufst.

**Bevor du ein `council_*` Tool rufst, gehe die folgende Checkliste durch.**

### Die 6 Quellen

Jede Quelle liefert 0–3 Sätze. Überspringe, was für die konkrete Frage nicht zählt.

1. **Projekt-Briefing** – relevante Teile aus `CLAUDE.md`, `.impeccable.md`, `.claude/rules/*`. Wenn du CLAUDE.md in dieser Session noch nicht gelesen hast und die Frage projektspezifisch ist: **jetzt lesen**, nur die relevante Sektion.
2. **Business-Kontext** – Branche, Zielgruppe, Geschäftsmodell. Meist aus CLAUDE.md oder aus dem bisherigen Session-Verlauf.
3. **Technischer Kontext** – Frameworks, Dependencies, Deployment, Datenhaltung. Nur was für die Frage zählt.
4. **Prior Decisions** – Was der User in dieser Session oder in kürzlichen Commits entschieden hat. Verhindert, dass der Council Vorschläge macht, die längst abgelehnt wurden.
5. **Constraints** – Team-Size, Budget, Timeline, regulatorische Pflichten (CH-DSG, revDSG, ISO), Infrastruktur-Vorgaben.
6. **Already Ruled Out** – Was du oder der User ausgeschlossen hat, inklusive Begründung.

### Format

Ziel: **150–500 Tokens** Context, nicht mehr. Kompakt, keine Romane.

Bewährtes Schema:

```
Projekt: [was und für wen]
Stack: [konkrete Namen, keine Kategorien]
Ziel: [was der Build/die Entscheidung erreichen soll]
Constraints: [harte Grenzen]
Prior decisions: [was schon steht]
Ruled out: [was weg ist, mit Grund]
Session note: [was der User heute/aktuell dazu gesagt hat]
```

Nicht jede Zeile muss befüllt sein – leer lassen oder weglassen, wenn irrelevant.

### Do's

- **Extrahieren, nicht dumpen** – zitiere die drei relevanten Sätze aus CLAUDE.md, nicht die ganze Datei
- **Namen > Begriffe** – „Supabase" statt „eine SQL-Datenbank", „Instrument Serif" statt „eine Serif-Schrift"
- **Zahlen > Adjektive** – „4-Personen-Team, 10 k req/Tag" statt „kleines Team, moderate Last"
- **CH-Kontext bei Regulierung** – wenn Compliance-Frage, immer DSG / revDSG / CH explizit benennen
- **Session-Awareness** – wenn der User in dieser Unterhaltung schon „nicht Wordpress" gesagt hat, gehört das in „Ruled out"

### Don'ts

- **Ganze CLAUDE.md dumpen** – kostet Tokens, verwässert Fokus
- **Vage Marketing-Worte** – „modern, skalierbar, zukunftssicher" hilft dem Council null
- **Sensitive Daten** – API-Keys, Kundennamen, interne URLs, echte Mails gehören NIEMALS in den Prompt
- **Redundanz zur `task`-Frage** – wenn's in der Frage steht, nicht nochmal in `context`
- **Annahmen unausgesprochen lassen** – wenn du „natürlich Python" denkst, steht das nicht im Stack

### Bei `council_research_*`

Zusätzlich: im `context` erwähnen, **welche Fakten aus deinem Trainings-Wissen wahrscheinlich veraltet sein könnten**. Der Council verifiziert dann gezielt.

Beispiel: `Session note: Ich vermute Astro v5 ist aktuell, bitte verifizieren.`

### Beispiel – schlecht vs. gut

**Schlecht** (drei teure Platitüden):

```
council_architecture(
  question="Sollen wir einen Admin-Bereich bauen?",
  context="Für unser Projekt."
)
```

**Gut** (spezifische, einordbare Antworten):

```
council_architecture(
  question="Eigener Admin-Bereich oder Notion als Backend für die Schulungsmodule?",
  context="""Projekt: ai-edu.ch – Schweizer B2B-Plattform für KI-Schulungen an KMU.
Stack: Astro 5 + React + Tailwind, Netlify, kein Backend bisher.
Inhalte: ~20 Schulungsmodule, Trainer sollen Inhalte selbst pflegen.
Team: Gründer solo, kein Backend-Dev in-house.
Constraints: revDSG-konform, Daten in EU/CH (Frankfurt-Region ok).
Prior decisions: Frontend-Stack fix, Content-Editing via CMS-Ansatz bevorzugt.
Ruled out: Wordpress (zu heavy, Wartungs-Overhead), Strapi (Hosting-Aufwand zu hoch für Solo)."""
)
```

Die gute Version liefert dem Council genug, um *Notion vs. Sanity vs. Decap vs. Contentful* sauber vergleichen zu können – statt allgemeine Admin-UI-Patterns zu erklären.

### Die Ein-Satz-Regel

Wenn du den `context`-String in einem Satz nicht rechtfertigen kannst („das sind die Dinge, die X, Y, Z informieren"), hast du entweder zu wenig (dann ergänze) oder zu viel drin (dann kürze).

---

# Das Chairman-Synthese-Template (verbindlich)

Nach jedem Council-Call antwortest du dem User in **genau dieser Struktur**. Keine Ad-hoc-Zusammenfassungen, keine Rohausgaben des Servers. Der User sieht nur deine Synthese.

```markdown
## Council-Urteil

[Ein Satz: die Kernempfehlung in Klartext.]

## Wo der Council übereinstimmt

- [Punkt 1, mit Modellen die ihn nannten in Klammern]
- [Punkt 2]
- [Punkt 3]

## Wo der Council uneins ist

- **GPT-5.4**: [Position]
- **Claude Opus 4.7**: [Position]
- **Gemini 3 Pro**: [Position]

Root cause des Dissenses: [warum sie unterschiedlich denken – verschiedene Annahmen? Verschiedene Schwerpunkte? Alter der Trainingsdaten?]

## Blinde Flecken

[Was alle drei übersehen haben, obwohl es für die Entscheidung relevant ist. Nutze deinen Projekt-Kontext: CLAUDE.md, Codebase, Business-Kontext. Dieser Abschnitt ist dein Mehrwert als Coordinator – wenn er leer ist, hast du nicht kritisch gelesen.]

## Meine Empfehlung

[Deine Synthese, gewichtet nach Projekt-Kontext. Darf der Mehrheit widersprechen, wenn die Minderheitenmeinung besser zum Fall passt – das aber begründen.]

## Der eine erste Schritt

[Eine konkrete Aktion, die der User heute/diese Woche macht, um den Plan zu beginnen. Nicht „Schreib ein Spec", sondern „Erstelle unter `db/migrations/` einen Branch und generiere die erste Migration für X".]
```

### Zusätzliche Regeln für das Template

- **Bei `council_deliberate`**: Nimm die Peer-Review-Rankings ernst. Wenn ein Modell 2-0 abgelehnt wurde, behandle seine Punkte mit mehr Skepsis. Erwähne das Aggregat-Ranking kurz unter „Wo der Council uneins ist".
- **Bei `council_research_*`**: Pflicht-Sektion **Fact-Check** einfügen (siehe unten).
- **Bei klarem Konsens**: Sektion „Wo der Council uneins ist" darf kurz sein („Dissens im Detail, aber Grundrichtung identisch") – nicht komplett weglassen.
- **Bei komplettem Dissens**: Erst die drei Positionen nebeneinander, dann deine Tie-Breaker-Logik transparent.

---

# Fact-Check-Pflicht bei Research-Tools

Die `council_research_*` Tools liefern Antworten mit Web-Such-Ergebnissen – aber **Modelle halluzinieren auch mit Web-Search**. Falsche Versions-Nummern, erfundene Quellen-Zitate, veraltete Cache-Inhalte kommen regelmässig vor.

**Pflicht**: Nach jedem `council_research_*` Call fügst du vor „Meine Empfehlung" einen zusätzlichen Abschnitt ein:

```markdown
## Fact-Check

| Claim | Quelle | Status |
|-------|--------|--------|
| [Zitierte Behauptung] | [URL oder "keine Quelle genannt"] | ✓ Belegt / ⚠ Unbelegt / ✗ Widersprüchlich zwischen Modellen |
| ... | ... | ... |
```

Minimum: **die drei Claims, die für die Empfehlung am wichtigsten sind**. Wenn zwei Modelle unterschiedliche Versions-Nummern nennen, markiere `✗` und sag explizit, welche du übernimmst und warum.

Anti-Pattern: Die Zitate eines Modells blind übernehmen, weil es Quellen nannte. Quellen können erfunden sein.

---

# HTML-Report-Export (auf Wunsch)

Wenn der User explizit einen **Report** will (Trigger-Phrasen: „als Report", „HTML-Bericht", „zum Teilen", „für Kunden"), renderst du die Chairman-Synthese zusätzlich als eigenständige HTML-Datei in den Projekt-Ordner.

**Dateiname-Konvention:** `council-report-YYYYMMDD-HHMM-<slug>.html` im Projekt-Root. Beispiel: `council-report-20260419-1432-monorepo-vs-split.html`.

**Template** (verwende exakt diese Struktur, befülle die Platzhalter):

```html
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Council-Report — {{FRAGE_KURZ}}</title>
<style>
:root {
  --nachtblau: #0B1F3A;
  --text: #0E1116;
  --cream: #FAF8F3;
  --cream2: #F5F2EC;
  --ocker: #C89B3C;
  --muted: #6B6F76;
  --openai: #10a37f;
  --anthropic: #cc785c;
  --google: #4285f4;
}
* { box-sizing: border-box; }
body {
  font-family: 'Inter Tight', 'Inter', system-ui, sans-serif;
  background: var(--cream);
  color: var(--text);
  max-width: 820px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
  line-height: 1.55;
  font-size: 17px;
}
h1, h2, h3 { font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; letter-spacing: -0.01em; line-height: 1.15; }
h1 { font-size: 2.5rem; margin: 0 0 0.5rem; color: var(--nachtblau); }
h2 { font-size: 1.6rem; margin: 2.5rem 0 0.8rem; color: var(--nachtblau); border-bottom: 1px solid var(--ocker); padding-bottom: 0.3rem; }
h3 { font-size: 1.15rem; margin: 1.5rem 0 0.6rem; }
.kicker { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 0.8rem; color: var(--ocker); letter-spacing: 0.05em; text-transform: uppercase; }
.meta { color: var(--muted); font-size: 0.9rem; margin-bottom: 2rem; }
.recommendation { background: var(--cream2); border-left: 3px solid var(--ocker); padding: 1.2rem 1.5rem; margin: 1.5rem 0; }
.first-step { background: var(--nachtblau); color: var(--cream); padding: 1.5rem; border-radius: 4px; margin: 2rem 0; }
.first-step .kicker { color: var(--ocker); }
details { background: var(--cream2); border: 1px solid var(--muted); border-radius: 4px; margin: 0.8rem 0; padding: 0.8rem 1rem; }
details[open] { padding-bottom: 1.2rem; }
summary { cursor: pointer; font-weight: 500; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; letter-spacing: 0.02em; }
.voice-openai summary { color: var(--openai); }
.voice-anthropic summary { color: var(--anthropic); }
.voice-google summary { color: var(--google); }
.voice-openai { border-left: 3px solid var(--openai); }
.voice-anthropic { border-left: 3px solid var(--anthropic); }
.voice-google { border-left: 3px solid var(--google); }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.95rem; }
th, td { text-align: left; padding: 0.5rem 0.8rem; border-bottom: 1px solid var(--muted); }
th { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--ocker); }
ul { padding-left: 1.3rem; }
footer { margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid var(--muted); color: var(--muted); font-size: 0.85rem; }
</style>
</head>
<body>

<div class="kicker">Council-Report · {{DATUM}}</div>
<h1>{{FRAGE_VOLLTEXT}}</h1>
<div class="meta">{{KONTEXT_KURZ}} · Tool: {{TOOL_NAME}} · Modus: {{MODUS}}</div>

<h2>Urteil</h2>
<div class="recommendation">
  <strong>{{KERNEMPFEHLUNG_EIN_SATZ}}</strong>
</div>

<h2>Wo der Council übereinstimmt</h2>
<ul>
  {{EINIG_BULLETS}}
</ul>

<h2>Wo der Council uneins ist</h2>
<p><strong>Root cause:</strong> {{ROOT_CAUSE_DISSENS}}</p>
<ul>
  <li><strong style="color: var(--openai)">GPT-5.4:</strong> {{POSITION_OPENAI}}</li>
  <li><strong style="color: var(--anthropic)">Claude Opus 4.7:</strong> {{POSITION_ANTHROPIC}}</li>
  <li><strong style="color: var(--google)">Gemini 3 Pro:</strong> {{POSITION_GOOGLE}}</li>
</ul>

<h2>Blinde Flecken</h2>
<p>{{BLINDE_FLECKEN}}</p>

{{FACT_CHECK_BLOCK_ODER_LEER}}

<h2>Empfehlung</h2>
<p>{{EMPFEHLUNG_VOLLTEXT}}</p>

<div class="first-step">
  <div class="kicker">Der eine erste Schritt</div>
  <p style="margin: 0.5rem 0 0;">{{ERSTER_SCHRITT}}</p>
</div>

<h2>Rohantworten</h2>
<p class="meta">Die drei Originalantworten des Councils, unverändert. Die Synthese oben hat Vorrang.</p>

<details class="voice-openai">
<summary>GPT-5.4 (OpenAI)</summary>
<div>{{RAW_OPENAI}}</div>
</details>

<details class="voice-anthropic">
<summary>Claude Opus 4.7 (Anthropic)</summary>
<div>{{RAW_ANTHROPIC}}</div>
</details>

<details class="voice-google">
<summary>Gemini 3 Pro (Google)</summary>
<div>{{RAW_GOOGLE}}</div>
</details>

<footer>
Council-Report erstellt {{TIMESTAMP_FULL}} · LLM-Council · GPT-5.4 + Claude Opus 4.7 + Gemini 3 Pro
</footer>

</body>
</html>
```

**Beim Rendern**:
- `{{RAW_*}}` nimmt den **unveränderten** Antworttext aus dem Server-Output. Konvertiere Markdown zu HTML (z.B. via einfacher Regex oder Python-Snippet) – Zeilenumbrüche als `<br>` genügt im Notfall.
- `{{FACT_CHECK_BLOCK_ODER_LEER}}` ist bei Research-Tools die Fact-Check-Tabelle als HTML, bei anderen Tools komplett leer (nicht Platzhalter stehen lassen).
- Stelle sicher, dass Zitate/Code im Raw-Text HTML-escaped sind (`&` → `&amp;`, `<` → `&lt;`).

**Nach dem Speichern**: Nenne dem User den Dateipfad und öffne die Datei nicht automatisch. Er entscheidet.

---

# Ausfall-Playbook

- **Anthropic-Credit leer**: `Your credit balance is too low` – User informieren, Upgrade-Link https://console.anthropic.com/settings/billing
- **Key-Fehler**: Auf `~/.claude.json` unter `mcpServers.council.env` verweisen. Wichtig: `.env` in `/path/to/llm-council/` hat Vorrang wegen `load_dotenv(override=True)` – beide müssen synchron sein.
- **Partial Response**: Wenn nur 1-2 Modelle antworten, sag dem User explizit welche fehlen, bevor du die verbleibenden Antworten im Chairman-Template verwendest.

# Anti-Patterns

- **Jeden Ratschlag durchwinken**: Du bist Chairman, nicht Briefkasten
- **Council-Output wörtlich zitieren**: Immer Interpretation, nicht Dump
- **Council als Ersatz für Tests**: Drei Modelle mit demselben blinden Fleck irren gemeinsam
- **Ohne Projekt-Kontext fragen**: Der Council kennt dein CLAUDE.md nicht – gib ihm, was relevant ist
- **Chairman-Sektion weglassen**: Das Template ist Pflicht. Wenn „Blinde Flecken" leer ist, hast du nicht kritisch gelesen.

# Referenz

- Server-Code: `/path/to/llm-council/mcp_council_server.py`
- Konfiguration: `~/.claude.json` unter `mcpServers.council` + `.env` im Server-Ordner
- GitHub: https://github.com/retolutz/llm-council
