import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Strong header title. */
  title?: React.ReactNode;
  /** Uppercase overline above the title. */
  overline?: React.ReactNode;
  /** Right-aligned header actions (e.g. IconButtons). */
  actions?: React.ReactNode;
  /** Remove the drop shadow. */
  flat?: boolean;
  bodyClassName?: string;
}

/** Bordered content surface for panels, answers and parameter blocks. */
export function Card(props: CardProps): JSX.Element;
