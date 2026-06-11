import React from 'react';

/**
 * Select — native select with custom chevron. Pass options or children.
 * options: [{ value, label }] or string[].
 */
export function Select({ label, hint, options, id, className = '', children, ...rest }) {
  const selId = id || (label ? `vc-sel-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const opts = (options || []).map((o) =>
    typeof o === 'string' ? { value: o, label: o } : o
  );
  const control = (
    <div className="vc-select">
      <select id={selId} className={['vc-select__el', className].filter(Boolean).join(' ')} {...rest}>
        {opts.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
        {children}
      </select>
      <svg className="vc-select__chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m6 9 6 6 6-6" />
      </svg>
    </div>
  );
  if (!label && !hint) return control;
  return (
    <div className="vc-field">
      {label && <label className="vc-label" htmlFor={selId}>{label}</label>}
      {control}
      {hint && <span className="vc-hint">{hint}</span>}
    </div>
  );
}
