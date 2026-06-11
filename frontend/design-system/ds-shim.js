/* ============================================================
   ds-shim.js — preview fallback for the Verzahnungs-Copilot DS.

   The compiler-generated _ds_bundle.js is injected by the Design
   System tab runtime, but is NOT served when an HTML file is opened
   directly in a plain preview. This shim defines the SAME namespace
   (window.VerzahnungsCopilotDesignSystem_c9990b) with plain-JS,
   React-global versions of every component — but ONLY if the real
   bundle has not already populated it. The real bundle always wins.

   Keep in sync with components/*. Styling comes from components.css.
   ============================================================ */
(function () {
  var NS = 'VerzahnungsCopilotDesignSystem_c9990b';
  if (window[NS] && window[NS].Button) return; // real bundle present
  var R = window.React;
  if (!R) return;
  var h = R.createElement;
  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(' '); }
  function rid(p) { return p + Math.random().toString(36).slice(2, 8); }

  function Button(props) {
    var p = props || {}, variant = p.variant || 'primary', size = p.size || 'md';
    var rest = Object.assign({}, p);
    delete rest.variant; delete rest.size; delete rest.iconLeft; delete rest.iconRight;
    delete rest.className; delete rest.children;
    var cls = cx('vc-btn', 'vc-btn--' + variant, size !== 'md' ? 'vc-btn--' + size : '', p.className);
    return h('button', Object.assign({ type: p.type || 'button', className: cls, disabled: p.disabled }, rest),
      p.iconLeft, p.children != null ? h('span', null, p.children) : null, p.iconRight);
  }

  function IconButton(props) {
    var p = props || {}, size = p.size || 'md';
    var rest = Object.assign({}, p);
    delete rest.size; delete rest.active; delete rest.className; delete rest.children; delete rest.title;
    var cls = cx('vc-icon-btn', size === 'sm' ? 'vc-icon-btn--sm' : '', p.active ? 'vc-icon-btn--active' : '', p.className);
    return h('button', Object.assign({ type: 'button', className: cls, title: p.title, 'aria-label': p.title }, rest), p.children);
  }

  function Input(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label; delete rest.hint; delete rest.invalid; delete rest.mono; delete rest.className; delete rest.id;
    var id = p.id || (p.label ? rid('vc-in-') : undefined);
    var cls = cx('vc-input', p.mono ? 'vc-input--mono' : '', p.invalid ? 'vc-input--invalid' : '', p.className);
    var field = h('input', Object.assign({ id: id, className: cls, 'aria-invalid': p.invalid || undefined }, rest));
    if (!p.label && !p.hint) return field;
    return h('div', { className: 'vc-field' },
      p.label ? h('label', { className: 'vc-label', htmlFor: id }, p.label) : null,
      field, p.hint ? h('span', { className: 'vc-hint' }, p.hint) : null);
  }

  function Textarea(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label; delete rest.hint; delete rest.invalid; delete rest.className; delete rest.id;
    var id = p.id || (p.label ? rid('vc-ta-') : undefined);
    var cls = cx('vc-textarea', p.invalid ? 'vc-textarea--invalid' : '', p.className);
    var field = h('textarea', Object.assign({ id: id, className: cls }, rest));
    if (!p.label && !p.hint) return field;
    return h('div', { className: 'vc-field' },
      p.label ? h('label', { className: 'vc-label', htmlFor: id }, p.label) : null,
      field, p.hint ? h('span', { className: 'vc-hint' }, p.hint) : null);
  }

  function Select(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label; delete rest.hint; delete rest.options; delete rest.className; delete rest.id; delete rest.children;
    var id = p.id || (p.label ? rid('vc-sel-') : undefined);
    var opts = (p.options || []).map(function (o) { return typeof o === 'string' ? { value: o, label: o } : o; });
    var control = h('div', { className: 'vc-select' },
      h('select', Object.assign({ id: id, className: cx('vc-select__el', p.className) }, rest),
        opts.map(function (o) { return h('option', { key: o.value, value: o.value }, o.label); }), p.children),
      h('svg', { className: 'vc-select__chev', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': 'true' },
        h('path', { d: 'm6 9 6 6 6-6' })));
    if (!p.label && !p.hint) return control;
    return h('div', { className: 'vc-field' },
      p.label ? h('label', { className: 'vc-label', htmlFor: id }, p.label) : null,
      control, p.hint ? h('span', { className: 'vc-hint' }, p.hint) : null);
  }

  function Badge(props) {
    var p = props || {}, variant = p.variant || 'neutral';
    var rest = Object.assign({}, p);
    delete rest.variant; delete rest.square; delete rest.iconLeft; delete rest.className; delete rest.children;
    var cls = cx('vc-badge', 'vc-badge--' + variant, p.square ? 'vc-badge--square' : '', p.className);
    return h('span', Object.assign({ className: cls }, rest), p.iconLeft, p.children);
  }

  function Card(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.title; delete rest.overline; delete rest.actions; delete rest.flat;
    delete rest.className; delete rest.bodyClassName; delete rest.children;
    var hasHeader = p.title || p.overline || p.actions;
    return h('div', Object.assign({ className: cx('vc-card', p.flat ? 'vc-card--flat' : '', p.className) }, rest),
      hasHeader ? h('div', { className: 'vc-card__header' },
        h('div', null,
          p.overline ? h('div', { className: 'vc-card__overline' }, p.overline) : null,
          p.title ? h('div', { className: 'vc-card__title' }, p.title) : null),
        p.actions ? h('div', { style: { marginLeft: 'auto', display: 'flex', gap: 'var(--space-2)' } }, p.actions) : null) : null,
      h('div', { className: cx('vc-card__body', p.bodyClassName) }, p.children));
  }

  function Tabs(props) {
    var p = props || {}, items = p.items || [];
    return h('div', { className: cx('vc-tabs', p.className), role: 'tablist' },
      items.map(function (it) {
        return h('button', {
          key: it.id, role: 'tab', 'aria-selected': p.value === it.id,
          className: cx('vc-tab', p.value === it.id ? 'vc-tab--active' : ''),
          onClick: function () { p.onChange && p.onChange(it.id); }
        }, it.label);
      }));
  }

  function Spinner(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.size; delete rest.className;
    return h('span', Object.assign({ className: cx('vc-spinner', p.size === 'lg' ? 'vc-spinner--lg' : '', p.className), role: 'status', 'aria-label': 'Lädt' }, rest));
  }

  var LABELS = { ready: 'Bereit', indexing: 'Indexiert…', error: 'Fehler', idle: 'Inaktiv' };
  function StatusBadge(props) {
    var p = props || {}, status = p.status || 'idle';
    var rest = Object.assign({}, p);
    delete rest.status; delete rest.label; delete rest.className;
    return h('span', Object.assign({ className: cx('vc-status', 'vc-status--' + status, p.className) }, rest),
      h('span', { className: 'vc-status__dot' }), p.label || LABELS[status]);
  }

  function Citation(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.qid; delete rest.onClick; delete rest.className;
    var label = typeof p.qid === 'number' ? '[Q' + p.qid + ']' : p.qid;
    return h('a', Object.assign({ className: cx('vc-cite', p.className), role: 'button', tabIndex: 0, onClick: p.onClick }, rest), label);
  }

  function SourceRow(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.qid; delete rest.source; delete rest.page; delete rest.similarity; delete rest.className;
    var label = typeof p.qid === 'number' ? 'Q' + p.qid : p.qid;
    var meta = (p.page != null ? 'Seite ' + p.page : '') + (p.similarity != null ? '  ·  ' + Number(p.similarity).toFixed(3) : '');
    return h('div', Object.assign({ className: cx('vc-source', p.className) }, rest),
      h('span', { className: 'vc-source__qid' }, label),
      h('span', { className: 'vc-source__name' }, p.source),
      h('span', { className: 'vc-source__meta' }, meta));
  }

  function ParameterTable(props) {
    var p = props || {}, rows = p.rows || [];
    var rest = Object.assign({}, p);
    delete rest.rows; delete rest.header; delete rest.className;
    return h('table', Object.assign({ className: cx('vc-param-table', p.className) }, rest),
      p.header ? h('thead', null, h('tr', null,
        h('th', null, p.header[0] || 'Parameter'),
        h('th', { style: { textAlign: 'right' }, colSpan: 2 }, p.header[1] || 'Wert'))) : null,
      h('tbody', null, rows.map(function (r, i) {
        return h('tr', { key: i },
          h('td', { className: 'vc-param-table__key' }, r.key),
          h('td', { className: 'vc-param-table__val' }, r.value),
          h('td', { className: 'vc-param-table__unit' }, r.unit || ''));
      })));
  }

  function CodeBlock(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.caption; delete rest.children; delete rest.className;
    if (p.caption) {
      return h('div', { className: cx('vc-card', 'vc-card--flat', p.className), style: { overflow: 'hidden' } },
        h('div', { className: 'vc-code__caption' }, p.caption),
        h('pre', Object.assign({ className: 'vc-code', style: { border: 'none', borderRadius: 0 } }, rest), p.children));
    }
    return h('pre', Object.assign({ className: cx('vc-code', p.className) }, rest), p.children);
  }

  window[NS] = {
    Button: Button, IconButton: IconButton, Input: Input, Textarea: Textarea, Select: Select,
    Badge: Badge, Card: Card, Tabs: Tabs, Spinner: Spinner, StatusBadge: StatusBadge,
    Citation: Citation, SourceRow: SourceRow, ParameterTable: ParameterTable, CodeBlock: CodeBlock
  };
})();
