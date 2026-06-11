# UI Kit — Verzahnungs-Copilot (RAG App)

High-fidelity, click-through recreation of the copilot's main view, composed from the
design-system component primitives. It is a faithful KIT-branded reimagining of the
original `frontend/index.html` (which was a bare Pico.css prototype), structured per the
product spec in `rag_system_prompt.md` §11.

## Layout (the three-pane copilot shell)
- **Left sidebar** (`Sidebar.jsx`) — brand, "Neue Konversation", chat history grouped by
  day, and the **Wissensbasis** document list with indexing status.
- **Main column** — `TopBar.jsx` (active component context + theme/inspector toggles),
  `ChatView.jsx` (transcript of user questions and grounded AI answers with inline
  `[Q#]` citations, source accordion, parameter tables and code/formula blocks), and the
  sticky `Composer.jsx` (question field, CAD attach, format select, strict-RAG note).
- **Right inspector** (`Inspector.jsx`) — expandable panel with tabs *Zeichnung /
  Parameter / Metadaten*; shows the technical-drawing placeholder, gear `ParameterTable`,
  and the raw `cad_metadata.json` — without losing chat context.

## Interactions (mocked)
- Send a question → loading state → a grounded, fully-cited answer is appended.
- Click suggestion chips on the empty state.
- Toggle **dark mode** (workshop/lab use) and toggle the inspector.
- Switch inspector tabs; expand "Quellen anzeigen" under any answer.
- Responsive: sidebar and inspector collapse to overlays on narrow widths.

## Files
`index.html` (entry + mount) · `data.js` (mock domain data) · `ui.jsx` (Icon/Logo) ·
`Sidebar.jsx` · `TopBar.jsx` · `ChatView.jsx` · `Composer.jsx` · `Inspector.jsx` ·
`App.jsx` · `kit.css` (shell layout).

Components are read from the compiled bundle via
`window.VerzahnungsCopilotDesignSystem_c9990b`. Icons are Lucide (CDN).

> This is a cosmetic recreation for design reference — not production code. Data is mock.
