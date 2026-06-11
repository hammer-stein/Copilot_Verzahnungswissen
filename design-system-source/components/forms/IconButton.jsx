import React from 'react';

/**
 * IconButton — square, icon-only control. Pass a Lucide <svg> as children.
 * Variants via `active`; sizes sm | md.
 */
export function IconButton({
  size = 'md',
  active = false,
  className = '',
  title,
  children,
  ...rest
}) {
  const cls = [
    'vc-icon-btn',
    size === 'sm' ? 'vc-icon-btn--sm' : '',
    active ? 'vc-icon-btn--active' : '',
    className,
  ].filter(Boolean).join(' ');
  return (
    <button type="button" className={cls} title={title} aria-label={title} {...rest}>
      {children}
    </button>
  );
}
