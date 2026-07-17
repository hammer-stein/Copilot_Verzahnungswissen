# Verzahnungs-Copilot — Design System

A design system for the **KI-Copilot für Verzahnungswissen** — an AI-assisted copilot
for engineers, researchers and students working on gear manufacturing & engineering
(*Verzahnungstechnik*) at the **Karlsruher Institut für Technologie (KIT)**.

The product is a strict-RAG copilot: it answers technical questions **only** from uploaded
reference documents (PDFs, datasheets, standards) and the geometric metadata of a concrete
component (parsed from STEP 242 / CAD files). Every statement is traceable to a source.

> **Audience:** domain experts. The interface must be **data-dense, functional and highly
> professional** — academic seriousness and engineering precision over decoration.

---

## Sources used to build this system

This system was derived from the project's repository. Explore it further to build more
faithful designs:

- **GitHub:** `hammer-stein/Copilot_Verzahnungswissen` — https://github.com/hammer-stein/Copilot_Verzahnungswissen
  - `frontend/index.html` — the original (Pico.css) prototype UI
  - `rag_system_prompt.md` — full system specification, answer logic, frontend spec
  - `schemas/gears.yaml` — gear metadata schema (filter fields)
  - `README.md` — architecture & API endpoints

The brand direction (KIT corporate design: clean whitespace, anthracite text, KIT green
`#009682` as the single accent, crisp/square forms) was supplied by the project owner. The
original prototype used Pico.css with a blue accent — this system **supersedes** it with a
KIT-aligned, engineering-grade visual language.

> **Design decisions** (confirmed for this university project — no external brand kit exists):
> - **Fonts** are loaded from the Google Fonts CDN (`Inter`, `JetBrains Mono`) — the
>   chosen, technical, freely-licensed typefaces. To self-host for offline builds later,
>   drop the woff2 files in and swap the `@import` for local `@font-face` rules.
> - **Icons** — **Lucide** (1.5px stroke, geometric) is the system's icon set, picked for
>   engineering precision (the original prototype had only the `📄` emoji).
> - **Logo** — an **original product wordmark** (gear mark + "Verzahnungs-Copilot"). This is
>   the project's own mark and is *not* the KIT institutional logo.

---

## Domain vocabulary (use the real terms)

The product speaks German engineering. Designs and copy should use the actual domain terms:

- **Verzahnungstypen:** Stirnrad, Schrägverzahnung, Kegelrad, Schneckenrad, Innenverzahnung
- **Parameter:** Modul (mm), Zähnezahl, Eingriffswinkel (°), Schrägungswinkel (°),
  Profilverschiebung (x), Teilkreis-/Kopfkreis-/Fußkreisdurchmesser (mm), Zahnbreite (mm)
- **Werkstoffe:** 16MnCr5, 20MnCr5, 42CrMo4, C45 · **Härte:** vergütet, einsatzgehärtet, nitriert
- **Verzahnungsqualität:** DIN-Klasse 6–8 · **Normen:** DIN 3960, ISO 1328
- **Themenkategorien:** Geometrie, Festigkeit, Fertigung, Werkstoff, Prüfung, Wirtschaftlichkeit
- **Ausgabeformate:** kurz, standard, ausführlich, stichpunkte, tabellarisch
- **Quellen / Citations:** inline markers `[Q1]`, `[Q2]` → file + page + similarity score

---

## CONTENT FUNDAMENTALS

**Voice:** professional, objective, precise, solution-oriented. The copilot is a *technical
assistant*, not a chatbot personality. No small talk, no exclamation marks, no hype.

**Language:** German (the domain is German engineering). UI labels, buttons and system
copy are German. Technical terms and standards keep their canonical spelling
(*Schrägverzahnung*, *DIN 3960*, *16MnCr5*).

**Person / address:** The system addresses the user formally and sparingly. Prefer
**imperative, neutral instructions** over "you" phrasing — e.g. *"PDF hochladen"*,
*"Frage stellen"*, *"Andere Werte würfeln"*. Microcopy is terse: *"Bitte pro Feld nur eine
Frage."*

**Casing:** Sentence case for UI labels and buttons (*"Zufälliges Zahnrad generieren"*).
Section/overline labels may be UPPERCASE with wide tracking (*"BAUTEILDATEN"*). Never
Title Case Every Word.

**Honesty / grounding (core to the brand):** the assistant must never bluff. When a source
is missing it says so explicitly: *"Aus den verfügbaren Quellen lässt sich dazu keine Aussage
treffen."* Every factual claim carries a `[Q#]` citation. This epistemic discipline is a
**brand value**, not just a feature — surface sources prominently, never hide them.

**Numbers & units:** always show units (`mm`, `°`). Use tabular figures for parameters.
Decimal comma is acceptable in prose (German) but the data panels use the schema's raw
values. Similarity scores show 3 decimals (`0.847`).

**Emoji:** avoid. The original prototype used `📄`; replace with a Lucide file icon. No
emoji in product copy.

**Tone examples**
- Button: *"Fragen stellen"* (not "Los geht's!")
- Empty state: *"Noch keine Dokumente indexiert. PDF hochladen, um die Wissensbasis aufzubauen."*
- Status: *"Indexiert · 142 Chunks"* · *"Fehler beim Einlesen"*
- Citation row: *"[Q1] DIN3960_Auszug.pdf — Seite 12 — Similarity 0.847"*

---

## VISUAL FOUNDATIONS

**Overall feel:** clean, white, instrument-panel precision. Think CAD software meets a
well-set academic paper. High information density without clutter; whitespace does the
separating, not heavy borders or shadows.

