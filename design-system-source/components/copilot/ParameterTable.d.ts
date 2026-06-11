import React from 'react';

export interface ParameterRow {
  key: React.ReactNode;
  value: React.ReactNode;
  /** Unit suffix (mm, °, …). */
  unit?: string;
}

/**
 * Right-aligned, tabular key/value/unit table for gear parameters & tolerances.
 * @startingPoint section="Copilot" subtitle="Gear parameter / tolerance table" viewport="700x320"
 */
export interface ParameterTableProps extends React.HTMLAttributes<HTMLTableElement> {
  rows: ParameterRow[];
  /** Optional [keyHeader, valueHeader] column titles. */
  header?: [string, string];
}

/** Tabular key/value/unit table for gear parameters. */
export function ParameterTable(props: ParameterTableProps): JSX.Element;
