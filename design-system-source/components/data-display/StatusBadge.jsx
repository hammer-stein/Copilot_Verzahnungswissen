import React from 'react';

/**
 * StatusBadge — dot + label for document/indexing state.
 * status: ready | indexing | error | idle.
 */
const LABELS = { ready: 'Bereit', indexing: 'Indexiert…', error: 'Fehler', idle: 'Inaktiv' };

export function StatusBadge({ status = 'idle', label, className = '', ...rest }) {
  const cls = ['vc-status', `vc-status--${status}`, className].filter(Boolean).join(' ');
  return (
    <span className={cls} {...rest}>
      <span className="vc-status__dot" />
      {label || LABELS[status]}
    </span>
  );
}