**Color.** A near-monochrome anthracite/neutral base with **one** accent — KIT green
`#009682`. Green is reserved for primary actions, active states, focus, citations and the
brand mark; it is never used decoratively. Semantic colors (blue = info/data, amber =
warning/tolerance, red = out-of-spec/error) appear only to carry meaning. Backgrounds are
flat — **no gradients**, no tints except the faint green citation/active wash.

**Type.** `Inter` for all UI and prose; `JetBrains Mono` for parameters, code, formulas and
citations. The scale is compact (UI body 14px) and uses tabular figures throughout so
parameter columns align. Headings are semibold with slightly tight tracking; overline
labels are uppercase 11–12px with wide tracking.

**Spacing.** 4px base grid. Dense but breathable — controls are 36px tall, list rows compact.
Panels separated by 1px hairlines (`--border-default`) and whitespace rather than cards
floating on cards.

**Corners.** Crisp. Controls and inputs `4px`, cards/panels `6px`, nothing larger than `8px`
except pills (badges, chips). This communicates engineering exactness; avoid soft/round.

**Borders & shadows.** Borders carry most of the structure — 1px hairlines in a neutral
ramp. Shadows are tight and low-spread (`--shadow-sm`/`--shadow-md`), used only for raised
surfaces (dropdowns, dialogs, toasts). No glow, no large blurry drop shadows.

**Backgrounds.** Flat surfaces. App background is a very light neutral (`--surface-app`),
cards/chat are pure white. No imagery, patterns or textures behind content. The only
"texture" is the optional faint technical drawing/diagram in the right inspector panel.

**Cards.** White surface, 1px `--border-default`, `6px` radius, `--shadow-sm` at most. Headers
use an overline label or a strong title; bodies are generously padded (16–20px).

**Animation.** Minimal and functional. Fades and short slides (120–260ms) on the standard
easing curve; **no bounce, no spring, no infinite loops**. Loading uses a calm pulsing/
spinner indicator. Respect `prefers-reduced-motion`.

**Hover / press.** Hover = subtle surface shift (`--surface-hover`) or one step darker accent
(`--accent-hover`). Press = next step darker (`--accent-active`); no scale/shrink toy effects.
Focus = 3px soft green ring (`--ring`). Disabled = reduced opacity + `not-allowed`.

**Transparency / blur.** Used sparingly — overlay scrims behind dialogs, and an optional
backdrop blur on the sticky composer. Not used decoratively.

**Layout rules (the copilot shell).**
- **Left sidebar** (`268px`): chat history + document/Wissensbasis management. Collapsible.
- **Main column**: the chat transcript, max readable width, with a sticky composer at the
  bottom. AI answers must cleanly render **code, formulas, tables (Schnittwerte/Toleranzen)
  and citations**.
- **Right inspector** (`360px`, expandable): technical drawings, parameter panels, diagrams
  and metadata for the current Verzahnung — opens without losing chat context.

**Dark mode.** A genuine high-contrast dark theme (`[data-theme="dark"]`) for monitor work
in workshops/labs. Anthracite-black surfaces, green steps up to `--green-300` for accents so
it stays legible. All tokens have dark equivalents; components must read from the semantic
aliases (never hard-code hex).

---

## ICONOGRAPHY

The repository had **no icon system** — the only glyph was the `📄` emoji in the document
list. For this system we adopt **[Lucide](https://lucide.dev)** (geometric, 1.5px stroke,
open-source) as the closest match to the brand's engineering precision. Load from CDN
(`lucide@latest`) and render via `data-lucide="<name>"` + `lucide.createIcons()`.

- **Stroke / style:** outline, 1.5px stroke, 20–24px box in the UI, 16px inline.
- **Color:** inherit `currentColor`; muted (`--text-muted`) by default, accent on active.
- **No emoji** in product UI. **No Unicode glyphs** as icons.
- **Common icons:** `file-text` (document), `upload`, `trash-2`, `cog`/`settings`,
  `message-square` (chat), `panel-right` (inspector), `quote`/`book-open` (sources),
  `table`, `sigma` (formula), `circle-gauge` (parameters), `plus`, `search`, `sun`/`moon`.
- The **product logo** is an original gear mark (`assets/logo-mark.svg`) — a precise
  involute-gear silhouette in KIT green, paired with the wordmark.

If you have a house icon set, replace Lucide and update this section.

---

## INDEX / MANIFEST

Root:
- `styles.css` — global entry point (link this one file). Imports all tokens + fonts + base.
- `readme.md` — this guide.
- `SKILL.md` — Kurzreferenz des Design-Systems für automatisierte Editor-Werkzeuge.

Tokens (`tokens/`):
- `fonts.css` · `colors.css` · `typography.css` · `spacing.css` · `base.css`

Assets (`assets/`):
- `logo-mark.svg`, `logo-lockup.svg` — product gear mark + wordmark.

Foundation cards (`guidelines/`): Type, Colors, Spacing/Radii/Shadow specimens
(rendered in the Design System tab).

Components (`components/`) — 14 primitives, read from `window.VerzahnungsCopilotDesignSystem_c9990b`:
- `forms/` — **Button**, **IconButton**, **Input**, **Textarea**, **Select**
- `data-display/` — **Badge**, **Card**, **Tabs**, **Spinner**, **StatusBadge**
- `copilot/` — **Citation**, **SourceRow**, **ParameterTable**, **CodeBlock**

Each directory has a `@dsCard` demo (Components group), and components carry `.d.ts` +
`.prompt.md`. Component styling lives in `components/components.css` (`vc-` classes,
shipped via `styles.css`). Starting points: the Copilot app, Button, Badge.

UI kit (`ui_kits/copilot/`): high-fidelity click-through recreation of the copilot
(left sidebar + chat transcript with grounded/cited answers + right inspector), composed
from the component primitives. Entry: `ui_kits/copilot/index.html`.
