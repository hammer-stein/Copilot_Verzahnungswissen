import React from 'react';

/**
 * Primary action control. KIT-green primary; secondary/ghost for lower emphasis.
 * @startingPoint section="Forms" subtitle="Primary, secondary, ghost & danger buttons" viewport="700x150"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style. @default "primary" */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  /** Control height. @default "md" */
  size?: 'sm' | 'md' | 'lg';
  /** Icon node rendered before the label (e.g. a Lucide <svg>). */
  iconLeft?: React.ReactNode;
  /** Icon node rendered after the label. */
  iconRight?: React.ReactNode;
  disabled?: boolean;
}

/** Primary action control. */
export function Button(props: ButtonProps): JSX.Element;
