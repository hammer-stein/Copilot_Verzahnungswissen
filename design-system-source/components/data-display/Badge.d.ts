import React from 'react';

/**
 * Compact label for categories, norms, materials and statuses.
 * @startingPoint section="Data display" subtitle="Status & category badges" viewport="700x120"
 */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** @default "neutral" */
  variant?: 'neutral' | 'accent' | 'info' | 'warning' | 'danger' | 'success';
  /** Square + mono styling, for codes like a DIN class or norm. */
  square?: boolean;
  iconLeft?: React.ReactNode;
}

/** Compact status/category label. */
export function Badge(props: BadgeProps): JSX.Element;
