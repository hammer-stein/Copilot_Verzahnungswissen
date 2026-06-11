import React from 'react';

/**
 * CodeBlock — monospace block for JSON metadata, formulas or code.
 * Optional caption; preserves whitespace, horizontally scrolls.
 */
export function CodeBlock({ caption, children, className = '', ...rest }) {
  if (caption) {
    return (
      <div className={['vc-card', 'vc-card--flat', className].filter(Boolean).join(' ')} style={{ overflow: 'hidden' }}>
        <div className="vc-code__caption">{caption}</div>
        <pre className="vc-code" style={{ border: 'none', borderRadius: 0 }} {...rest}>{children}</pre>
      </div>
    );
  }
  return <pre className={['vc-code', className].filter(Boolean).join(' ')} {...rest}>{children}</pre>;
}
