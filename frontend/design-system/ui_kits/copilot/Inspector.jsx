/* Right inspector panel: technical drawing, parameter table, metadata JSON. */
function cadRawValue(value) {
  if (value && typeof value === 'object' && Object.prototype.hasOwnProperty.call(value, 'value')) return value.value;
  return value;
}

function cadNumber(value, fallback = null) {
  const raw = cadRawValue(value);
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function parseAsciiStl(text, THREE) {
  const number = '[+-]?(?:\\d+\\.?\\d*|\\.\\d+)(?:[eE][+-]?\\d+)?';
  const vertexRe = new RegExp(`vertex\\s+(${number})\\s+(${number})\\s+(${number})`, 'g');
  const positions = [];
  let match;
  while ((match = vertexRe.exec(text)) !== null) {
    positions.push(Number(match[1]), Number(match[2]), Number(match[3]));
  }
  if (positions.length < 9) {
    throw new Error('STL enthält keine Dreiecksgeometrie.');
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

function StepMeshViewer({ preview, fallback }) {
  const mountRef = React.useRef(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const THREE = window.THREE;
    const mount = mountRef.current;
    if (!preview || !preview.url || !mount || !THREE) {
      setLoading(false);
      if (!THREE) setError('Three.js ist nicht geladen.');
      return undefined;
    }

    let disposed = false;
    let frame = null;
    let renderer = null;
    let resizeObserver = null;
    const cleanup = [];

    const run = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(preview.url, { cache: 'no-store' });
        if (!response.ok) throw new Error(`Preview konnte nicht geladen werden (HTTP ${response.status}).`);
        const stlText = await response.text();
        if (disposed) return;

        const geometry = parseAsciiStl(stlText, THREE);
        const box = geometry.boundingBox || new THREE.Box3().setFromBufferAttribute(geometry.getAttribute('position'));
        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        box.getCenter(center);
        box.getSize(size);
        geometry.translate(-center.x, -center.y, -center.z);
        const maxDim = Math.max(size.x, size.y, size.z, 1);

        const styles = getComputedStyle(document.documentElement);
        const accent = styles.getPropertyValue('--accent').trim() || '#4664aa';
        const textMuted = styles.getPropertyValue('--text-muted').trim() || '#6f7480';

        const scene = new THREE.Scene();
        const group = new THREE.Group();
        group.rotation.x = -0.45;
        group.rotation.z = 0.12;
        scene.add(group);

        const material = new THREE.MeshStandardMaterial({
          color: accent,
          metalness: 0.28,
          roughness: 0.62,
          side: THREE.DoubleSide,
        });
        const mesh = new THREE.Mesh(geometry, material);
        group.add(mesh);

        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(geometry, 25),
          new THREE.LineBasicMaterial({ color: textMuted, transparent: true, opacity: 0.3 })
        );
        group.add(edges);

        scene.add(new THREE.HemisphereLight(0xffffff, 0x8290a8, 1.8));
        const key = new THREE.DirectionalLight(0xffffff, 2.4);
        key.position.set(maxDim * 2, maxDim * 2, maxDim * 3);
        scene.add(key);

        const width = Math.max(mount.clientWidth, 280);
        const height = Math.max(mount.clientHeight, 210);
        const camera = new THREE.PerspectiveCamera(38, width / height, Math.max(maxDim / 500, 0.01), maxDim * 30);
        camera.position.set(maxDim * 1.2, maxDim * 0.85, maxDim * 1.7);
        camera.lookAt(0, 0, 0);

        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height, false);
        renderer.domElement.className = 'vc-step-viewer__webgl';
        mount.replaceChildren(renderer.domElement);

        const resize = () => {
          if (!renderer || !mount) return;
          const nextWidth = Math.max(mount.clientWidth, 280);
          const nextHeight = Math.max(mount.clientHeight, 210);
          camera.aspect = nextWidth / nextHeight;
          camera.updateProjectionMatrix();
          renderer.setSize(nextWidth, nextHeight, false);
        };
        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(mount);

        let dragging = false;
        let lastX = 0;
        let lastY = 0;
        const onPointerDown = (event) => {
          dragging = true;
          lastX = event.clientX;
          lastY = event.clientY;
          renderer.domElement.setPointerCapture?.(event.pointerId);
        };
        const onPointerMove = (event) => {
          if (!dragging) return;
          const dx = event.clientX - lastX;
          const dy = event.clientY - lastY;
          group.rotation.y += dx * 0.01;
          group.rotation.x += dy * 0.01;
          lastX = event.clientX;
          lastY = event.clientY;
        };
        const onPointerUp = (event) => {
          dragging = false;
          renderer.domElement.releasePointerCapture?.(event.pointerId);
        };
        const onWheel = (event) => {
          event.preventDefault();
          const factor = event.deltaY > 0 ? 1.08 : 0.92;
          camera.position.multiplyScalar(factor);
          camera.lookAt(0, 0, 0);
        };
        renderer.domElement.addEventListener('pointerdown', onPointerDown);
        renderer.domElement.addEventListener('pointermove', onPointerMove);
        renderer.domElement.addEventListener('pointerup', onPointerUp);
        renderer.domElement.addEventListener('pointerleave', onPointerUp);
        renderer.domElement.addEventListener('wheel', onWheel, { passive: false });
        cleanup.push(() => {
          renderer.domElement.removeEventListener('pointerdown', onPointerDown);
          renderer.domElement.removeEventListener('pointermove', onPointerMove);
          renderer.domElement.removeEventListener('pointerup', onPointerUp);
          renderer.domElement.removeEventListener('pointerleave', onPointerUp);
          renderer.domElement.removeEventListener('wheel', onWheel);
        });

        const animate = () => {
          if (disposed || !renderer) return;
          if (!dragging) group.rotation.y += 0.006;
          renderer.render(scene, camera);
          frame = window.requestAnimationFrame(animate);
        };
        animate();
        if (!disposed) setLoading(false);
      } catch (e) {
        if (!disposed) {
          console.warn('STEP-Preview konnte nicht gerendert werden', e);
          setError(String(e.message || e));
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      disposed = true;
      if (frame) window.cancelAnimationFrame(frame);
      if (resizeObserver) resizeObserver.disconnect();
      cleanup.forEach((fn) => fn());
      if (renderer) {
        renderer.dispose();
        renderer.domElement.remove();
      }
    };
  }, [preview && preview.url]);

  if (error) {
    return (
      <div className="vc-step-viewer vc-step-viewer--fallback">
        {fallback}
        <div className="vc-step-viewer__notice">3D-Preview nicht verfügbar</div>
      </div>
    );
  }

  return (
    <div className="vc-step-viewer">
      <div ref={mountRef} className="vc-step-viewer__canvas" />
      {loading && (
        <div className="vc-step-viewer__overlay">
          <span className="vc-step-viewer__spinner" />
          <span>STEP-Geometrie wird geladen</span>
        </div>
      )}
    </div>
  );
}

