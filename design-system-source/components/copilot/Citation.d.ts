import React from 'react';

export interface CitationProps extends React.HTMLAttributes<HTMLAnchorElement> {
  /** Source index — number (renders "[Q3]") or a full string. */
  qid: number | string;
  onClick?: (e: React.MouseEvent) => void;
}

/** Inline source marker appended to every factual statement in an answer. */
export function Citation(props: CitationProps): JSX.Element;
