import React from 'react';

/**
 * Textarea — multi-line input for questions / free text.
 */
export function Textarea({ label, hint, invalid = false, id, className = '', ...rest }) {
  const taId = id || (label ? `vc-ta-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const cls = ['vc-textarea', invalid ? 'vc-textarea--invalid' : '', className].filter(Boolean).join(' ');
  const field = <textarea id={taId} className={cls} aria-invalid={invalid || undefined} {...rest} />;
  if (!label && !hint) return field;
  return (
    <div className="vc-field">
      {label && <label className="vc-label" htmlFor={taId}>{label}</label>}
      {field}
      {hint && <span className="vc-hint">{hint}</span>}
    </div>
  );
}
