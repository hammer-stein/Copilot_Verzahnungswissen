/* Shared UI helpers for the copilot kit: Lucide Icon + product Logo. */

function Icon({ name, size = 18, color, style, ...rest }) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current && window.lucide) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      ref.current.appendChild(el);
      window.lucide.createIcons({
        attrs: { width: size, height: size, 'stroke-width': 1.75 },
        nameAttr: 'data-lucide',
      });
    }
  }, [name, size]);
  return <span ref={ref} aria-hidden="true" style={{ display: 'inline-flex', color, ...style }} />;
}

function LogoTile({ size = 34, radius = 10, iconSize = 19 }) {
  return (
    <div className="vc-logo__tile" style={{ width: size, height: size, borderRadius: radius }}>
      <Icon name="cog" size={iconSize} />
    </div>
  );
}

function Logo({ showWordmark = true }) {
  return (
    <div className="vc-logo">
      <LogoTile />
      {showWordmark && (
        <div>
          <div className="vc-logo__name">Verzahnung&nbsp;Intelligence</div>
          <div className="vc-logo__sub">Wissensbasis · KIT</div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Icon, Logo, LogoTile });
