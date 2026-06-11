Form primitives — use for any input surface in the copilot (composer, parameter editor, upload dialogs).

```jsx
<Button variant="primary" iconLeft={<Icon/>}>Fragen stellen</Button>
<Button variant="secondary" size="sm">Würfeln</Button>
<IconButton title="Inspector" active><PanelIcon/></IconButton>
<Input label="Modul (mm)" mono defaultValue="2.5" />
<Select label="Ausgabeformat" options={['kurz','standard','ausführlich']} />
<Textarea label="Frage 1" hint="Bitte pro Feld nur eine Frage." />
```

- `Button` variants: `primary` (KIT green, one per view), `secondary`, `ghost`, `danger`; sizes `sm|md|lg`.
- `IconButton` for toolbars/row-actions; always pass `title` (a11y).
- `Input mono` for numeric/parameter entry (tabular figures).
- `Select` takes `options` as strings or `{value,label}`.
