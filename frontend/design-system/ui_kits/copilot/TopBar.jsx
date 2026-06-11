/* Top bar: active component context, theme toggle, inspector toggle. */
function TopBar({ gear, dark, onToggleTheme, inspectorOpen, onToggleInspector, onToggleSidebar }) {
  const { IconButton, Badge } = window.VerzahnungsCopilotDesignSystem_c9990b;
  return (
    <header className="vc-topbar">
      <IconButton title="Seitenleiste" className="vc-only-narrow" onClick={onToggleSidebar}><Icon name="panel-left" size={18} /></IconButton>
      <div className="vc-topbar__context">
        <span className="vc-topbar__icon"><Icon name="circle-gauge" size={17} /></span>
        <span className="vc-topbar__title">{gear.verzahnungstyp}</span>
        <Badge square variant="neutral">Modul {gear.modul}</Badge>
        <Badge square variant="neutral">z = {gear.zaehnezahl}</Badge>
        <Badge square variant="neutral">{gear.werkstoff}</Badge>
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
