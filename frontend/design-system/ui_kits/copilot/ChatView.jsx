/* Main chat transcript: user questions + grounded AI answer cards. */
function UserMessage({ text }) {
  return (
    <div className="vc-msg vc-msg--user">
      <div className="vc-bubble vc-bubble--user">{text}</div>
    </div>
  );
}

function AssistantMessage({ children }) {
  return (
    <div className="vc-msg vc-msg--ai">
      <div className="vc-msg__avatar vc-msg__avatar--ai"><Icon name="cog" size={17} /></div>
      <div className="vc-msg__body">{children}</div>
    </div>
  );
}

function SourcesAccordion({ sources }) {
  const { SourceRow } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [open, setOpen] = React.useState(false);
  return (
    <div className="vc-sources">
      <button className="vc-sources__toggle" onClick={() => setOpen(!open)}>
        <Icon name="book-open" size={15} />
        Quellen
        <span className="vc-sources__count">{sources.length}</span>
        <Icon name={open ? 'chevron-up' : 'chevron-down'} size={15} style={{ marginLeft: open ? 0 : 0 }} />
      </button>
      {open && (
        <div className="vc-sources__list">
          {sources.map((s, i) => (
            <SourceRow key={i} qid={s.qid} source={s.source} page={s.page} similarity={s.similarity} />
          ))}
        </div>
      )}
    </div>
  );
}

/* Maps an agent-step status to a short German badge label. null = no badge (neutral "ok"). */
const STEP_STATUS_LABELS = {
  ok: null,
  warnung: 'Hinweis',
  korrigiert: 'korrigiert',
  freigegeben: 'freigegeben',
  fallback: 'Fallback',
};

/* Prüfbarer Lösungsweg: zeigt die Einzelschritte des Multi-Agenten-Flusses
   (Orchestrator → Solver → Reviewer) und das Prüfurteil. Rein additiv; rendert nur,
   wenn die Antwort einen agent_trace trägt (Single-Pass-Antworten haben keinen). */
function ReasoningAccordion({ steps, review }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="vc-sources vc-reasoning">
      <button className="vc-sources__toggle" onClick={() => setOpen(!open)}>
        <Icon name="sparkles" size={15} />
        Lösungsweg &amp; Prüfung
        <span className="vc-sources__count">{steps.length}</span>
        <Icon name={open ? 'chevron-up' : 'chevron-down'} size={15} />
      </button>
      {open && (
        <div className="vc-reasoning__list">
          {steps.map((s, i) => {
            const badge = STEP_STATUS_LABELS[s.status];
            return (
              <div key={i} className="vc-reasoning__step">
                <div className="vc-reasoning__head">
                  <Icon name={s.icon || 'cog'} size={14} />
                  <span className="vc-reasoning__agent">{s.label}</span>
                  <span className="vc-reasoning__title">{s.title}</span>
                  {s.status && badge !== null && (
                    <span className={'vc-reasoning__badge vc-reasoning__badge--' + s.status}>
                      {badge || s.status}
                    </span>
                  )}
                </div>
                <div className="vc-reasoning__content">{s.content}</div>
              </div>
            );
          })}
          {review && review.status && (
            <div className={'vc-reasoning__verdict vc-reasoning__verdict--' + review.status}>
              <Icon name="shield-check" size={14} />
              <span><strong>Prüfurteil ({review.status}):</strong> {review.summary || ''}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Answer({ title, children, sources, steps, review }) {
  return (
    <div className="vc-answer-wrap">
      {title && <div className="vc-answer-title">{title}</div>}
      <div className="vc-answer">{children}</div>
      {steps && steps.length > 0 && <ReasoningAccordion steps={steps} review={review} />}
      {sources && sources.length > 0 && <SourcesAccordion sources={sources} />}
    </div>
  );
}

function ChatView({ messages, generating }) {
  const { Spinner } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const endRef = React.useRef(null);
  React.useEffect(() => { if (endRef.current) endRef.current.parentNode.scrollTop = endRef.current.offsetTop; }, [messages.length, generating]);

  return (
    <div className="vc-chat">
      <div className="vc-chat__inner">
        {messages.map((m, i) => (
          m.role === 'user'
            ? <UserMessage key={i} text={m.text} />
            : <AssistantMessage key={i}><Answer title={m.title} sources={m.sources} steps={m.steps} review={m.review}>{m.body}</Answer></AssistantMessage>
        ))}
        {generating && (
          <div className="vc-msg vc-msg--ai">
            <div className="vc-msg__avatar vc-msg__avatar--ai"><Icon name="cog" size={17} /></div>
            <div className="vc-generating"><Spinner /> Antwort wird aus den Quellen generiert…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
Object.assign(window, { ChatView, Answer, UserMessage, AssistantMessage, ReasoningAccordion });
