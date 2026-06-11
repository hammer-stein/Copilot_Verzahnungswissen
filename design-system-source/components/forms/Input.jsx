import React from 'react';

/**
 * Input — single-line text field with optional label and hint.
 * Use `mono` for parameter/number entry (tabular figures).
 */
export function Input({
  label,
  hint,
  invalid = false,
  mono = false,
  id,
  className = '',
  ...rest
}) {
  const inputId = id || (label ? `vc-in-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const cls = [
    'vc-input',
    mono ? 'vc-input--mono' : '',
    invalid ? 'vc-input--invalid' : '',
    className,
  ].filter(Boolean).join(' ');
  const field = <input id={inputId} className={cls} aria-invalid={invalid || undefined} {...rest} />;
  if (!label && !hint) return field;
  return (
    <div className="vc-field">
      {label && <label className="vc-label" htmlFor={inputId}>{label}</label>}
      {field}
      {hint && <span className="vc-hint">{hint}</span>}
    </div>
  );
}
