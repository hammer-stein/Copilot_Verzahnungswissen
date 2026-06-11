import React from 'react';

export interface SpinnerProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** @default "sm" */
  size?: 'sm' | 'lg';
}

/** Calm rotating loading indicator (slows under reduced-motion). */
export function Spinner(props: SpinnerProps): JSX.Element;
