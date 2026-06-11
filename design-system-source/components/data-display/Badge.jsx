import React from 'react';

/**
 * Badge — compact status/category label.
 */
export function Badge({ variant = 'neutral', square = false, iconLeft, className = '', children, ...rest }) {
  const cls = [
    'vc-badge',
    `vc-badge--${variant}`,
    square ? 'vc-badge--square' : '',
    className,
  ].filter(Boolean).join(' ');
  return (
    <span className={cls} {...rest}>
      {iconLeft}
      {children}
    </span>
  );
}
