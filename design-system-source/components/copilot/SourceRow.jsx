import React from 'react';

/**
 * SourceRow — a retrieved chunk's provenance: [Q#] file — page — similarity.
 */
export function SourceRow({ qid, source, page, similarity, className = '', ...rest }) {
  const label = typeof qid === 'number' ? `Q${qid}` : qid;
  return (
    <div className={['vc-source', className].filter(Boolean).join(' ')} {...rest}>
      <span className="vc-source__qid">{label}</span>
      <span className="vc-source__name">{source}</span>
      <span className="vc-source__meta">
        {page != null && `Seite ${page}`}
        {similarity != null && `  ·  ${Number(similarity).toFixed(3)}`}
      </span>
    </div>
  );
}
