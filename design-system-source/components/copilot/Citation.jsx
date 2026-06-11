import React from 'react';

/**
 * Citation — inline source marker like [Q1]. Renders a clickable chip.
 */
export function Citation({ qid, onClick, className = '', ...rest }) {
  const label = typeof qid === 'number' ? `[Q${qid}]` : qid;
  return (
    <a
      className={['vc-cite', className].filter(Boolean).join(' ')}
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && onClick) { e.preventDefault(); onClick(e); } }}
      {...rest}
    >
      {label}
    </a>
  );
}
