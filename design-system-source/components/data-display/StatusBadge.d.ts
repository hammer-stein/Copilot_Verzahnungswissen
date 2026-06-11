import React from 'react';

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** @default "idle" */
  status?: 'ready' | 'indexing' | 'error' | 'idle';
  /** Override the default German label. */
  label?: React.ReactNode;
}

/** Dot + label conveying document indexing state (ready/indexing/error). */
export function StatusBadge(props: StatusBadgeProps): JSX.Element;
