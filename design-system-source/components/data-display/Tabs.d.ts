import React from 'react';

export interface TabItem { id: string; label: React.ReactNode; }

export interface TabsProps {
  items: TabItem[];
  /** Currently active tab id. */
  value: string;
  onChange?: (id: string) => void;
  className?: string;
}

/** Underline tab strip for switching inspector views (Zeichnung / Parameter / Meta). */
export function Tabs(props: TabsProps): JSX.Element;