function GearSketch({ gear, raw }) {
  const geo = (raw && raw.basic_geometry) || {};
  const tp = (raw && raw.tooth_profile) || {};
  const topology = (raw && raw.topology) || {};
  const teeth = Math.max(8, Math.min(96, Math.round(cadNumber(tp.num_teeth, cadNumber(gear.zaehnezahl, 32)) || 32)));
  const outer = cadNumber(geo.outer_diameter_mm, cadNumber(gear.kopfkreis, 100)) || 100;
  const root = cadNumber(geo.root_diameter_mm, cadNumber(gear.fusskreis, outer * 0.84)) || outer * 0.84;
  const pitch = cadNumber(geo.pitch_diameter_mm, cadNumber(gear.teilkreis, (outer + root) / 2)) || (outer + root) / 2;
  const bore = cadNumber(geo.hub_bore_diameter_mm, outer * 0.24) || outer * 0.24;
  const face = cadNumber(geo.face_width_mm, cadNumber(gear.zahnbreite, null));
  const type = cadRawValue(raw && raw.gear_type) || String(gear.verzahnungstyp || '');
  const isInternal = Boolean(cadRawValue(topology.is_internal_gear)) || String(type).includes('internal');
  const maxD = Math.max(outer, root, pitch, bore, 1);
  const scale = 160 / maxD;
  const rOuter = Math.max(54, outer * scale / 2);
  const rRoot = Math.max(38, root * scale / 2);
  const rPitch = Math.max(26, pitch * scale / 2);
  const rBore = Math.max(13, bore * scale / 2);
  const ticks = Array.from({ length: Math.min(teeth, 72) }, (_, i) => i);
  return (
    <div className="vc-cad-preview">
      <svg viewBox="0 0 260 210" role="img" aria-label="CAD-Vorschau des analysierten Zahnrads">
        <defs>
          <radialGradient id="gearFill" cx="48%" cy="42%" r="65%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.92)" />
            <stop offset="100%" stopColor="rgba(70,100,170,0.18)" />
          </radialGradient>
        </defs>
        <g transform="translate(130 93)">
          {ticks.map((i) => {
            const a = (Math.PI * 2 * i) / ticks.length;
            const x1 = Math.cos(a) * (rRoot + 4);
            const y1 = Math.sin(a) * (rRoot + 4);
            const x2 = Math.cos(a) * (rOuter + 6);
            const y2 = Math.sin(a) * (rOuter + 6);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className="vc-cad-preview__tooth" />;
          })}
          <circle r={rOuter} className="vc-cad-preview__outer" />
          <circle r={rPitch} className="vc-cad-preview__pitch" />
          <circle r={isInternal ? rRoot : rBore} className="vc-cad-preview__bore" />
          {isInternal && <circle r={rBore} className="vc-cad-preview__hub" />}
          <line x1={-rOuter} y1={rOuter + 18} x2={rOuter} y2={rOuter + 18} className="vc-cad-preview__dim" />
          <text x="0" y={rOuter + 35} textAnchor="middle" className="vc-cad-preview__label">dₐ {outer.toFixed(1)} mm</text>
        </g>
        <g transform="translate(206 32)">
          <line x1="0" y1="0" x2="0" y2="122" className="vc-cad-preview__dim" />
          <line x1="-8" y1="0" x2="8" y2="0" className="vc-cad-preview__dim" />
          <line x1="-8" y1="122" x2="8" y2="122" className="vc-cad-preview__dim" />
          <text x="13" y="64" className="vc-cad-preview__label">d_f {root.toFixed(1)} mm</text>
        </g>
      </svg>
      <div className="vc-cad-preview__meta">
        <span>{gear.verzahnungstyp}</span>
        <span>z = {teeth}</span>
        {face !== null && <span>b = {face.toFixed(1)} mm</span>}
      </div>
    </div>
  );
}

