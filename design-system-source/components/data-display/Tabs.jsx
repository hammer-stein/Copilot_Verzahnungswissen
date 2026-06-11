import React from 'react';

/**
 * Tabs — controlled tab strip. items: [{ id, label }]. Calls onChange(id).
 */
export function Tabs({ items = [], value, onChange, className = '' }) {
  return (
    <div className={['vc-tabs', className].filter(Boolean).join(' ')} role="tablist">
      {items.map((it) => (
        <button
          key={it.id}
          role="tab"
          aria-selected={value === it.id}
          className={['vc-tab', value === it.id ? 'vc-tab--active' : ''].filter(Boolean).join(' ')}
          onClick={() => onChange && onChange(it.id)}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
