/* Document library.
   Two-pane organisation: folders on the left, documents in the selected folder on
   the right. Uploads target the selected folder; folder uploads can preserve their
   relative subfolder names. */
function KnowledgeBase({
  documents, folders, busy, onClose,
  onUpload, onCreateFolder, onDeleteFolder, onMoveDocument, onRenameDocument, onDeleteDocument,
}) {
  const { Button, IconButton, Input, Select, Spinner } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [selectedFolder, setSelectedFolder] = React.useState('');
  const [newFolder, setNewFolder] = React.useState('');
  const [notice, setNotice] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [workingDoc, setWorkingDoc] = React.useState('');
  const fileRef = React.useRef(null);
  const folderRef = React.useRef(null);

  const docTitle = (d) =>
    d.file_name || (d.source_path ? d.source_path.split('/').pop() : String(d.doc_hash || '').slice(0, 10));

  const groups = React.useMemo(() => {
    const out = { '': [] };
    (folders || []).forEach((f) => {
      const name = String(f || '').trim();
      if (name) out[name] = out[name] || [];
    });
    (documents || []).forEach((d) => {
      const folder = String(d.folder || '').trim();
      out[folder] = out[folder] || [];
      out[folder].push(d);
    });
    Object.keys(out).forEach((folder) => {
      out[folder].sort((a, b) => docTitle(a).localeCompare(docTitle(b), 'de'));
    });
    return out;
  }, [documents, folders]);

  const folderNames = React.useMemo(
    () => Object.keys(groups).filter(Boolean).sort((a, b) => a.localeCompare(b, 'de')),
    [groups],
  );

  React.useEffect(() => {
    if (!Object.prototype.hasOwnProperty.call(groups, selectedFolder)) {
      setSelectedFolder('');
    }
  }, [groups, selectedFolder]);

  const activeDocs = groups[selectedFolder] || [];
  const totalDocs = (documents || []).length;
  const folderCount = folderNames.length;
  const activeLabel = selectedFolder || 'Ohne Ordner';
  const moveOptions = [
    { value: '', label: 'Ohne Ordner' },
    ...folderNames.map((f) => ({ value: f, label: f })),
  ];

  const createFolder = async () => {
    const name = newFolder.trim();
    if (!name) return;
    setCreating(true);
    setNotice('');
    try {
      await onCreateFolder(name);
      setNewFolder('');
      setSelectedFolder(name);
      setNotice(`Ordner „${name}“ angelegt.`);
    } catch (e) {
      setNotice(`Ordner konnte nicht angelegt werden: ${String(e.message || e)}`);
    } finally {
      setCreating(false);
    }
  };

  const deleteFolder = async (name) => {
    if (!window.confirm(`Ordner „${name}“ löschen? Enthaltene Dokumente werden nach „Ohne Ordner“ verschoben.`)) return;
    setNotice('');
    try {
      await onDeleteFolder(name);
      setSelectedFolder('');
      setNotice(`Ordner „${name}“ gelöscht. Dokumente bleiben erhalten.`);
    } catch (e) {
      setNotice(`Ordner konnte nicht gelöscht werden: ${String(e.message || e)}`);
    }
  };

  const uploadFiles = async (files, preserveFolders = false) => {
    const allowed = Array.from(files || []).filter((f) => /\.(pdf|csv|xlsx|xls)$/i.test(f.name));
    if (allowed.length === 0) {
      setNotice('Keine unterstützten Dateien (PDF, CSV, Excel) gefunden.');
      return;
    }
    setNotice(`${allowed.length.toLocaleString('de-DE')} Datei(en) werden hochgeladen...`);
    try {
      const result = await onUpload(allowed, selectedFolder, { preserveFolders });
      const failed = result && result.failed ? result.failed : 0;
      setNotice(failed
        ? `${(result.uploaded || 0).toLocaleString('de-DE')} Datei(en) hochgeladen, ${failed.toLocaleString('de-DE')} fehlgeschlagen.`
        : `${allowed.length.toLocaleString('de-DE')} Datei(en) hochgeladen.`);
    } catch (e) {
      setNotice(`Upload fehlgeschlagen: ${String(e.message || e)}`);
    }
  };

  const moveDocument = async (doc, folder) => {
    setWorkingDoc(doc.doc_hash);
    setNotice('');
    try {
      await onMoveDocument(doc.doc_hash, folder);
      setNotice(`„${docTitle(doc)}“ verschoben.`);
    } catch (e) {
      setNotice(`Dokument konnte nicht verschoben werden: ${String(e.message || e)}`);
    } finally {
      setWorkingDoc('');
    }
  };

  const renameDocument = async (doc) => {
    const current = docTitle(doc);
    const next = window.prompt('Dokumenttitel', current);
    if (next === null) return;
    const title = next.trim();
    if (!title || title === current) return;
    setWorkingDoc(doc.doc_hash);
    setNotice('');
    try {
      await onRenameDocument(doc.doc_hash, title);
      setNotice(`„${title}“ gespeichert.`);
    } catch (e) {
      setNotice(`Dokumenttitel konnte nicht gespeichert werden: ${String(e.message || e)}`);
    } finally {
      setWorkingDoc('');
    }
  };

  const deleteDocument = async (doc) => {
    if (!window.confirm(`„${docTitle(doc)}“ aus der Wissensbasis entfernen?`)) return;
    setWorkingDoc(doc.doc_hash);
    setNotice('');
    try {
      await onDeleteDocument(doc.doc_hash);
      setNotice(`„${docTitle(doc)}“ entfernt.`);
    } catch (e) {
      setNotice(`Dokument konnte nicht gelöscht werden: ${String(e.message || e)}`);
    } finally {
      setWorkingDoc('');
    }
  };

  const FolderButton = ({ folder, label, count, icon }) => (
    <button
      type="button"
      className={'vc-libfolder' + (selectedFolder === folder ? ' vc-libfolder--active' : '')}
      onClick={() => setSelectedFolder(folder)}
    >
      <span className="vc-libfolder__ico"><Icon name={icon} size={15} /></span>
      <span className="vc-libfolder__main">
        <span className="vc-libfolder__name">{label}</span>
        <span className="vc-libfolder__meta">{count.toLocaleString('de-DE')} Dokumente</span>
      </span>
      <span className="vc-libfolder__count">{count}</span>
    </button>
  );

  return (
    <section className="vc-kbview">
      <header className="vc-kbview__head">
        <span className="vc-kbview__hico"><Icon name="library" size={19} /></span>
        <div className="vc-kbview__headmain">
          <div className="vc-kbview__title">Dokumentbibliothek</div>
          <div className="vc-kbview__sub">
            {totalDocs.toLocaleString('de-DE')} Dokumente · {folderCount.toLocaleString('de-DE')} Ordner
          </div>
        </div>
        {busy && <Spinner />}
        <Button variant="secondary" iconLeft={<Icon name="arrow-left" size={15} />} onClick={onClose}>
          Zurück zum Chat
        </Button>
      </header>

      {notice && <div className="vc-kbnotice">{notice}</div>}

      <div className="vc-library">
        <aside className="vc-library__folders" aria-label="Ordner">
          <div className="vc-library__folders-head">
            <span>Ordner</span>
            <span>{folderCount + 1}</span>
          </div>

          <div className="vc-library__folder-list">
            <FolderButton folder="" label="Ohne Ordner" count={(groups[''] || []).length} icon="files" />
            {folderNames.map((name) => (
              <div className="vc-libfolderwrap" key={name}>
                <FolderButton folder={name} label={name} count={(groups[name] || []).length} icon="folder" />
                <IconButton size="sm" title="Ordner löschen" onClick={() => deleteFolder(name)}>
                  <Icon name="trash-2" size={13} />
                </IconButton>
              </div>
            ))}
          </div>

          <form className="vc-libcreate" onSubmit={(e) => { e.preventDefault(); createFolder(); }}>
            <Input
              placeholder="Neuer Ordner"
              value={newFolder}
              onChange={(e) => setNewFolder(e.target.value)}
            />
            <Button type="submit" variant="secondary" iconLeft={<Icon name="folder-plus" size={15} />} disabled={creating || !newFolder.trim()}>
              Anlegen
            </Button>
          </form>
        </aside>

        <main className="vc-library__docs">
          <div className="vc-library__docs-head">
            <div>
              <div className="vc-library__docs-title">{activeLabel}</div>
              <div className="vc-library__docs-sub">
                {activeDocs.length.toLocaleString('de-DE')} Dokumente in diesem Ordner
              </div>
            </div>
            <div className="vc-library__actions">
              <input ref={fileRef} type="file" accept=".pdf,.csv,.xlsx,.xls" multiple style={{ display: 'none' }} onChange={async (e) => {
                await uploadFiles(e.target.files, false);
                e.target.value = '';
              }} />
              <input ref={folderRef} type="file" accept=".pdf,.csv,.xlsx,.xls" multiple webkitdirectory="" directory="" style={{ display: 'none' }} onChange={async (e) => {
                await uploadFiles(e.target.files, true);
                e.target.value = '';
              }} />
              <Button variant="primary" iconLeft={<Icon name="upload" size={15} />} onClick={() => fileRef.current && fileRef.current.click()}>
                Dokumente hochladen
              </Button>
              <Button variant="secondary" iconLeft={<Icon name="folder-up" size={15} />} onClick={() => folderRef.current && folderRef.current.click()}>
                Ordner hochladen
              </Button>
            </div>
          </div>

          {activeDocs.length === 0 ? (
            <div className="vc-libempty">
              <Icon name="inbox" size={30} style={{ color: 'var(--text-faint)' }} />
              <p>Dieser Ordner enthält noch keine Dokumente.</p>
            </div>
          ) : (
            <div className="vc-libdocs">
              {activeDocs.map((doc) => (
                <div className="vc-libdoc" key={doc.doc_hash}>
                  <span className="vc-libdoc__ico"><Icon name="file-text" size={17} /></span>
                  <div className="vc-libdoc__main">
                    <div className="vc-libdoc__title" title={docTitle(doc)}>{docTitle(doc)}</div>
                    <div className="vc-libdoc__meta">{(doc.chunk_count || 0).toLocaleString('de-DE')} Chunks</div>
                  </div>
                  <Select
                    className="vc-libdoc__move"
                    options={moveOptions}
                    value={doc.folder || ''}
                    disabled={workingDoc === doc.doc_hash}
                    onChange={(e) => moveDocument(doc, e.target.value)}
                    title="In Ordner verschieben"
                  />
                  <IconButton size="sm" title="Dokumenttitel ändern" disabled={workingDoc === doc.doc_hash} onClick={() => renameDocument(doc)}>
                    <Icon name="pencil" size={15} />
                  </IconButton>
                  <IconButton size="sm" title="Dokument löschen" disabled={workingDoc === doc.doc_hash} onClick={() => deleteDocument(doc)}>
                    <Icon name="trash-2" size={15} />
                  </IconButton>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
Object.assign(window, { KnowledgeBase });