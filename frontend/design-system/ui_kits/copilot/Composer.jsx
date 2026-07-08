/* Sticky composer: question field + format select + send. Strict-RAG note. */
function Composer({ onSend, format, onFormat, formats, onUploadStep }) {
  const { IconButton, Select } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [value, setValue] = React.useState('');
  const taRef = React.useRef(null);
  const fileRef = React.useRef(null);

  const pickFile = () => { if (fileRef.current) fileRef.current.click(); };
  const onFile = (e) => {
    const f = e.target.files && e.target.files[0];
    if (f && onUploadStep) onUploadStep(f);
    e.target.value = '';
  };

  const submit = () => {
    const v = value.trim();
    if (!v) return;
    onSend(v);
    setValue('');
    if (taRef.current) taRef.current.style.height = 'auto';
  };
  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };
  const autosize = (e) => {
    setValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  return (
    <div className="vc-composer">
      <div className="vc-composer__box">
        <div className="vc-composer__row">
          <input ref={fileRef} type="file" accept=".step,.stp,.stp242,.p21,.iges,.igs,.json,.csv,.xlsx,.xls,model/step,application/json,text/csv" style={{ display: 'none' }} onChange={onFile} />
          <button className="vc-composer__attach" title="CAD- / STEP- / JSON- / CSV-Datei anhängen" onClick={pickFile}>
            <Icon name="plus" size={20} />
          </button>
          <textarea
            ref={taRef}
            className="vc-composer__input"
            placeholder="Fachfrage zur Verzahnung stellen…"
            value={value}
            onChange={autosize}
            onKeyDown={onKey}
            rows={1}
          />
          <button className="vc-composer__send" onClick={submit} disabled={!value.trim()} aria-label="Frage stellen">
            <Icon name="arrow-up" size={19} />
          </button>
        </div>
        <div className="vc-composer__meta">
          <div className="vc-composer__format">
            <span className="vc-composer__fmtlabel">Format</span>
            <Select options={formats} value={format} onChange={(e) => onFormat(e.target.value)} style={{ height: 28, fontSize: 12.5 }} />
          </div>
          <div className="vc-composer__note">
            <Icon name="shield-check" size={12} style={{ color: 'var(--accent-text)' }} />
            Striktes RAG — nur indexierte Quellen
          </div>
        </div>
      </div>
    </div>
  );
}
Object.assign(window, { Composer });
