import React from 'react';

/**
 * Card — bordered surface with optional header (overline + title + actions).
 */
export function Card({ title, overline, actions, flat = false, className = '', bodyClassName = '', children, ...rest }) {
  const cls = ['vc-card', flat ? 'vc-card--flat' : '', className].filter(Boolean).join(' ');
  const hasHeader = title || overline || actions;
  return (
    <div className={cls} {...rest}>
      {hasHeader && (
        <div className="vc-card__header">
          <div>
            {overline && <div className="vc-card__overline">{overline}</div>}
            {title && <div className="vc-card__title">{title}</div>}
          </div>
          {actions && <div style={{ marginLeft: 'auto', display: 'flex', gap: 'var(--space-2)' }}>{actions}</div>}
        </div>
      )}
      <div className={['vc-card__body', bodyClassName].filter(Boolean).join(' ')}>{children}</div>
    </div>
  );
}
