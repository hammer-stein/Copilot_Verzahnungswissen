import React from 'react';

export interface SelectOption { value: string; label: string; }

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  /** Options as strings or {value,label} objects. */
  options?: Array<string | SelectOption>;
}

/** Native select with a custom chevron, matching the field styling. */
export function Select(props: SelectProps): JSX.Element;
