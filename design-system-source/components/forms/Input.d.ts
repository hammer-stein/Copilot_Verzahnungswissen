import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Field label rendered above the input. */
  label?: string;
  /** Helper text below the input. */
  hint?: string;
  /** Error styling. */
  invalid?: boolean;
  /** Monospace + tabular figures, for numeric/parameter entry. */
  mono?: boolean;
}

/** Single-line text field. Wrap with label/hint or render bare. */
export function Input(props: InputProps): JSX.Element;
