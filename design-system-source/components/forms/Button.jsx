import React from 'react';

/**
 * Button — primary action control for the copilot UI.
 * Variants: primary (KIT green), secondary, ghost, danger. Sizes: sm | md | lg.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  type = 'button',
  iconLeft,
  iconRight,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  const cls = [
    'vc-btn',
    `vc-btn--${variant}`,
    size !== 'md' ? `vc-btn--${size}` : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button type={type} className={cls} disabled={disabled} {...rest}>
      {iconLeft}
      {children != null && <span>{children}</span>}
      {iconRight}
    </button>
  );
}
