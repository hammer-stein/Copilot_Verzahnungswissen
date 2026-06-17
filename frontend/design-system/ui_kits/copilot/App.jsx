/* App shell: sidebar + chat + composer + inspector.
   Wired to the real FastAPI backend (/ask, /cad/analyze, /upload, /documents). */

/* API base — same origin as the served page; '' keeps fetch('/ask') relative. */
const API = '';

/* Placeholder shown before any CAD/STEP part has been analysed. */
const EMPTY_GEAR = {
  verzahnungstyp: 'Kein Bauteil', modul: '—', zaehnezahl: '—', eingriffswinkel: '—',
  schraegungswinkel: '—', profilverschiebung: '—', teilkreis: '—', kopfkreis: '—',
  fusskreis: '—', zahnbreite: '—', werkstoff: '—', haerte: '—', qualitaet: '—',
};

/* German labels for the GearParameters gear_type enum. */
const GEAR_TYPE_LABELS = {
  spur: 'Stirnrad', helical: 'Schrägverzahnung', bevel: 'Kegelrad',
  internal: 'Innenverzahnung', worm: 'Schnecke', rack: 'Zahnstange',
};

/* Map raw backend cad_metadata (GearParameters nested format from cad_processor /
   the synthetic test JSONs) → the stringified gear shape the UI renders. */
function toGear(cad) {
  if (!cad || typeof cad !== 'object' || Object.keys(cad).length === 0) return null;
  const s = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));
  const tp = cad.tooth_profile || {};
  const geo = cad.basic_geometry || {};
  const mc = cad.material_context || {};
  return {
    verzahnungstyp: cad.gear_type ? (GEAR_TYPE_LABELS[cad.gear_type] || cad.gear_type) : '—',
    modul: s(tp.module_mm),
    zaehnezahl: s(tp.num_teeth),
    eingriffswinkel: s(tp.pressure_angle_deg),
    schraegungswinkel: s(tp.helix_angle_deg),
    profilverschiebung: s(tp.profile_shift_x),
    teilkreis: s(geo.pitch_diameter_mm),
    kopfkreis: s(geo.outer_diameter_mm),
    fusskreis: s(geo.root_diameter_mm),
    zahnbreite: s(geo.face_width_mm),
    werkstoff: s(mc.material),
    haerte: s(mc.tolerance_class),
    qualitaet: s(mc.quality_class_din),
  };
}

/* Inline markdown within a single text run: [Q#] → Citation chip, [CAD] → CAD chip,
   **bold** → <strong>. [CAD] marks facts the LLM derived from the Bauteildaten. */
function renderInline(text, Citation, keyPrefix) {
  return String(text).split(/(\[Q\d+\]|\[CAD\]|\*\*[^*]+\*\*)/g).map((tok, i) => {
    const key = keyPrefix + '-' + i;
    const cite = tok.match(/^\[Q(\d+)\]$/);
    if (cite) return <Citation key={key} qid={Number(cite[1])} />;
    if (tok === '[CAD]') return <span key={key} className="vc-cadchip" title="Aus den Bauteildaten (CAD)">CAD</span>;
    const bold = tok.match(/^\*\*([^*]+)\*\*$/);
    if (bold) return <strong key={key}>{bold[1]}</strong>;
    if (!tok) return null;
    return <React.Fragment key={key}>{tok}</React.Fragment>;
  });
}

