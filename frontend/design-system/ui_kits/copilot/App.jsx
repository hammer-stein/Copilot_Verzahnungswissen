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

/* Map raw backend cad_metadata → the stringified gear shape the UI renders. */
function toGear(cad) {
  if (!cad || typeof cad !== 'object' || Object.keys(cad).length === 0) return null;
  const s = (v) => (v === null || v === undefined ? '—' : String(v));
  return {
    verzahnungstyp: s(cad.verzahnungstyp),
    modul: s(cad.modul),
    zaehnezahl: s(cad.zaehnezahl),
    eingriffswinkel: s(cad.eingriffswinkel),
    schraegungswinkel: s(cad.schraegungswinkel),
    profilverschiebung: s(cad.profilverschiebung),
    teilkreis: s(cad.teilkreisdurchmesser),
    kopfkreis: s(cad.kopfkreisdurchmesser),
    fusskreis: s(cad.fusskreisdurchmesser),
    zahnbreite: s(cad.zahnbreite),
    werkstoff: s(cad.werkstoff),
    haerte: s(cad.haerte),
    qualitaet: s(cad.verzahnungsqualitaet),
  };
}

/* Inline markdown within a single text run: [Q#] → Citation chip, **bold** → <strong>. */
function renderInline(text, Citation, keyPrefix) {
  return String(text).split(/(\[Q\d+\]|\*\*[^*]+\*\*)/g).map((tok, i) => {
    const key = keyPrefix + '-' + i;
    const cite = tok.match(/^\[Q(\d+)\]$/);
    if (cite) return <Citation key={key} qid={Number(cite[1])} />;
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

/* Map backend AnswerSource[] → the {qid, source, page, similarity} shape SourceRow expects. */
function toSources(sources) {
  return (sources || []).map((s) => {
    const n = parseInt(String(s.qid).replace(/\D/g, ''), 10);
    return {
      qid: Number.isFinite(n) ? n : s.qid,
      source: s.source_path,
      page: s.page_number,
      similarity: s.similarity,
    };
  });
}

const PDF_RE = /\.pdf$/i;
const STEP_RE = /\.(step|stp|stp242|p21|iges|igs)$/i;

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

  /* Load the indexed-document count for the knowledge-base status panel. */
  const refreshKnowledgeBase = React.useCallback(() => {
    fetch(`${API}/documents`)
      .then((r) => (r.ok ? r.json() : []))
      .then((docs) => setKnowledgeBase({ docs: Array.isArray(docs) ? docs.length : 0, status: 'ready' }))
      .catch(() => setKnowledgeBase({ docs: 0, status: 'error' }));
  }, []);

  React.useEffect(() => { refreshKnowledgeBase(); }, [refreshKnowledgeBase]);

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
      appendMsg(chatId, {
        role: 'assistant',
        title: ans.question || text,
        body: renderAnswer(ans.answer_text, Citation),
        sources: toSources(ans.sources),
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
     - PDF  → /upload  (adds to the RAG knowledge base)
     - STEP → /cad/analyze (CAD processor → cad_metadata for the active part) */
  const uploadFile = async (file) => {
    if (!file) return;

    if (PDF_RE.test(file.name)) {
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch(`${API}/upload`, { method: 'POST', body: fd });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
      } catch (e) {
        console.error('PDF-Upload fehlgeschlagen', e);
      } finally {
        refreshKnowledgeBase();
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

  return (
    <div className={'vc-shell' + (inspectorOpen ? ' vc-shell--inspector' : '') + (sidebarOpen ? ' vc-shell--sidebar-open' : '')}>
      <Sidebar
        chats={chats}
        activePart={activePart}
        knowledgeBase={knowledgeBase}
        activeChat={activeChat}
        onSelectChat={(id) => { setActiveChat(id); setSidebarOpen(false); }}
        onNewChat={newChat}
        onHome={goHome}
        onUploadStep={uploadFile}
      />
      <div className="vc-main">
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
      </div>
      {inspectorOpen && <Inspector gear={gearView} hasPart={!!cadMeta} onClose={() => setInspectorOpen(false)} />}
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
