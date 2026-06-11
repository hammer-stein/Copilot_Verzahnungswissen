import React from 'react';

export interface SourceRowProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Source index — number or string. */
  qid: number | string;
  /** File name / source path. */
  source: string;
  /** Page number in the source document. */
  page?: number;
  /** Vector similarity score (0–1), shown to 3 decimals. */
  similarity?: number;
}

/** Provenance row for the "Quellen anzeigen" accordion under an answer. */
export function SourceRow(props: SourceRowProps): JSX.Element;
