import React from 'react';

export interface CodeBlockProps extends React.HTMLAttributes<HTMLPreElement> {
  /** Uppercase caption bar above the code (e.g. "cad_metadata.json"). */
  caption?: string;
  children: React.ReactNode;
}

/** Monospace block for JSON metadata, formulas (e.g. d = m·z) and code. */
export function CodeBlock(props: CodeBlockProps): JSX.Element;
