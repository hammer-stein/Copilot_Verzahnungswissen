/* Right inspector panel: technical drawing, parameter table, metadata JSON. */
function Inspector({ gear, hasPart = true, onClose }) {
  const { Tabs, ParameterTable, CodeBlock, Badge } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [tab, setTab] = React.useState('zeichnung');

  /* No CAD/STEP part analysed yet — show an empty state instead of placeholders. */
  if (!hasPart) {
    return (
      <aside className="vc-inspector">
        <div className="vc-inspector__head">
          <span className="vc-inspector__title">Inspektor</span>
          <button className="vc-inspector__close" onClick={onClose} aria-label="Schließen"><Icon name="x" size={16} /></button>
        </div>
        <div className="vc-inspector__body">
          <div className="vc-drawing">
            <Icon name="box" size={40} style={{ color: 'var(--text-faint)' }} />
            <div className="vc-drawing__label">Kein Bauteil geladen</div>
            <div className="vc-drawing__sub">STEP-/CAD-Datei hochladen, um Bauteildaten anzuzeigen</div>
          </div>
        </div>
      </aside>
    );
  }

  const rows = [
    { key: 'Verzahnungstyp', value: gear.verzahnungstyp, unit: '' },
    { key: 'Modul', value: gear.modul, unit: 'mm' },
    { key: 'Zähnezahl', value: gear.zaehnezahl, unit: '' },
    { key: 'Eingriffswinkel', value: gear.eingriffswinkel, unit: '°' },
    { key: 'Schrägungswinkel', value: gear.schraegungswinkel, unit: '°' },
    { key: 'Profilverschiebung', value: gear.profilverschiebung, unit: 'x' },
    { key: 'Teilkreis d', value: gear.teilkreis, unit: 'mm' },
    { key: 'Kopfkreis dₐ', value: gear.kopfkreis, unit: 'mm' },
    { key: 'Fußkreis d_f', value: gear.fusskreis, unit: 'mm' },
    { key: 'Zahnbreite b', value: gear.zahnbreite, unit: 'mm' },
  ];
  const json = `{
  "verzahnungstyp": "${gear.verzahnungstyp}",
  "modul": ${gear.modul.replace(',', '.')},
  "zaehnezahl": ${gear.zaehnezahl},
  "eingriffswinkel": ${gear.eingriffswinkel.replace(',', '.')},
  "werkstoff": "${gear.werkstoff}",
  "haerte": "${gear.haerte}",
  "verzahnungsqualitaet": ${gear.qualitaet}
}`;

  return (
    <aside className="vc-inspector">
      <div className="vc-inspector__head">
        <span className="vc-inspector__title">Inspektor</span>
        <Badge variant="accent">{gear.verzahnungstyp}</Badge>
        <button className="vc-inspector__close" onClick={onClose} aria-label="Schließen"><Icon name="x" size={16} /></button>
      </div>
      <div className="vc-inspector__tabs">
        <Tabs value={tab} onChange={setTab} items={[
          { id: 'zeichnung', label: 'Zeichnung' },
          { id: 'parameter', label: 'Parameter' },
          { id: 'meta', label: 'Metadaten' },
        ]} />
      </div>
      <div className="vc-inspector__body">
        {tab === 'zeichnung' && (
          <div>
            <div className="vc-drawing">
              <Icon name="circle-gauge" size={40} style={{ color: 'var(--text-faint)' }} />
              <div className="vc-drawing__label">Technische Zeichnung</div>
              <div className="vc-drawing__sub">STEP 242 · Schnittansicht — Platzhalter</div>
            </div>
            <div className="vc-inspector__caption">Quelle: {gear.verzahnungstyp.toLowerCase()}_z{gear.zaehnezahl}.stp</div>
          </div>
        )}
        {tab === 'parameter' && (
          <div>
            <div className="vc-inspector__sectlbl">Geometrie &amp; Werkstoff</div>
            <ParameterTable rows={rows} />
            <div className="vc-inspector__chips">
              <Badge variant="success">{gear.haerte}</Badge>
              <Badge square variant="neutral">DIN-Qualität {gear.qualitaet}</Badge>
              <Badge variant="info">{gear.werkstoff}</Badge>
            </div>
          </div>
        )}
        {tab === 'meta' && (
          <div>
            <div className="vc-inspector__sectlbl">CAD-Metadaten (JSON)</div>
            <CodeBlock caption="cad_metadata.json">{json}</CodeBlock>
          </div>
        )}
      </div>
    </aside>
  );
}
Object.assign(window, { Inspector });
