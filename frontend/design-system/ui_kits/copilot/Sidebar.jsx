/* Left sidebar: brand, new chat, chat history, active part + RAG status. */
function Sidebar({ chats, activePart, knowledgeBase, activeChat, kbOpen, onSelectChat, onNewChat, onHome, onUploadStep, onManageKb }) {
  const { Button, IconButton, Spinner } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const stepInput = React.useRef(null);
  const groups = {};
  chats.forEach((c) => { (groups[c.when] = groups[c.when] || []).push(c); });

  const pickStep = () => { if (stepInput.current) stepInput.current.click(); };
  const onStepChosen = (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) onUploadStep(f);
    e.target.value = '';
  };

  return (
    <aside className="vc-sidebar">
      <button className="vc-sidebar__brand" onClick={onHome} title="Zur Startseite">
        <Logo />
      </button>

      <div className="vc-sidebar__section">
        <Button variant="primary" iconLeft={<Icon name="plus" size={16} />} style={{ width: '100%' }} onClick={onNewChat}>
          Neue Konversation
        </Button>
      </div>

      <div className="vc-sidebar__scroll">
        <div className="vc-sidebar__label">Verlauf</div>
        {Object.entries(groups).map(([when, list]) => (
          <div key={when} className="vc-histgroup">
            <div className="vc-histgroup__when">{when}</div>
            {list.map((c) => (
              <button
                key={c.id}
                className={'vc-histitem' + (c.id === activeChat ? ' vc-histitem--active' : '')}
                onClick={() => onSelectChat(c.id)}
              >
                <Icon name="message-square" size={15} />
                <span className="vc-histitem__title">{c.title}</span>
              </button>
            ))}
          </div>
        ))}

        <div className="vc-sidebar__label" style={{ marginTop: 18 }}>Aktives Bauteil</div>
        <input
          ref={stepInput}
          type="file"
          accept=".step,.stp,.stp242,.p21,.iges,.igs,.json,model/step,application/json"
          style={{ display: 'none' }}
          onChange={onStepChosen}
        />
        {activePart ? (
          <div className="vc-part">
            <span className="vc-part__ico"><Icon name="box" size={18} /></span>
            <div className="vc-part__main">
              <div className="vc-part__name" title={activePart.name}>{activePart.name}</div>
              {activePart.status === 'indexing' ? (
                <div className="vc-part__status vc-part__status--idx"><Spinner /> Wird analysiert…</div>
              ) : activePart.status === 'error' ? (
                <div className="vc-part__status vc-part__status--err" title={activePart.error || ''}>
                  <Icon name="alert-circle" size={12} /> Analyse fehlgeschlagen
                </div>
              ) : (
                <div className="vc-part__status"><span className="vc-part__dot" /> Bereit für Fragen</div>
              )}
            </div>
            <IconButton size="sm" title="Andere STEP-Datei hochladen" onClick={pickStep}><Icon name="refresh-cw" size={14} /></IconButton>
          </div>
        ) : (
          <button className="vc-upload" onClick={pickStep}>
            <span className="vc-upload__ico"><Icon name="box" size={18} /></span>
            <span className="vc-upload__main">
              <span className="vc-upload__title">CAD / STEP / JSON laden</span>
              <span className="vc-upload__hint">.step · .stp · .iges · .json — klicken oder ablegen</span>
            </span>
            <Icon name="upload" size={16} />
          </button>
        )}

        <div className="vc-sidebar__label" style={{ marginTop: 20 }}>Wissensbasis</div>
        <button className={'vc-kb vc-kb--btn' + (kbOpen ? ' vc-kb--active' : '')} onClick={onManageKb} title="Wissensbasis verwalten">
          <span className="vc-kb__ico"><Icon name="database" size={16} /></span>
          <div className="vc-kb__main">
            <div className="vc-kb__title">RAG-Wissensbasis verbunden</div>
            <div className="vc-kb__meta">{knowledgeBase.docs.toLocaleString('de-DE')} Dokumente · verwalten</div>
          </div>
          <Icon name="settings-2" size={15} />
        </button>
        <p className="vc-kb__note">Dokumente und Ordner verwalten: hinzufügen, verschieben, löschen. Pro Antwort erscheinen nur die tatsächlich verwendeten Quellen.</p>
      </div>

      <div className="vc-sidebar__foot">
        <span className="vc-avatar">VZ</span>
        <span>Verzahnungs-Copilot</span>
        <IconButton size="sm" title="Einstellungen" style={{ marginLeft: 'auto' }}><Icon name="settings" size={15} /></IconButton>
      </div>
    </aside>
  );
}
Object.assign(window, { Sidebar });
