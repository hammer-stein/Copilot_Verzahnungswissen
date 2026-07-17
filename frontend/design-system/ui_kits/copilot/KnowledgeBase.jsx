/* Document library.
   Two-pane organisation: folders on the left, documents in the selected folder on
   the right. Uploads target the selected folder; folder uploads can preserve their
   relative subfolder names.

   Zwei Löschwege zusätzlich zum Einzel-Löschen:
   - "Alle löschen": leert die gesamte Wissensbasis (alle Dokumente + Ordner).
   - Mehrfachauswahl ("Auswählen"): Checkboxen an Ordnern und Dokumenten; die
     Auswahl wird auf einmal gelöscht (ein ausgewählter Ordner nimmt seine
     Dokumente mit). Die Auswahl bleibt beim Wechsel des Ordners erhalten. */
function KnowledgeBase({
  documents, folders, busy, onClose,
  onUpload, onCreateFolder, onDeleteFolder, onMoveDocument, onRenameDocument, onDeleteDocument,
  onDeleteAll, onBulkDelete,
}) {
  const { Button, IconButton, Input, Select, Spinner } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [selectedFolder, setSelectedFolder] = React.useState('');
  const [newFolder, setNewFolder] = React.useState('');
  const [notice, setNotice] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [workingDoc, setWorkingDoc] = React.useState('');
  // Live-Fortschritt beim (ggf. sehr großen) Mehrfach-Upload: null = kein Upload aktiv.
  const [uploadProgress, setUploadProgress] = React.useState(null);
  // Mehrfachauswahl-Modus zum gebündelten Löschen von Dokumenten und Ordnern.
  const [selectMode, setSelectMode] = React.useState(false);
  const [selectedDocs, setSelectedDocs] = React.useState(() => new Set());
  const [selectedFolders, setSelectedFolders] = React.useState(() => new Set());
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

  // Alle Dokumente, die die aktuelle Auswahl löschen würde (direkt gewählte
  // plus alle in gewählten Ordnern) – für Bestätigungstext und Löschzähler.
  const affectedDocHashes = React.useMemo(() => {
    const s = new Set(selectedDocs);
    (documents || []).forEach((d) => {
      if (selectedFolders.has(String(d.folder || '').trim())) s.add(d.doc_hash);
    });
    return s;
  }, [selectedDocs, selectedFolders, documents]);

  const selectionEmpty = selectedDocs.size === 0 && selectedFolders.size === 0;

  const toggleDoc = (hash) => setSelectedDocs((prev) => {
    const next = new Set(prev);
    if (next.has(hash)) next.delete(hash); else next.add(hash);
    return next;
  });
  const toggleFolder = (name) => setSelectedFolders((prev) => {
    const next = new Set(prev);
    if (next.has(name)) next.delete(name); else next.add(name);
    return next;
  });
  const selectAllInFolder = () => setSelectedDocs((prev) => {
    const next = new Set(prev);
    activeDocs.forEach((d) => next.add(d.doc_hash));
    return next;
  });
  const clearSelection = () => { setSelectedDocs(new Set()); setSelectedFolders(new Set()); };
  const enterSelect = () => { setSelectMode(true); clearSelection(); setNotice(''); };
  const cancelSelect = () => { setSelectMode(false); clearSelection(); };

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

  // "Alle löschen": komplette Wissensbasis leeren (Dokumente + Ordner).
  const deleteAll = async () => {
    if (totalDocs === 0 && folderCount === 0) return;
    const summary = [];
    if (totalDocs) summary.push(`${totalDocs.toLocaleString('de-DE')} Dokument(e)`);
    if (folderCount) summary.push(`${folderCount.toLocaleString('de-DE')} Ordner`);
    if (!window.confirm(`Gesamte Wissensbasis löschen? ${summary.join(' und ')} werden endgültig entfernt.`)) return;
    setNotice('');
    try {
      const res = await onDeleteAll();
      const dd = (res && typeof res.deleted_documents === 'number') ? res.deleted_documents : totalDocs;
      setSelectedFolder('');
      cancelSelect();
      setNotice(`Wissensbasis geleert: ${dd.toLocaleString('de-DE')} Dokument(e) gelöscht.`);
    } catch (e) {
      setNotice(`Löschen fehlgeschlagen: ${String(e.message || e)}`);
    }
  };

  // Mehrfachauswahl gebündelt löschen (gewählte Dokumente + ganze Ordner).
  const deleteSelected = async () => {
    if (selectionEmpty) return;
    const nDocs = affectedDocHashes.size;
    const nFolders = selectedFolders.size;
    const summary = [];
    if (nDocs) summary.push(`${nDocs.toLocaleString('de-DE')} Dokument(e)`);
    if (nFolders) summary.push(`${nFolders.toLocaleString('de-DE')} Ordner`);
    if (!window.confirm(`${summary.join(' und ')} endgültig löschen?`)) return;
    setNotice('');
    try {
      // Nur explizit gewählte Dokumente + Ordnernamen senden – der Server ergänzt
      // die Dokumente der gewählten Ordner selbst.
      await onBulkDelete(Array.from(selectedDocs), Array.from(selectedFolders));
      setSelectedFolder('');
      cancelSelect();
      setNotice(`${summary.join(' und ')} gelöscht.`);
    } catch (e) {
      setNotice(`Löschen fehlgeschlagen: ${String(e.message || e)}`);
    }
  };

  const uploadFiles = async (files, preserveFolders = false) => {
    const allowed = Array.from(files || []).filter((f) => /\.(pdf|csv|xlsx|xls)$/i.test(f.name));
    if (allowed.length === 0) {
      setNotice('Keine unterstützten Dateien (PDF, CSV, Excel) gefunden.');
      return;
    }
    setNotice('');
    setUploadProgress({ done: 0, total: allowed.length, uploaded: 0, failed: 0, currentName: '' });
    try {
      const result = await onUpload(allowed, selectedFolder, {
        preserveFolders,
        onProgress: (p) => setUploadProgress(p),
      });
      const failed = result && result.failed ? result.failed : 0;
      setNotice(failed
        ? `${(result.uploaded || 0).toLocaleString('de-DE')} Datei(en) hochgeladen, ${failed.toLocaleString('de-DE')} fehlgeschlagen.`
        : `${allowed.length.toLocaleString('de-DE')} Datei(en) hochgeladen.`);
    } catch (e) {
      setNotice(`Upload fehlgeschlagen: ${String(e.message || e)}`);
    } finally {
      setUploadProgress(null);
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

  const hasContent = totalDocs > 0 || folderCount > 0;
  const uploading = !!uploadProgress;
  const uploadPct = uploadProgress && uploadProgress.total
    ? Math.round((uploadProgress.done / uploadProgress.total) * 100)
    : 0;

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
        {!selectMode && hasContent && (
          <Button variant="secondary" iconLeft={<Icon name="list-checks" size={15} />} onClick={enterSelect}>
            Auswählen
          </Button>
        )}
        {!selectMode && hasContent && (
          <Button variant="danger" iconLeft={<Icon name="trash-2" size={15} />} onClick={deleteAll}>
            Alle löschen
          </Button>
        )}
        <Button variant="secondary" iconLeft={<Icon name="arrow-left" size={15} />} onClick={onClose}>
          Zurück zum Chat
        </Button>
      </header>

      {selectMode && (
        <div className="vc-kbview__toolbar vc-kbselbar">
          <div className="vc-kbselbar__info">
            {selectedDocs.size.toLocaleString('de-DE')} Dokument(e) · {selectedFolders.size.toLocaleString('de-DE')} Ordner ausgewählt
          </div>
          <div className="vc-kbselbar__actions">
            <Button variant="ghost" onClick={selectAllInFolder} disabled={activeDocs.length === 0}>
              Ordner auswählen
            </Button>
            <Button variant="ghost" onClick={clearSelection} disabled={selectionEmpty}>
              Auswahl aufheben
            </Button>
            <Button
              variant="danger"
              iconLeft={<Icon name="trash-2" size={15} />}
              disabled={selectionEmpty}
              onClick={deleteSelected}
            >
              {`Löschen${affectedDocHashes.size ? ` (${affectedDocHashes.size.toLocaleString('de-DE')})` : ''}`}
            </Button>
            <Button variant="secondary" onClick={cancelSelect}>Fertig</Button>
          </div>
        </div>
      )}

      {uploadProgress && (
        <div className="vc-uploadprog" role="status" aria-live="polite">
          <div className="vc-uploadprog__top">
            <span className="vc-uploadprog__label">
              <span className="vc-uploadprog__spin"><Icon name="loader" size={14} /></span>
              Upload läuft …
            </span>
            <span className="vc-uploadprog__count">
              {uploadProgress.done.toLocaleString('de-DE')} / {uploadProgress.total.toLocaleString('de-DE')} Dateien ({uploadPct}%)
              {uploadProgress.failed ? ` · ${uploadProgress.failed.toLocaleString('de-DE')} fehlgeschlagen` : ''}
            </span>
          </div>
          <div className="vc-uploadprog__track">
            <div className="vc-uploadprog__fill" style={{ width: `${uploadPct}%` }} />
          </div>
          {uploadProgress.currentName && (
            <div className="vc-uploadprog__file" title={uploadProgress.currentName}>
              Gerade: {uploadProgress.currentName}
            </div>
          )}
        </div>
      )}

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
              <div
                className={'vc-libfolderwrap' + (selectMode ? ' vc-libfolderwrap--select' : '')}
                key={name}
              >
                {selectMode && (
                  <input
                    type="checkbox"
                    className="vc-check"
                    checked={selectedFolders.has(name)}
                    onChange={() => toggleFolder(name)}
                    aria-label={`Ordner ${name} auswählen`}
                  />
                )}
                <FolderButton folder={name} label={name} count={(groups[name] || []).length} icon="folder" />
                {!selectMode && (
                  <IconButton size="sm" title="Ordner löschen" onClick={() => deleteFolder(name)}>
                    <Icon name="trash-2" size={13} />
                  </IconButton>
                )}
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
              <Button variant="primary" iconLeft={<Icon name="upload" size={15} />} disabled={selectMode || uploading} onClick={() => fileRef.current && fileRef.current.click()}>
                Dokumente hochladen
              </Button>
              <Button variant="secondary" iconLeft={<Icon name="folder-up" size={15} />} disabled={selectMode || uploading} onClick={() => folderRef.current && folderRef.current.click()}>
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
              {activeDocs.map((doc) => {
                if (selectMode) {
                  const folderSelected = !!doc.folder && selectedFolders.has(String(doc.folder).trim());
                  const checked = selectedDocs.has(doc.doc_hash) || folderSelected;
                  return (
                    <label className={'vc-libdoc vc-libdoc--select' + (checked ? ' vc-libdoc--checked' : '')} key={doc.doc_hash}>
                      <input
                        type="checkbox"
                        className="vc-check"
                        checked={checked}
                        disabled={folderSelected}
                        onChange={() => toggleDoc(doc.doc_hash)}
                      />
                      <span className="vc-libdoc__ico"><Icon name="file-text" size={17} /></span>
                      <div className="vc-libdoc__main">
                        <div className="vc-libdoc__title" title={docTitle(doc)}>{docTitle(doc)}</div>
                        <div className="vc-libdoc__meta">
                          {folderSelected
                            ? 'Wird mit dem Ordner gelöscht'
                            : `${(doc.chunk_count || 0).toLocaleString('de-DE')} Chunks`}
                        </div>
                      </div>
                    </label>
                  );
                }
                return (
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
                );
              })}
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
Object.assign(window, { KnowledgeBase });
