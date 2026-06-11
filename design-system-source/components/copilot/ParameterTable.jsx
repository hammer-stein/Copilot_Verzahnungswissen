import React from 'react';

/**
 * ParameterTable — key / value / unit table for gear (CAD) metadata.
 * rows: [{ key, value, unit }].
 */
export function ParameterTable({ rows = [], header, className = '', ...rest }) {
  return (
    <table className={['vc-param-table', className].filter(Boolean).join(' ')} {...rest}>
      {header && (
        <thead>
          <tr>
            <th>{header[0] || 'Parameter'}</th>
            <th style={{ textAlign: 'right' }} colSpan={2}>{header[1] || 'Wert'}</th>
          </tr>
        </thead>
      )}
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="vc-param-table__key">{r.key}</td>
            <td className="vc-param-table__val">{r.value}</td>
            <td className="vc-param-table__unit">{r.unit || ''}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
