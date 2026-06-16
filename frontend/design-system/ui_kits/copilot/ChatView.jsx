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

function Answer({ title, children, sources }) {
  return (
    <div className="vc-answer-wrap">
      {title && <div className="vc-answer-title">{title}</div>}
      <div className="vc-answer">{children}</div>
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
            : <AssistantMessage key={i}><Answer title={m.title} sources={m.sources}>{m.body}</Answer></AssistantMessage>
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
Object.assign(window, { ChatView, Answer, UserMessage, AssistantMessage });