/* Split a markdown table row "| a | b |" into trimmed cell strings. */
function splitRow(row) {
  return row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

/* Render an LLM answer_text (markdown-ish) into JSX: paragraphs, bullet lists,
   markdown tables and headings — each with inline [Q#] citations and **bold**.
   This makes every Ausgabeformat (kurz/standard/ausführlich/stichpunkte/tabellarisch)
   render correctly instead of showing raw markdown. */
function renderAnswer(text, Citation) {
  const lines = String(text || '').replace(/\r/g, '').split('\n');
  const isTable = (l) => /^\s*\|.*\|\s*$/.test(l);
  const isTableSep = (l) => l.includes('-') && /^\s*\|?[\s:|-]+\|?\s*$/.test(l);
  const isBullet = (l) => /^\s*[-*•]\s+/.test(l);
  const isHeading = (l) => /^\s*#{1,6}\s+/.test(l);

  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    // Markdown table — consume consecutive "| … |" lines, drop the "---" separator row.
    if (isTable(line)) {
      const block = [];
      while (i < lines.length && isTable(lines[i])) { block.push(lines[i]); i++; }
      const rows = block.filter((r) => !isTableSep(r)).map(splitRow);
      const [head, ...body] = rows;
      out.push(
        <table key={'t' + i} className="vc-md-table">
          {head && (
            <thead><tr>{head.map((c, ci) => <th key={ci}>{renderInline(c, Citation, 'th' + i + ci)}</th>)}</tr></thead>
          )}
          <tbody>
            {body.map((r, ri) => (
              <tr key={ri}>{r.map((c, ci) => <td key={ci}>{renderInline(c, Citation, 'td' + i + ri + ci)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      );
      continue;
    }

    // Bullet list — consume consecutive bullet lines.
    if (isBullet(line)) {
      const items = [];
      while (i < lines.length && isBullet(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*•]\s+/, '')); i++;
      }
      out.push(
        <ul key={'u' + i} className="vc-md-list">
          {items.map((it, ii) => <li key={ii}>{renderInline(it, Citation, 'li' + i + ii)}</li>)}
        </ul>
      );
      continue;
    }

    // Heading (## …) — rendered as a small bold subheading.
    if (isHeading(line)) {
      out.push(<div key={'h' + i} className="vc-md-h">{renderInline(line.replace(/^\s*#{1,6}\s+/, ''), Citation, 'h' + i)}</div>);
      i++;
      continue;
    }

    // Default: paragraph.
    out.push(<p key={'p' + i}>{renderInline(line, Citation, 'p' + i)}</p>);
    i++;
  }
  return <>{out}</>;
}

function isUnknownDocumentTitle(value) {
  const text = String(value || '').trim();
  return !text || /^(unbenanntes|unbekanntes) dokument$/i.test(text);
}

function generatedUploadBasename(value) {
  const name = String(value || '').split(/[\\/]/).filter(Boolean).pop() || '';
  const stem = name.replace(/\.[^.]+$/, '');
  return /^\d{8}_\d{6}_[0-9a-f]{16,}$/i.test(stem);
}

function titleFromDocument(doc) {
  if (!doc) return '';
  const explicit = String(doc.file_name || doc.title || doc.document_title || doc.original_filename || '').trim();
  if (!isUnknownDocumentTitle(explicit)) return explicit;
  if (doc.source_path && !generatedUploadBasename(doc.source_path)) {
    return String(doc.source_path).split(/[\\/]/).filter(Boolean).pop() || '';
  }
  return '';
}

function documentTitleIndex(documents) {
  const byHash = new Map();
  const byPath = new Map();
  (documents || []).forEach((doc) => {
    const title = titleFromDocument(doc);
    if (!title) return;
    const hash = String(doc.doc_hash || '').trim();
    const path = String(doc.source_path || '').trim();
    if (hash) byHash.set(hash, title);
    if (path) byPath.set(path, title);
  });
  return { byHash, byPath };
}

function sourceLabel(source, titleIndex) {
  const docHash = String(source.doc_hash || source.docHash || '').trim();
  if (docHash && titleIndex && titleIndex.byHash && titleIndex.byHash.has(docHash)) {
    return titleIndex.byHash.get(docHash);
  }

  const raw = String(source.source_path || source.sourcePath || source.source || '').trim();
  if (raw && titleIndex && titleIndex.byPath && titleIndex.byPath.has(raw)) {
    return titleIndex.byPath.get(raw);
  }

  const explicit = String(source.title || source.file_name || source.document_title || source.original_filename || '').trim();
  if (!isUnknownDocumentTitle(explicit)) return explicit;

  const name = raw.split(/[\\/]/).filter(Boolean).pop() || '';
  if (!name) return 'Unbenanntes Dokument';

  if (generatedUploadBasename(name)) return 'Unbenanntes Dokument';
  return name;
}

/* Map backend AnswerSource[] → the {qid, source, page, similarity} shape SourceRow expects. */
function toSources(sources, documents) {
  const titleIndex = documentTitleIndex(documents);
  return (sources || []).map((s) => {
    const n = parseInt(String(s.qid).replace(/\D/g, ''), 10);
    return {
      qid: Number.isFinite(n) ? n : s.qid,
      source: sourceLabel(s, titleIndex),
      sourcePath: s.source_path,
      page: s.page_number,
      similarity: s.similarity,
    };
  });
}

const PDF_RE = /\.pdf$/i;
const STEP_RE = /\.(step|stp|stp242|p21|iges|igs)$/i;
const JSON_RE = /\.json$/i;

function relativeFolder(file) {
  const rel = file && file.webkitRelativePath ? String(file.webkitRelativePath) : '';
  const parts = rel.split('/').map((p) => p.trim()).filter(Boolean);
  return parts.length > 1 ? parts.slice(0, -1).join('/') : '';
}

function joinFolder(base, child) {
  const left = String(base || '').trim().replace(/^\/+|\/+$/g, '');
  const right = String(child || '').trim().replace(/^\/+|\/+$/g, '');
  return [left, right].filter(Boolean).join('/');
}

function App() {
  const D = window.VC_DATA;
  const { Citation } = window.VerzahnungsCopilotDesignSystem_c9990b;

  const [dark, setDark] = React.useState(false);
  const [inspectorOpen, setInspectorOpen] = React.useState(true);
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [chats, setChats] = React.useState([]);
  const [activePart, setActivePart] = React.useState(null);
  const [knowledgeBase, setKnowledgeBase] = React.useState({ docs: 0, status: 'loading' });
  const [transcripts, setTranscripts] = React.useState({});
  const [activeChat, setActiveChat] = React.useState(null);
  const [format, setFormat] = React.useState('standard');
  const [generating, setGenerating] = React.useState(false);
  /* Raw backend cad_metadata (sent to /ask); null until a STEP is analysed. */
  const [cadMeta, setCadMeta] = React.useState(null);

  const gearView = toGear(cadMeta) || EMPTY_GEAR;

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  }, [dark]);

  /* Knowledge-base management state (modal): full document list + folders. */
  const [kbOpen, setKbOpen] = React.useState(false);
  const [documents, setDocuments] = React.useState([]);
  const [folders, setFolders] = React.useState([]);
  const [kbBusy, setKbBusy] = React.useState(false);

  /* Load the indexed-document count for the knowledge-base status panel. */
  const refreshKnowledgeBase = React.useCallback(() => {
    fetch(`${API}/documents`)
      .then((r) => (r.ok ? r.json() : []))
      .then((docs) => {
        const list = Array.isArray(docs) ? docs : [];
        setDocuments(list);
        setKnowledgeBase({ docs: list.length, status: 'ready' });
      })
      .catch(() => setKnowledgeBase({ docs: 0, status: 'error' }));
  }, []);

  React.useEffect(() => { refreshKnowledgeBase(); }, [refreshKnowledgeBase]);

  /* Load full document list + folder list for the management modal. */
  const refreshKb = React.useCallback(async () => {
    setKbBusy(true);
    try {
      const [dRes, fRes] = await Promise.all([fetch(`${API}/documents`), fetch(`${API}/folders`)]);
      const docs = dRes.ok ? await dRes.json() : [];
      const fold = fRes.ok ? await fRes.json() : { folders: [] };
      setDocuments(Array.isArray(docs) ? docs : []);
      setFolders((fold && fold.folders) || []);
      setKnowledgeBase({ docs: Array.isArray(docs) ? docs.length : 0, status: 'ready' });
    } catch (e) {
      console.error('Wissensbasis konnte nicht geladen werden', e);
    } finally {
      setKbBusy(false);
    }
  }, []);

  const openKb = () => { setKbOpen(true); refreshKb(); };

  /* KB actions — each refreshes the list afterwards. */
  const kbUpload = async (files, folder, opts = {}) => {
    const list = Array.from(files || []).filter((file) => PDF_RE.test(file.name));
    if (list.length === 0) return { uploaded: 0, failed: 0 };
    let uploaded = 0;
    let failed = 0;
    setKbBusy(true);
    try {
      for (const file of list) {
        const uploadFolder = opts.preserveFolders
          ? joinFolder(folder, relativeFolder(file))
          : (folder || '');
        try {
          await uploadFile(file, uploadFolder, { refresh: false, throwOnError: true });
          uploaded += 1;
        } catch (e) {
          failed += 1;
          console.error('PDF-Upload fehlgeschlagen', file.name, e);
        }
      }
    } finally {
      await refreshKb();
      setKbBusy(false);
    }
    return { uploaded, failed };
  };
  const kbCreateFolder = async (name) => {
    const r = await fetch(`${API}/folders`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    if (!r.ok) {
      const j = await r.json().catch(() => null);
      throw new Error((j && j.detail) || `HTTP ${r.status}`);
    }
    const j = await r.json().catch(() => null);
    if (j && Array.isArray(j.folders)) {
      setFolders(j.folders);
    } else {
      setFolders((prev) => Array.from(new Set([...(prev || []), name])).sort((a, b) => a.localeCompare(b, 'de')));
    }
    await refreshKb();
  };
  const kbDeleteFolder = async (name) => {
    await fetch(`${API}/folders/${encodeURIComponent(name)}`, { method: 'DELETE' });
    await refreshKb();
  };
  const kbMoveDocument = async (docHash, folder) => {
    await fetch(`${API}/documents/${docHash}/move`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder: folder || '' }) });
    await refreshKb();
  };
  const kbRenameDocument = async (docHash, title) => {
    const r = await fetch(`${API}/documents/${docHash}/title`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => null);
      throw new Error((j && j.detail) || `HTTP ${r.status}`);
    }
    await refreshKb();
  };
  const kbDeleteDocument = async (docHash) => {
    await fetch(`${API}/documents/${docHash}`, { method: 'DELETE' });
    await refreshKb();
  };

  const messages = activeChat ? (transcripts[activeChat] || []) : [];

  const appendMsg = (chatId, msg) => {
    setTranscripts((t) => ({ ...t, [chatId]: [...(t[chatId] || []), msg] }));
  };

  const send = async (text) => {
    let chatId = activeChat;
    /* Starting from the home screen creates a brand-new, client-side chat. */
    if (!chatId) {
      chatId = 'c' + Date.now();
      const title = text.length > 46 ? text.slice(0, 43) + '…' : text;
      setChats((cs) => [{ id: chatId, title, when: 'Heute' }, ...cs]);
      setTranscripts((t) => ({ ...t, [chatId]: [] }));
      setActiveChat(chatId);
    }
    appendMsg(chatId, { role: 'user', text });
    setGenerating(true);

    try {
      const r = await fetch(`${API}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ questions: [text], cad_metadata: cadMeta || {}, format }),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        const detail = j && (j.detail || j.message) ? (j.detail || j.message) : `HTTP ${r.status}`;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      const ans = (j.answers && j.answers[0]) || {};
      let sourceDocuments = documents;
      if ((!sourceDocuments || sourceDocuments.length === 0) && ans.sources && ans.sources.length) {
        try {
          const dRes = await fetch(`${API}/documents`);
          const docs = dRes.ok ? await dRes.json() : [];
          sourceDocuments = Array.isArray(docs) ? docs : [];
          if (sourceDocuments.length) setDocuments(sourceDocuments);
        } catch (e) {
          console.warn('Dokumenttitel konnten nicht nachgeladen werden', e);
        }
      }
      appendMsg(chatId, {
        role: 'assistant',
        title: ans.question || text,
        body: renderAnswer(ans.answer_text, Citation),
        sources: toSources(ans.sources, sourceDocuments),
      });
    } catch (e) {
      appendMsg(chatId, {
        role: 'assistant',
        title: 'Fehler bei der Beantwortung',
        body: (
          <p className="vc-answer__nosrc">
            Die Anfrage konnte nicht verarbeitet werden: {String(e.message || e)}
          </p>
        ),
        sources: [],
      });
    } finally {
      setGenerating(false);
    }
  };

  const goHome = () => { setActiveChat(null); setSidebarOpen(false); };
  const newChat = () => { setActiveChat(null); };

  /* File upload from sidebar/composer.
     - PDF  → /upload  (adds to the RAG knowledge base; optional target folder)
     - JSON → parsed client-side as a GearParameters part → cad_metadata (test data)
     - STEP → /cad/analyze (CAD processor → cad_metadata for the active part) */
  const uploadFile = async (file, folder = '', options = {}) => {
    if (!file) return;
    const shouldRefresh = options.refresh !== false;

    if (PDF_RE.test(file.name)) {
      const fd = new FormData();
      fd.append('file', file);
      if (folder) fd.append('folder', folder);
      try {
        const r = await fetch(`${API}/upload`, { method: 'POST', body: fd });
        const j = await r.json().catch(() => null);
        if (!r.ok) {
          const detail = j && (j.detail || j.message) ? (j.detail || j.message) : `HTTP ${r.status}`;
          throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
        }
        return j;
      } catch (e) {
        console.error('PDF-Upload fehlgeschlagen', e);
        if (options.throwOnError) throw e;
      } finally {
        if (shouldRefresh) refreshKnowledgeBase();
      }
      return;
    }

    /* GearParameters test JSON → load directly as the active part (no server round-trip). */
    if (JSON_RE.test(file.name)) {
      setActivePart({ name: file.name, status: 'indexing' });
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        if (!parsed || typeof parsed !== 'object' || (!parsed.gear_type && !parsed.tooth_profile)) {
          throw new Error('Keine gültigen GearParameters (gear_type / tooth_profile fehlen).');
        }
        setCadMeta(parsed);
        setActivePart({ name: file.name, status: 'ready' });
      } catch (e) {
        console.error('JSON-Bauteil konnte nicht geladen werden', e);
        setActivePart({ name: file.name, status: 'error', error: String(e.message || e) });
      }
      return;
    }

    if (!STEP_RE.test(file.name)) {
      console.warn('Nicht unterstützter Dateityp:', file.name);
      return;
    }

    setActivePart({ name: file.name, status: 'indexing' });
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(`${API}/cad/analyze`, { method: 'POST', body: fd });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        const detail = j && j.detail ? j.detail : `HTTP ${r.status}`;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      setCadMeta(j);
      setActivePart({ name: file.name, status: 'ready' });
    } catch (e) {
      console.error('CAD-Analyse fehlgeschlagen', e);
      setActivePart({ name: file.name, status: 'error', error: String(e.message || e) });
    }
  };

  /* While the knowledge-base manager is open it takes over the whole main area
     (chat, composer and inspector are hidden) — focused document/folder work. */
  const showInspector = inspectorOpen && !kbOpen;

  return (
    <div className={'vc-shell' + (showInspector ? ' vc-shell--inspector' : '') + (sidebarOpen ? ' vc-shell--sidebar-open' : '')}>
      <Sidebar
        chats={chats}
        activePart={activePart}
        knowledgeBase={knowledgeBase}
        activeChat={activeChat}
        kbOpen={kbOpen}
        onSelectChat={(id) => { setActiveChat(id); setKbOpen(false); setSidebarOpen(false); }}
        onNewChat={() => { setKbOpen(false); newChat(); }}
        onHome={() => { setKbOpen(false); goHome(); }}
        onUploadStep={uploadFile}
        onManageKb={openKb}
      />
      <div className="vc-main">
        {kbOpen ? (
          <KnowledgeBase
            documents={documents}
            folders={folders}
            busy={kbBusy}
            onClose={() => setKbOpen(false)}
            onUpload={kbUpload}
            onCreateFolder={kbCreateFolder}
            onDeleteFolder={kbDeleteFolder}
            onMoveDocument={kbMoveDocument}
            onRenameDocument={kbRenameDocument}
            onDeleteDocument={kbDeleteDocument}
          />
        ) : (
          <>
            <TopBar
              gear={gearView}
              dark={dark}
              onToggleTheme={() => setDark((v) => !v)}
              inspectorOpen={inspectorOpen}
              onToggleInspector={() => setInspectorOpen((v) => !v)}
              onToggleSidebar={() => setSidebarOpen((v) => !v)}
            />
            {messages.length === 0
              ? <EmptyState onPick={send} />
              : <ChatView key={activeChat} messages={messages} generating={generating} />}
            <Composer onSend={send} format={format} onFormat={setFormat} formats={D.formats} onUploadStep={uploadFile} />
          </>
        )}
      </div>
      {showInspector && <Inspector gear={gearView} raw={cadMeta} hasPart={!!cadMeta} onClose={() => setInspectorOpen(false)} />}
      {sidebarOpen && <div className="vc-scrim" onClick={() => setSidebarOpen(false)} />}
    </div>
  );
}

function EmptyState({ onPick }) {
  const suggestions = [
    'Wie wirkt sich die Profilverschiebung auf die Zahnfußtragfähigkeit aus?',
    'Vergleiche Wälzfräsen und Wälzstoßen für Modul 3.',
    'Welche Härteverfahren sind für 42CrMo4 geeignet?',
  ];
  return (
    <div className="vc-empty">
      <div className="vc-empty__icon"><Icon name="cog" size={34} /></div>
      <h1 className="vc-empty__title">Womit kann ich helfen?</h1>
      <p className="vc-empty__sub">Antworten ausschließlich aus Ihrer indexierten Wissensbasis — mit vollständiger Quellenangabe.</p>
      <div className="vc-empty__chips">
        {suggestions.map((s, i) => (
          <button key={i} className="vc-suggest" onClick={() => onPick(s)}>
            <span className="vc-suggest__ico"><Icon name="sparkles" size={15} /></span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
Object.assign(window, { App, EmptyState });
