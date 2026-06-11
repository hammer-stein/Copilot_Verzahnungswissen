import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  invalid?: boolean;
}

/** Multi-line text input for questions and longer entries. */
export function Textarea(props: TextareaProps): JSX.Element;
