import React from 'react';

/** Spinner — calm loading indicator. size: sm | lg. */
export function Spinner({ size = 'sm', className = '', ...rest }) {
  const cls = ['vc-spinner', size === 'lg' ? 'vc-spinner--lg' : '', className].filter(Boolean).join(' ');
  return <span className={cls} role="status" aria-label="Lädt" {...rest} />;
}
