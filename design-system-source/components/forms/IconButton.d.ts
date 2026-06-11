import React from 'react';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** @default "md" */
  size?: 'sm' | 'md';
  /** Renders the active/selected surface (e.g. open inspector toggle). */
  active?: boolean;
  /** Accessible label + tooltip (icon-only buttons must have one). */
  title?: string;
  /** The icon, typically a Lucide <svg>. */
  children: React.ReactNode;
}

/** Icon-only button for toolbars, list-row actions and panel toggles. */
export function IconButton(props: IconButtonProps): JSX.Element;
