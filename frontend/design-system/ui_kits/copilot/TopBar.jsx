/* Top bar: active component context, theme toggle, inspector toggle. */
function TopBar({ gear, dark, onToggleTheme, inspectorOpen, onToggleInspector, onToggleSidebar }) {
  const { IconButton, Badge } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const text = (value) => {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch (e) {
        return String(value);
      }
    }
    return String(value);
  };
  // Leere/„—"-Werte werden gar nicht als Chip angezeigt (z.B. Werkstoff fehlt bei reinen Geometrie-STEPs).
  const has = (value) => value !== null && value !== undefined && String(value).trim() !== '' && String(value).trim() !== '—';
  return (
    <header className="vc-topbar">
      <IconButton title="Seitenleiste" className="vc-only-narrow" onClick={onToggleSidebar}><Icon name="panel-left" size={18} /></IconButton>
      <div className="vc-topbar__context">
        <span className="vc-topbar__icon"><Icon name="circle-gauge" size={17} /></span>
        <span className="vc-topbar__title">{text(gear.verzahnungstyp)}</span>
        {has(gear.modul) && <Badge square variant="neutral">Modul {text(gear.modul)}</Badge>}
        {has(gear.zaehnezahl) && <Badge square variant="neutral">z = {text(gear.zaehnezahl)}</Badge>}
        {has(gear.werkstoff) && <Badge square variant="neutral">{text(gear.werkstoff)}</Badge>}
      </div>
      <div className="vc-topbar__actions">
        <IconButton title={dark ? 'Light-Mode' : 'Dark-Mode'} onClick={onToggleTheme}>
          <Icon name={dark ? 'sun' : 'moon'} size={18} />
        </IconButton>
        <IconButton title="Inspector" active={inspectorOpen} onClick={onToggleInspector}>
          <Icon name="panel-right" size={18} />
        </IconButton>
      </div>
    </header>
  );
}
Object.assign(window, { TopBar });