function Inspector({ gear, raw = null, preview = null, hasPart = true, onClose }) {
  const { Tabs, ParameterTable, CodeBlock, Badge } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [tab, setTab] = React.useState('zeichnung');
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
  // Nur Badges mit echtem Wert anzeigen (Werkstoff/Qualität fehlen bei reinen Geometrie-STEPs).
  const has = (value) => value !== null && value !== undefined && String(value).trim() !== '' && String(value).trim() !== '—';

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
    { key: 'Verzahnungstyp', value: text(gear.verzahnungstyp), unit: '' },
    { key: 'Modul', value: text(gear.modul), unit: 'mm' },
    { key: 'Zähnezahl', value: text(gear.zaehnezahl), unit: '' },
    { key: 'Eingriffswinkel', value: text(gear.eingriffswinkel), unit: '°' },
    { key: 'Schrägungswinkel', value: text(gear.schraegungswinkel), unit: '°' },
    { key: 'Profilverschiebung', value: text(gear.profilverschiebung), unit: 'x' },
    { key: 'Teilkreis d', value: text(gear.teilkreis), unit: 'mm' },
    { key: 'Kopfkreis dₐ', value: text(gear.kopfkreis), unit: 'mm' },
    { key: 'Fußkreis d_f', value: text(gear.fusskreis), unit: 'mm' },
    { key: 'Zahnbreite b', value: text(gear.zahnbreite), unit: 'mm' },
  ];
  // Echtes cad_metadata-JSON (GearParameters) anzeigen; Fallback auf die Parameter-Sicht.
  const json = raw && Object.keys(raw).length
    ? JSON.stringify(raw, null, 2)
    : JSON.stringify({
        verzahnungstyp: gear.verzahnungstyp, modul: gear.modul, zaehnezahl: gear.zaehnezahl,
        eingriffswinkel: gear.eingriffswinkel, werkstoff: gear.werkstoff, qualitaet: gear.qualitaet,
      }, null, 2);

  return (
    <aside className="vc-inspector">
      <div className="vc-inspector__head">
        <span className="vc-inspector__title">Inspektor</span>
        <Badge variant="accent">{text(gear.verzahnungstyp)}</Badge>
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
              {preview && preview.url
                ? <StepMeshViewer preview={preview} fallback={<GearSketch gear={gear} raw={raw} />} />
                : <GearSketch gear={gear} raw={raw} />}
            </div>
            <div className="vc-inspector__caption">
              {preview && preview.url ? '3D-Preview aus der hochgeladenen STEP-Datei' : 'CAD-Vorschau aus analysierten STEP-Parametern'}
            </div>
          </div>
        )}
        {tab === 'parameter' && (
          <div>
            <div className="vc-inspector__sectlbl">Geometrie &amp; Werkstoff</div>
            <ParameterTable rows={rows} />
            {(has(gear.haerte) || has(gear.qualitaet) || has(gear.werkstoff)) && (
              <div className="vc-inspector__chips">
                {has(gear.haerte) && <Badge variant="success">{text(gear.haerte)}</Badge>}
                {has(gear.qualitaet) && <Badge square variant="neutral">DIN-Qualität {text(gear.qualitaet)}</Badge>}
                {has(gear.werkstoff) && <Badge variant="info">{text(gear.werkstoff)}</Badge>}
              </div>
            )}
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
