Copilot-specific primitives — render grounded AI answers with full source traceability.

```jsx
<div>…Einsatzstähle wie 16MnCr5 <Citation qid={1}/>. Härte 58–62 HRC <Citation qid={2}/>.</div>
<SourceRow qid={1} source="DIN3990.pdf" page={42} similarity={0.871} />
<ParameterTable rows={[{key:'Modul', value:'2,500', unit:'mm'}]} />
<CodeBlock caption="cad_metadata.json">{json}</CodeBlock>
```

- Append `<Citation qid={n}/>` to **every** factual statement (brand value: nothing un-sourced).
- `SourceRow` populates the "Quellen anzeigen" accordion: file + page + similarity (3 decimals).
- `ParameterTable` right-aligns mono/tabular values with a unit column — use for gear params & tolerances.
- `CodeBlock` for JSON metadata, formulas and code; pass `caption` for a labelled header bar.
