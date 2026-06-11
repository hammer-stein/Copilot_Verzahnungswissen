---
name: verzahnungs-copilot-design
description: Use this skill to generate well-branded interfaces and assets for the Verzahnungs-Copilot (KI-Copilot für Verzahnungswissen, KIT) — for production or throwaway prototypes/mocks. Contains essential design guidelines, KIT-aligned colors, type, fonts, assets, and UI-kit components for prototyping gear-engineering copilot UIs.
user-invocable: true
---

Read the `readme.md` file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and
create static HTML files for the user to view. If working on production code, copy assets and
read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or
design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_
production code, depending on the need.

## Map
- `readme.md` — full design guide: product context, content fundamentals, visual
  foundations, iconography, and a file manifest. **Start here.**
- `styles.css` — single entry point; link it to get every token + font + component style.
- `tokens/` — colors (KIT green `#009682` + anthracite neutrals, light + dark), typography
  (Inter / JetBrains Mono), spacing, radii, shadows, base element styles.
- `components/` — React primitives (Button, IconButton, Input, Select, Textarea, Badge,
  Card, Tabs, Spinner, StatusBadge, and copilot-specific Citation, SourceRow,
  ParameterTable, CodeBlock). Each has a `.d.ts`, a `.prompt.md`, and a `@dsCard` demo.
- `guidelines/` — foundation specimen cards (Type, Colors, Spacing, Brand).
- `ui_kits/copilot/` — full click-through recreation of the RAG copilot app.
- `assets/` — product gear-mark logo (mark + lockup).

## Brand in one paragraph
Academic seriousness + engineering precision. Clean white UI, lots of whitespace, anthracite
text, KIT green as the single accent. Crisp forms (4–6px radii), tight shadows, hairline
borders. Inter for UI/prose, JetBrains Mono with tabular figures for parameters and code.
German domain language. Every AI statement is source-cited (`[Q#]`) — honesty is a brand
value. Genuine high-contrast dark mode for monitor work in labs/workshops.
