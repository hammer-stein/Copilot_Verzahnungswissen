/* @ds-bundle: {"format":3,"namespace":"VerzahnungsCopilotDesignSystem_c9990b","components":[{"name":"Citation","sourcePath":"components/copilot/Citation.jsx"},{"name":"CodeBlock","sourcePath":"components/copilot/CodeBlock.jsx"},{"name":"ParameterTable","sourcePath":"components/copilot/ParameterTable.jsx"},{"name":"SourceRow","sourcePath":"components/copilot/SourceRow.jsx"},{"name":"Badge","sourcePath":"components/data-display/Badge.jsx"},{"name":"Card","sourcePath":"components/data-display/Card.jsx"},{"name":"Spinner","sourcePath":"components/data-display/Spinner.jsx"},{"name":"StatusBadge","sourcePath":"components/data-display/StatusBadge.jsx"},{"name":"Tabs","sourcePath":"components/data-display/Tabs.jsx"},{"name":"Button","sourcePath":"components/forms/Button.jsx"},{"name":"IconButton","sourcePath":"components/forms/IconButton.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Textarea","sourcePath":"components/forms/Textarea.jsx"}],"sourceHashes":{"components/copilot/Citation.jsx":"fa6476537514","components/copilot/CodeBlock.jsx":"f9be1874ebd9","components/copilot/ParameterTable.jsx":"fc6432299443","components/copilot/SourceRow.jsx":"95d24d63c94b","components/data-display/Badge.jsx":"60dfcf868765","components/data-display/Card.jsx":"61b20bae4b06","components/data-display/Spinner.jsx":"cc47cfdf7e79","components/data-display/StatusBadge.jsx":"952002a1a4ff","components/data-display/Tabs.jsx":"5da8179f1604","components/forms/Button.jsx":"ba3d754fe69b","components/forms/IconButton.jsx":"40e25f76b24f","components/forms/Input.jsx":"963f1a3b62fd","components/forms/Select.jsx":"128b1dd5e1a6","components/forms/Textarea.jsx":"40e092a5122e","ds-shim.js":"7b7210fe4ca8","ui_kits/copilot/App.jsx":"aa9c4fb6325a","ui_kits/copilot/ChatView.jsx":"9065d6c47423","ui_kits/copilot/Composer.jsx":"97cc44af6617","ui_kits/copilot/Inspector.jsx":"89e260743c5f","ui_kits/copilot/Sidebar.jsx":"1bcd505846ec","ui_kits/copilot/TopBar.jsx":"acb8dc2f7d16","ui_kits/copilot/data.js":"6a865770cc6c","ui_kits/copilot/ui.jsx":"8e2026ad3fec"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.VerzahnungsCopilotDesignSystem_c9990b = window.VerzahnungsCopilotDesignSystem_c9990b || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/copilot/Citation.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Citation — inline source marker like [Q1]. Renders a clickable chip.
 */
function Citation({
  qid,
  onClick,
  className = '',
  ...rest
}) {
  const label = typeof qid === 'number' ? `[Q${qid}]` : qid;
  return /*#__PURE__*/React.createElement("a", _extends({
    className: ['vc-cite', className].filter(Boolean).join(' '),
    role: "button",
    tabIndex: 0,
    onClick: onClick,
    onKeyDown: e => {
      if ((e.key === 'Enter' || e.key === ' ') && onClick) {
        e.preventDefault();
        onClick(e);
      }
    }
  }, rest), label);
}
Object.assign(__ds_scope, { Citation });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/copilot/Citation.jsx", error: String((e && e.message) || e) }); }

// components/copilot/CodeBlock.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * CodeBlock — monospace block for JSON metadata, formulas or code.
 * Optional caption; preserves whitespace, horizontally scrolls.
 */
function CodeBlock({
  caption,
  children,
  className = '',
  ...rest
}) {
  if (caption) {
    return /*#__PURE__*/React.createElement("div", {
      className: ['vc-card', 'vc-card--flat', className].filter(Boolean).join(' '),
      style: {
        overflow: 'hidden'
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "vc-code__caption"
    }, caption), /*#__PURE__*/React.createElement("pre", _extends({
      className: "vc-code",
      style: {
        border: 'none',
        borderRadius: 0
      }
    }, rest), children));
  }
  return /*#__PURE__*/React.createElement("pre", _extends({
    className: ['vc-code', className].filter(Boolean).join(' ')
  }, rest), children);
}
Object.assign(__ds_scope, { CodeBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/copilot/CodeBlock.jsx", error: String((e && e.message) || e) }); }

// components/copilot/ParameterTable.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * ParameterTable — key / value / unit table for gear (CAD) metadata.
 * rows: [{ key, value, unit }].
 */
function ParameterTable({
  rows = [],
  header,
  className = '',
  ...rest
}) {
  return /*#__PURE__*/React.createElement("table", _extends({
    className: ['vc-param-table', className].filter(Boolean).join(' ')
  }, rest), header && /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null, header[0] || 'Parameter'), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right'
    },
    colSpan: 2
  }, header[1] || 'Wert'))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: "vc-param-table__key"
  }, r.key), /*#__PURE__*/React.createElement("td", {
    className: "vc-param-table__val"
  }, r.value), /*#__PURE__*/React.createElement("td", {
    className: "vc-param-table__unit"
  }, r.unit || '')))));
}
Object.assign(__ds_scope, { ParameterTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/copilot/ParameterTable.jsx", error: String((e && e.message) || e) }); }

// components/copilot/SourceRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * SourceRow — a retrieved chunk's provenance: [Q#] file — page — similarity.
 */
function SourceRow({
  qid,
  source,
  page,
  similarity,
  className = '',
  ...rest
}) {
  const label = typeof qid === 'number' ? `Q${qid}` : qid;
  return /*#__PURE__*/React.createElement("div", _extends({
    className: ['vc-source', className].filter(Boolean).join(' ')
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vc-source__qid"
  }, label), /*#__PURE__*/React.createElement("span", {
    className: "vc-source__name"
  }, source), /*#__PURE__*/React.createElement("span", {
    className: "vc-source__meta"
  }, page != null && `Seite ${page}`, similarity != null && `  ·  ${Number(similarity).toFixed(3)}`));
}
Object.assign(__ds_scope, { SourceRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/copilot/SourceRow.jsx", error: String((e && e.message) || e) }); }

// components/data-display/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Badge — compact status/category label.
 */
function Badge({
  variant = 'neutral',
  square = false,
  iconLeft,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vc-badge', `vc-badge--${variant}`, square ? 'vc-badge--square' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), iconLeft, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data-display/Badge.jsx", error: String((e && e.message) || e) }); }

// components/data-display/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Card — bordered surface with optional header (overline + title + actions).
 */
function Card({
  title,
  overline,
  actions,
  flat = false,
  className = '',
  bodyClassName = '',
  children,
  ...rest
}) {
  const cls = ['vc-card', flat ? 'vc-card--flat' : '', className].filter(Boolean).join(' ');
  const hasHeader = title || overline || actions;
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls
  }, rest), hasHeader && /*#__PURE__*/React.createElement("div", {
    className: "vc-card__header"
  }, /*#__PURE__*/React.createElement("div", null, overline && /*#__PURE__*/React.createElement("div", {
    className: "vc-card__overline"
  }, overline), title && /*#__PURE__*/React.createElement("div", {
    className: "vc-card__title"
  }, title)), actions && /*#__PURE__*/React.createElement("div", {
    style: {
      marginLeft: 'auto',
      display: 'flex',
      gap: 'var(--space-2)'
    }
  }, actions)), /*#__PURE__*/React.createElement("div", {
    className: ['vc-card__body', bodyClassName].filter(Boolean).join(' ')
  }, children));
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data-display/Card.jsx", error: String((e && e.message) || e) }); }

// components/data-display/Spinner.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Spinner — calm loading indicator. size: sm | lg. */
function Spinner({
  size = 'sm',
  className = '',
  ...rest
}) {
  const cls = ['vc-spinner', size === 'lg' ? 'vc-spinner--lg' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls,
    role: "status",
    "aria-label": "L\xE4dt"
  }, rest));
}
Object.assign(__ds_scope, { Spinner });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data-display/Spinner.jsx", error: String((e && e.message) || e) }); }

// components/data-display/StatusBadge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * StatusBadge — dot + label for document/indexing state.
 * status: ready | indexing | error | idle.
 */
const LABELS = {
  ready: 'Bereit',
  indexing: 'Indexiert…',
  error: 'Fehler',
  idle: 'Inaktiv'
};
function StatusBadge({
  status = 'idle',
  label,
  className = '',
  ...rest
}) {
  const cls = ['vc-status', `vc-status--${status}`, className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "vc-status__dot"
  }), label || LABELS[status]);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data-display/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/data-display/Tabs.jsx
try { (() => {
/**
 * Tabs — controlled tab strip. items: [{ id, label }]. Calls onChange(id).
 */
function Tabs({
  items = [],
  value,
  onChange,
  className = ''
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: ['vc-tabs', className].filter(Boolean).join(' '),
    role: "tablist"
  }, items.map(it => /*#__PURE__*/React.createElement("button", {
    key: it.id,
    role: "tab",
    "aria-selected": value === it.id,
    className: ['vc-tab', value === it.id ? 'vc-tab--active' : ''].filter(Boolean).join(' '),
    onClick: () => onChange && onChange(it.id)
  }, it.label)));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data-display/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/forms/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Button — primary action control for the copilot UI.
 * Variants: primary (KIT green), secondary, ghost, danger. Sizes: sm | md | lg.
 */
function Button({
  variant = 'primary',
  size = 'md',
  type = 'button',
  iconLeft,
  iconRight,
  disabled = false,
  className = '',
  children,
  ...rest
}) {
  const cls = ['vc-btn', `vc-btn--${variant}`, size !== 'md' ? `vc-btn--${size}` : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    className: cls,
    disabled: disabled
  }, rest), iconLeft, children != null && /*#__PURE__*/React.createElement("span", null, children), iconRight);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Button.jsx", error: String((e && e.message) || e) }); }

// components/forms/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * IconButton — square, icon-only control. Pass a Lucide <svg> as children.
 * Variants via `active`; sizes sm | md.
 */
function IconButton({
  size = 'md',
  active = false,
  className = '',
  title,
  children,
  ...rest
}) {
  const cls = ['vc-icon-btn', size === 'sm' ? 'vc-icon-btn--sm' : '', active ? 'vc-icon-btn--active' : '', className].filter(Boolean).join(' ');
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: cls,
    title: title,
    "aria-label": title
  }, rest), children);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Input — single-line text field with optional label and hint.
 * Use `mono` for parameter/number entry (tabular figures).
 */
function Input({
  label,
  hint,
  invalid = false,
  mono = false,
  id,
  className = '',
  ...rest
}) {
  const inputId = id || (label ? `vc-in-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const cls = ['vc-input', mono ? 'vc-input--mono' : '', invalid ? 'vc-input--invalid' : '', className].filter(Boolean).join(' ');
  const field = /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    className: cls,
    "aria-invalid": invalid || undefined
  }, rest));
  if (!label && !hint) return field;
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vc-label",
    htmlFor: inputId
  }, label), field, hint && /*#__PURE__*/React.createElement("span", {
    className: "vc-hint"
  }, hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Select — native select with custom chevron. Pass options or children.
 * options: [{ value, label }] or string[].
 */
function Select({
  label,
  hint,
  options,
  id,
  className = '',
  children,
  ...rest
}) {
  const selId = id || (label ? `vc-sel-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const opts = (options || []).map(o => typeof o === 'string' ? {
    value: o,
    label: o
  } : o);
  const control = /*#__PURE__*/React.createElement("div", {
    className: "vc-select"
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: selId,
    className: ['vc-select__el', className].filter(Boolean).join(' ')
  }, rest), opts.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label)), children), /*#__PURE__*/React.createElement("svg", {
    className: "vc-select__chev",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": "true"
  }, /*#__PURE__*/React.createElement("path", {
    d: "m6 9 6 6 6-6"
  })));
  if (!label && !hint) return control;
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vc-label",
    htmlFor: selId
  }, label), control, hint && /*#__PURE__*/React.createElement("span", {
    className: "vc-hint"
  }, hint));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Textarea.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Textarea — multi-line input for questions / free text.
 */
function Textarea({
  label,
  hint,
  invalid = false,
  id,
  className = '',
  ...rest
}) {
  const taId = id || (label ? `vc-ta-${Math.random().toString(36).slice(2, 8)}` : undefined);
  const cls = ['vc-textarea', invalid ? 'vc-textarea--invalid' : '', className].filter(Boolean).join(' ');
  const field = /*#__PURE__*/React.createElement("textarea", _extends({
    id: taId,
    className: cls,
    "aria-invalid": invalid || undefined
  }, rest));
  if (!label && !hint) return field;
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-field"
  }, label && /*#__PURE__*/React.createElement("label", {
    className: "vc-label",
    htmlFor: taId
  }, label), field, hint && /*#__PURE__*/React.createElement("span", {
    className: "vc-hint"
  }, hint));
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Textarea.jsx", error: String((e && e.message) || e) }); }

// ds-shim.js
try { (() => {
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
  function cx() {
    return Array.prototype.filter.call(arguments, Boolean).join(' ');
  }
  function rid(p) {
    return p + Math.random().toString(36).slice(2, 8);
  }
  function Button(props) {
    var p = props || {},
      variant = p.variant || 'primary',
      size = p.size || 'md';
    var rest = Object.assign({}, p);
    delete rest.variant;
    delete rest.size;
    delete rest.iconLeft;
    delete rest.iconRight;
    delete rest.className;
    delete rest.children;
    var cls = cx('vc-btn', 'vc-btn--' + variant, size !== 'md' ? 'vc-btn--' + size : '', p.className);
    return h('button', Object.assign({
      type: p.type || 'button',
      className: cls,
      disabled: p.disabled
    }, rest), p.iconLeft, p.children != null ? h('span', null, p.children) : null, p.iconRight);
  }
  function IconButton(props) {
    var p = props || {},
      size = p.size || 'md';
    var rest = Object.assign({}, p);
    delete rest.size;
    delete rest.active;
    delete rest.className;
    delete rest.children;
    delete rest.title;
    var cls = cx('vc-icon-btn', size === 'sm' ? 'vc-icon-btn--sm' : '', p.active ? 'vc-icon-btn--active' : '', p.className);
    return h('button', Object.assign({
      type: 'button',
      className: cls,
      title: p.title,
      'aria-label': p.title
    }, rest), p.children);
  }
  function Input(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label;
    delete rest.hint;
    delete rest.invalid;
    delete rest.mono;
    delete rest.className;
    delete rest.id;
    var id = p.id || (p.label ? rid('vc-in-') : undefined);
    var cls = cx('vc-input', p.mono ? 'vc-input--mono' : '', p.invalid ? 'vc-input--invalid' : '', p.className);
    var field = h('input', Object.assign({
      id: id,
      className: cls,
      'aria-invalid': p.invalid || undefined
    }, rest));
    if (!p.label && !p.hint) return field;
    return h('div', {
      className: 'vc-field'
    }, p.label ? h('label', {
      className: 'vc-label',
      htmlFor: id
    }, p.label) : null, field, p.hint ? h('span', {
      className: 'vc-hint'
    }, p.hint) : null);
  }
  function Textarea(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label;
    delete rest.hint;
    delete rest.invalid;
    delete rest.className;
    delete rest.id;
    var id = p.id || (p.label ? rid('vc-ta-') : undefined);
    var cls = cx('vc-textarea', p.invalid ? 'vc-textarea--invalid' : '', p.className);
    var field = h('textarea', Object.assign({
      id: id,
      className: cls
    }, rest));
    if (!p.label && !p.hint) return field;
    return h('div', {
      className: 'vc-field'
    }, p.label ? h('label', {
      className: 'vc-label',
      htmlFor: id
    }, p.label) : null, field, p.hint ? h('span', {
      className: 'vc-hint'
    }, p.hint) : null);
  }
  function Select(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.label;
    delete rest.hint;
    delete rest.options;
    delete rest.className;
    delete rest.id;
    delete rest.children;
    var id = p.id || (p.label ? rid('vc-sel-') : undefined);
    var opts = (p.options || []).map(function (o) {
      return typeof o === 'string' ? {
        value: o,
        label: o
      } : o;
    });
    var control = h('div', {
      className: 'vc-select'
    }, h('select', Object.assign({
      id: id,
      className: cx('vc-select__el', p.className)
    }, rest), opts.map(function (o) {
      return h('option', {
        key: o.value,
        value: o.value
      }, o.label);
    }), p.children), h('svg', {
      className: 'vc-select__chev',
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      strokeWidth: 2,
      strokeLinecap: 'round',
      strokeLinejoin: 'round',
      'aria-hidden': 'true'
    }, h('path', {
      d: 'm6 9 6 6 6-6'
    })));
    if (!p.label && !p.hint) return control;
    return h('div', {
      className: 'vc-field'
    }, p.label ? h('label', {
      className: 'vc-label',
      htmlFor: id
    }, p.label) : null, control, p.hint ? h('span', {
      className: 'vc-hint'
    }, p.hint) : null);
  }
  function Badge(props) {
    var p = props || {},
      variant = p.variant || 'neutral';
    var rest = Object.assign({}, p);
    delete rest.variant;
    delete rest.square;
    delete rest.iconLeft;
    delete rest.className;
    delete rest.children;
    var cls = cx('vc-badge', 'vc-badge--' + variant, p.square ? 'vc-badge--square' : '', p.className);
    return h('span', Object.assign({
      className: cls
    }, rest), p.iconLeft, p.children);
  }
  function Card(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.title;
    delete rest.overline;
    delete rest.actions;
    delete rest.flat;
    delete rest.className;
    delete rest.bodyClassName;
    delete rest.children;
    var hasHeader = p.title || p.overline || p.actions;
    return h('div', Object.assign({
      className: cx('vc-card', p.flat ? 'vc-card--flat' : '', p.className)
    }, rest), hasHeader ? h('div', {
      className: 'vc-card__header'
    }, h('div', null, p.overline ? h('div', {
      className: 'vc-card__overline'
    }, p.overline) : null, p.title ? h('div', {
      className: 'vc-card__title'
    }, p.title) : null), p.actions ? h('div', {
      style: {
        marginLeft: 'auto',
        display: 'flex',
        gap: 'var(--space-2)'
      }
    }, p.actions) : null) : null, h('div', {
      className: cx('vc-card__body', p.bodyClassName)
    }, p.children));
  }
  function Tabs(props) {
    var p = props || {},
      items = p.items || [];
    return h('div', {
      className: cx('vc-tabs', p.className),
      role: 'tablist'
    }, items.map(function (it) {
      return h('button', {
        key: it.id,
        role: 'tab',
        'aria-selected': p.value === it.id,
        className: cx('vc-tab', p.value === it.id ? 'vc-tab--active' : ''),
        onClick: function () {
          p.onChange && p.onChange(it.id);
        }
      }, it.label);
    }));
  }
  function Spinner(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.size;
    delete rest.className;
    return h('span', Object.assign({
      className: cx('vc-spinner', p.size === 'lg' ? 'vc-spinner--lg' : '', p.className),
      role: 'status',
      'aria-label': 'Lädt'
    }, rest));
  }
  var LABELS = {
    ready: 'Bereit',
    indexing: 'Indexiert…',
    error: 'Fehler',
    idle: 'Inaktiv'
  };
  function StatusBadge(props) {
    var p = props || {},
      status = p.status || 'idle';
    var rest = Object.assign({}, p);
    delete rest.status;
    delete rest.label;
    delete rest.className;
    return h('span', Object.assign({
      className: cx('vc-status', 'vc-status--' + status, p.className)
    }, rest), h('span', {
      className: 'vc-status__dot'
    }), p.label || LABELS[status]);
  }
  function Citation(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.qid;
    delete rest.onClick;
    delete rest.className;
    var label = typeof p.qid === 'number' ? '[Q' + p.qid + ']' : p.qid;
    return h('a', Object.assign({
      className: cx('vc-cite', p.className),
      role: 'button',
      tabIndex: 0,
      onClick: p.onClick
    }, rest), label);
  }
  function SourceRow(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.qid;
    delete rest.source;
    delete rest.page;
    delete rest.similarity;
    delete rest.className;
    var label = typeof p.qid === 'number' ? 'Q' + p.qid : p.qid;
    var meta = (p.page != null ? 'Seite ' + p.page : '') + (p.similarity != null ? '  ·  ' + Number(p.similarity).toFixed(3) : '');
    return h('div', Object.assign({
      className: cx('vc-source', p.className)
    }, rest), h('span', {
      className: 'vc-source__qid'
    }, label), h('span', {
      className: 'vc-source__name'
    }, p.source), h('span', {
      className: 'vc-source__meta'
    }, meta));
  }
  function ParameterTable(props) {
    var p = props || {},
      rows = p.rows || [];
    var rest = Object.assign({}, p);
    delete rest.rows;
    delete rest.header;
    delete rest.className;
    return h('table', Object.assign({
      className: cx('vc-param-table', p.className)
    }, rest), p.header ? h('thead', null, h('tr', null, h('th', null, p.header[0] || 'Parameter'), h('th', {
      style: {
        textAlign: 'right'
      },
      colSpan: 2
    }, p.header[1] || 'Wert'))) : null, h('tbody', null, rows.map(function (r, i) {
      return h('tr', {
        key: i
      }, h('td', {
        className: 'vc-param-table__key'
      }, r.key), h('td', {
        className: 'vc-param-table__val'
      }, r.value), h('td', {
        className: 'vc-param-table__unit'
      }, r.unit || ''));
    })));
  }
  function CodeBlock(props) {
    var p = props || {};
    var rest = Object.assign({}, p);
    delete rest.caption;
    delete rest.children;
    delete rest.className;
    if (p.caption) {
      return h('div', {
        className: cx('vc-card', 'vc-card--flat', p.className),
        style: {
          overflow: 'hidden'
        }
      }, h('div', {
        className: 'vc-code__caption'
      }, p.caption), h('pre', Object.assign({
        className: 'vc-code',
        style: {
          border: 'none',
          borderRadius: 0
        }
      }, rest), p.children));
    }
    return h('pre', Object.assign({
      className: cx('vc-code', p.className)
    }, rest), p.children);
  }
  window[NS] = {
    Button: Button,
    IconButton: IconButton,
    Input: Input,
    Textarea: Textarea,
    Select: Select,
    Badge: Badge,
    Card: Card,
    Tabs: Tabs,
    Spinner: Spinner,
    StatusBadge: StatusBadge,
    Citation: Citation,
    SourceRow: SourceRow,
    ParameterTable: ParameterTable,
    CodeBlock: CodeBlock
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ds-shim.js", error: String((e && e.message) || e) }); }

// ui_kits/copilot/App.jsx
try { (() => {
/* App shell: sidebar + chat + composer + inspector. Mock interactions. */
function App() {
  const D = window.VC_DATA;
  const {
    Citation,
    ParameterTable
  } = window.VerzahnungsCopilotDesignSystem_c9990b;

  /* ----- per-chat transcripts (each history entry has its own conversation) ----- */
  const transcriptC1 = [{
    role: 'user',
    text: 'Welche Werkstoffe eignen sich für einsatzgehärtete Stirnräder, und welche Randschichthärte ist üblich?'
  }, {
    role: 'assistant',
    title: 'Werkstoffe & Randschichthärte für einsatzgehärtete Stirnräder',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "F\xFCr einsatzgeh\xE4rtete Stirnr\xE4der werden niedriglegierte Einsatzst\xE4hle wie ", /*#__PURE__*/React.createElement("strong", null, "16MnCr5"), " und", /*#__PURE__*/React.createElement("strong", null, " 20MnCr5"), " empfohlen ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), ". Bei h\xF6heren Belastungen kommt auch ", /*#__PURE__*/React.createElement("strong", null, "18CrNiMo7-6"), " zum Einsatz ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), "."), /*#__PURE__*/React.createElement("p", null, "Die Randschichth\xE4rte nach dem Einsatzh\xE4rten liegt typischerweise bei ", /*#__PURE__*/React.createElement("strong", null, "58\u201362 HRC"), ", w\xE4hrend der z\xE4he Kern bei etwa 30\u201342 HRC verbleibt ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ". Die Einsatzh\xE4rtungstiefe (CHD) wird auf den Modul abgestimmt (Richtwert CHD \u2248 0,15 \xB7 m) ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), "."), /*#__PURE__*/React.createElement("p", {
      className: "vc-answer__nosrc"
    }, "Zur konkreten Lebensdauer dieses Bauteils l\xE4sst sich aus den verf\xFCgbaren Quellen keine Aussage treffen.")),
    sources: [{
      qid: 1,
      source: 'Werkstoffkunde_Verzahnung.pdf',
      page: 17,
      similarity: 0.871
    }, {
      qid: 2,
      source: 'DIN3990_Tragfaehigkeit.pdf',
      page: 42,
      similarity: 0.804
    }]
  }, {
    role: 'user',
    text: 'Gib mir die zulässigen Toleranzen für Qualität 7 tabellarisch aus.'
  }, {
    role: 'assistant',
    title: 'Zulässige Toleranzen — Verzahnungsqualität 7 (ISO 1328)',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "F\xFCr Qualit\xE4t 7 nach ISO 1328 gelten bei Modul 2,5 und Teilkreis 85 mm folgende Richtwerte ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), ":"), /*#__PURE__*/React.createElement(ParameterTable, {
      header: ['Toleranz', 'Wert'],
      rows: [{
        key: 'Einzelteilungsabw. fp',
        value: '11',
        unit: 'µm'
      }, {
        key: 'Teilungs-Gesamtabw. Fp',
        value: '32',
        unit: 'µm'
      }, {
        key: 'Profil-Gesamtabw. Fα',
        value: '13',
        unit: 'µm'
      }, {
        key: 'Flankenlinienabw. Fβ',
        value: '15',
        unit: 'µm'
      }, {
        key: 'Rundlaufabw. Fr',
        value: '25',
        unit: 'µm'
      }]
    }), /*#__PURE__*/React.createElement("p", {
      style: {
        marginTop: 12
      }
    }, "Die Werte sind Obergrenzen; die Pr\xFCfung erfolgt nach Abschnitt 5 der Norm ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ".")),
    sources: [{
      qid: 1,
      source: 'ISO1328_Toleranzen.pdf',
      page: 8,
      similarity: 0.889
    }, {
      qid: 2,
      source: 'ISO1328_Toleranzen.pdf',
      page: 11,
      similarity: 0.842
    }]
  }];
  const transcriptC2 = [{
    role: 'user',
    text: 'Wie wähle ich den Profilverschiebungsfaktor x für mein Stirnrad aus?'
  }, {
    role: 'assistant',
    title: 'Auslegung des Profilverschiebungsfaktors x',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "Eine positive Profilverschiebung (", /*#__PURE__*/React.createElement("strong", null, "x > 0"), ") vergr\xF6\xDFert die Zahnfu\xDFdicke und erh\xF6ht damit die Zahnfu\xDFtragf\xE4higkeit; sie wird au\xDFerdem zur Vermeidung von Unterschnitt bei kleinen Z\xE4hnezahlen eingesetzt ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), "."), /*#__PURE__*/React.createElement("p", null, "Als Richtwert zur Unterschnittvermeidung gilt ", /*#__PURE__*/React.createElement("strong", null, "x \u2265 (14 \u2212 z) / 17"), ". Bei Paarungen wird die Summe der Verschiebungen (x\u2081 + x\u2082) auf den geforderten Achsabstand abgestimmt ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), "."), /*#__PURE__*/React.createElement("p", {
      className: "vc-answer__nosrc"
    }, "Eine bauteilspezifische Optimierung erfordert zus\xE4tzliche Lastannahmen.")),
    sources: [{
      qid: 1,
      source: 'Werkstoffkunde_Verzahnung.pdf',
      page: 24,
      similarity: 0.857
    }, {
      qid: 2,
      source: 'DIN3990_Tragfaehigkeit.pdf',
      page: 31,
      similarity: 0.821
    }]
  }];
  const transcriptC3 = [{
    role: 'user',
    text: 'Welchen Einfluss hat der Schrägungswinkel auf die Laufruhe?'
  }, {
    role: 'assistant',
    title: 'Schrägungswinkel β und Laufruhe',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "Ein gr\xF6\xDFerer Schr\xE4gungswinkel erh\xF6ht die ", /*#__PURE__*/React.createElement("strong", null, "Sprung\xFCberdeckung \u03B5\u03B2"), " und damit die Gesamt\xFCberdeckung. Dadurch sind stets mehr Z\xE4hne gleichzeitig im Eingriff, was Laufruhe und Ger\xE4uschverhalten deutlich verbessert ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), "."), /*#__PURE__*/React.createElement("p", null, "Nachteilig sind die entstehenden ", /*#__PURE__*/React.createElement("strong", null, "Axialkr\xE4fte"), ", die eine entsprechende Lagerauslegung erfordern. \xDCbliche Werte liegen bei \u03B2 = 8\xB0\u201320\xB0 ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ".")),
    sources: [{
      qid: 1,
      source: 'DIN3990_Tragfaehigkeit.pdf',
      page: 58,
      similarity: 0.834
    }, {
      qid: 2,
      source: 'Werkstoffkunde_Verzahnung.pdf',
      page: 12,
      similarity: 0.796
    }]
  }];
  const transcriptC4 = [{
    role: 'user',
    text: 'Worin unterscheiden sich die Toleranzklassen 6, 7 und 8 nach ISO 1328?'
  }, {
    role: 'assistant',
    title: 'Vergleich der Toleranzklassen 6 / 7 / 8 (ISO 1328)',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "Eine niedrigere Qualit\xE4tszahl bedeutet engere Toleranzen. Bei Modul 2,5 / Teilkreis 85 mm ergeben sich u. a. ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), ":"), /*#__PURE__*/React.createElement(ParameterTable, {
      header: ['Kenngröße', 'Wert'],
      rows: [{
        key: 'Fp — Qualität 6',
        value: '23',
        unit: 'µm'
      }, {
        key: 'Fp — Qualität 7',
        value: '32',
        unit: 'µm'
      }, {
        key: 'Fp — Qualität 8',
        value: '45',
        unit: 'µm'
      }, {
        key: 'Fα — Qualität 7',
        value: '13',
        unit: 'µm'
      }, {
        key: 'Fβ — Qualität 7',
        value: '15',
        unit: 'µm'
      }]
    }), /*#__PURE__*/React.createElement("p", {
      style: {
        marginTop: 12
      }
    }, "Qualit\xE4t 6 wird f\xFCr hochbelastete Getriebe, Qualit\xE4t 8 f\xFCr untergeordnete Anwendungen genutzt ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ".")),
    sources: [{
      qid: 1,
      source: 'ISO1328_Toleranzen.pdf',
      page: 8,
      similarity: 0.901
    }, {
      qid: 2,
      source: 'ISO1328_Toleranzen.pdf',
      page: 14,
      similarity: 0.838
    }]
  }];
  const transcriptC5 = [{
    role: 'user',
    text: 'Welche Schnittparameter empfiehlst du beim Wälzfräsen von Modul 3?'
  }, {
    role: 'assistant',
    title: 'Schnittparameter Wälzfräsen — Modul 3',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "F\xFCr HSS-W\xE4lzfr\xE4ser und einen Einsatzstahl wie 16MnCr5 gelten folgende Richtwerte ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), ":"), /*#__PURE__*/React.createElement(ParameterTable, {
      header: ['Parameter', 'Wert'],
      rows: [{
        key: 'Schnittgeschwindigkeit vc',
        value: '45',
        unit: 'm/min'
      }, {
        key: 'Axialvorschub fa',
        value: '2,5',
        unit: 'mm/U'
      }, {
        key: 'Schnitttiefe (Vollschnitt)',
        value: '6,75',
        unit: 'mm'
      }, {
        key: 'Shift-Strategie',
        value: 'aktiv',
        unit: ''
      }]
    }), /*#__PURE__*/React.createElement("p", {
      style: {
        marginTop: 12
      }
    }, "Bei Hartmetallfr\xE4sern l\xE4sst sich vc deutlich steigern; die Standzeit profitiert von einer Shift-Strategie ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ".")),
    sources: [{
      qid: 1,
      source: 'Fraesparameter_Datenblatt.pdf',
      page: 4,
      similarity: 0.882
    }, {
      qid: 2,
      source: 'Fraesparameter_Datenblatt.pdf',
      page: 9,
      similarity: 0.815
    }]
  }];
  const transcriptC6 = [{
    role: 'user',
    text: 'Wie läuft der Tragfähigkeitsnachweis nach DIN 3990 ab?'
  }, {
    role: 'assistant',
    title: 'Tragfähigkeitsnachweis nach DIN 3990',
    body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "Der Nachweis umfasst zwei Hauptkriterien: die ", /*#__PURE__*/React.createElement("strong", null, "Zahnfu\xDFtragf\xE4higkeit"), " (Methode B \xFCber \u03C3F und \u03C3FP) und die", /*#__PURE__*/React.createElement("strong", null, " Gr\xFCbchentragf\xE4higkeit"), " (Flankenpressung \u03C3H gegen \u03C3HP) ", /*#__PURE__*/React.createElement(Citation, {
      qid: 1
    }), "."), /*#__PURE__*/React.createElement("p", null, "Ber\xFCcksichtigt werden Anwendungs-, Dynamik-, Breiten- und Stirnfaktoren (KA, KV, KF\u03B2, KF\u03B1). Die erforderlichen Sicherheiten betragen \xFCblicherweise SF \u2248 1,4 und SH \u2248 1,0\u20131,3 ", /*#__PURE__*/React.createElement(Citation, {
      qid: 2
    }), ".")),
    sources: [{
      qid: 1,
      source: 'DIN3990_Tragfaehigkeit.pdf',
      page: 6,
      similarity: 0.913
    }, {
      qid: 2,
      source: 'DIN3990_Tragfaehigkeit.pdf',
      page: 71,
      similarity: 0.846
    }]
  }];
  const initialTranscripts = {
    c1: transcriptC1,
    c2: transcriptC2,
    c3: transcriptC3,
    c4: transcriptC4,
    c5: transcriptC5,
    c6: transcriptC6
  };
  const [dark, setDark] = React.useState(false);
  const [inspectorOpen, setInspectorOpen] = React.useState(true);
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [chats, setChats] = React.useState(D.chats);
  const [activePart, setActivePart] = React.useState(D.activePart);
  const [transcripts, setTranscripts] = React.useState(initialTranscripts);
  const [activeChat, setActiveChat] = React.useState('c1');
  const [format, setFormat] = React.useState('standard');
  const [generating, setGenerating] = React.useState(false);
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  }, [dark]);
  const messages = activeChat ? transcripts[activeChat] || [] : [];
  const appendMsg = (chatId, msg) => {
    setTranscripts(t => ({
      ...t,
      [chatId]: [...(t[chatId] || []), msg]
    }));
  };
  const send = text => {
    let chatId = activeChat;
    /* Starting from the home screen creates a brand-new, persistent chat. */
    if (!chatId) {
      chatId = 'c' + Date.now();
      const title = text.length > 46 ? text.slice(0, 43) + '…' : text;
      setChats(cs => [{
        id: chatId,
        title,
        when: 'Heute'
      }, ...cs]);
      setTranscripts(t => ({
        ...t,
        [chatId]: []
      }));
      setActiveChat(chatId);
    }
    appendMsg(chatId, {
      role: 'user',
      text
    });
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      appendMsg(chatId, {
        role: 'assistant',
        title: text.length > 64 ? text.slice(0, 61) + '…' : text,
        body: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("p", null, "Auf Basis der indexierten Quellen und der Bauteildaten (", D.gear.verzahnungstyp, ", Modul ", D.gear.modul, ",", ' ', "z = ", D.gear.zaehnezahl, ") ergibt sich: die ma\xDFgeblichen Kenngr\xF6\xDFen sind dokumentiert und normbezogen nachvollziehbar ", /*#__PURE__*/React.createElement(Citation, {
          qid: 1
        }), ". F\xFCr die konkrete Auslegung ist der Eingriffswinkel von 20\xB0 und die Werkstoffpaarung ", D.gear.werkstoff, " zu ber\xFCcksichtigen ", /*#__PURE__*/React.createElement(Citation, {
          qid: 2
        }), "."), /*#__PURE__*/React.createElement("p", {
          className: "vc-answer__nosrc"
        }, "Weiterf\xFChrende Aussagen erfordern zus\xE4tzliche Dokumente in der Wissensbasis.")),
        sources: [{
          qid: 1,
          source: 'DIN3990_Tragfaehigkeit.pdf',
          page: 23,
          similarity: 0.812
        }, {
          qid: 2,
          source: 'Werkstoffkunde_Verzahnung.pdf',
          page: 9,
          similarity: 0.777
        }]
      });
    }, 1400);
  };
  const goHome = () => {
    setActiveChat(null);
    setSidebarOpen(false);
  };
  const newChat = () => {
    setActiveChat(null);
  };

  /* STEP / CAD upload — the user only uploads their part; the Copilot then
     answers questions about it. The large RAG knowledge base stays in the
     background and is never listed; only used sources surface per answer. */
  const uploadStep = file => {
    if (!file) return;
    setActivePart({
      name: file.name,
      status: 'indexing'
    });
    setTimeout(() => {
      setActivePart({
        name: file.name,
        status: 'ready'
      });
    }, 2600);
  };
  return /*#__PURE__*/React.createElement("div", {
    className: 'vc-shell' + (inspectorOpen ? ' vc-shell--inspector' : '') + (sidebarOpen ? ' vc-shell--sidebar-open' : '')
  }, /*#__PURE__*/React.createElement(Sidebar, {
    chats: chats,
    activePart: activePart,
    knowledgeBase: D.knowledgeBase,
    activeChat: activeChat,
    onSelectChat: id => {
      setActiveChat(id);
      setSidebarOpen(false);
    },
    onNewChat: newChat,
    onHome: goHome,
    onUploadStep: uploadStep
  }), /*#__PURE__*/React.createElement("div", {
    className: "vc-main"
  }, /*#__PURE__*/React.createElement(TopBar, {
    gear: D.gear,
    dark: dark,
    onToggleTheme: () => setDark(v => !v),
    inspectorOpen: inspectorOpen,
    onToggleInspector: () => setInspectorOpen(v => !v),
    onToggleSidebar: () => setSidebarOpen(v => !v)
  }), messages.length === 0 ? /*#__PURE__*/React.createElement(EmptyState, {
    onPick: send
  }) : /*#__PURE__*/React.createElement(ChatView, {
    key: activeChat,
    messages: messages,
    generating: generating
  }), /*#__PURE__*/React.createElement(Composer, {
    onSend: send,
    format: format,
    onFormat: setFormat,
    formats: D.formats,
    onUploadStep: uploadStep
  })), inspectorOpen && /*#__PURE__*/React.createElement(Inspector, {
    gear: D.gear,
    onClose: () => setInspectorOpen(false)
  }), sidebarOpen && /*#__PURE__*/React.createElement("div", {
    className: "vc-scrim",
    onClick: () => setSidebarOpen(false)
  }));
}
function EmptyState({
  onPick
}) {
  const suggestions = ['Wie wirkt sich die Profilverschiebung auf die Zahnfußtragfähigkeit aus?', 'Vergleiche Wälzfräsen und Wälzstoßen für Modul 3.', 'Welche Härteverfahren sind für 42CrMo4 geeignet?'];
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-empty"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-empty__icon"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "cog",
    size: 34
  })), /*#__PURE__*/React.createElement("h1", {
    className: "vc-empty__title"
  }, "Womit kann ich helfen?"), /*#__PURE__*/React.createElement("p", {
    className: "vc-empty__sub"
  }, "Antworten ausschlie\xDFlich aus Ihrer indexierten Wissensbasis \u2014 mit vollst\xE4ndiger Quellenangabe."), /*#__PURE__*/React.createElement("div", {
    className: "vc-empty__chips"
  }, suggestions.map((s, i) => /*#__PURE__*/React.createElement("button", {
    key: i,
    className: "vc-suggest",
    onClick: () => onPick(s)
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-suggest__ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "sparkles",
    size: 15
  })), s))));
}
Object.assign(window, {
  App,
  EmptyState
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/ChatView.jsx
try { (() => {
/* Main chat transcript: user questions + grounded AI answer cards. */
function UserMessage({
  text
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-msg vc-msg--user"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-bubble vc-bubble--user"
  }, text));
}
function AssistantMessage({
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-msg vc-msg--ai"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-msg__avatar vc-msg__avatar--ai"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "cog",
    size: 17
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-msg__body"
  }, children));
}
function SourcesAccordion({
  sources
}) {
  const {
    SourceRow
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [open, setOpen] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-sources"
  }, /*#__PURE__*/React.createElement("button", {
    className: "vc-sources__toggle",
    onClick: () => setOpen(!open)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "book-open",
    size: 15
  }), "Quellen", /*#__PURE__*/React.createElement("span", {
    className: "vc-sources__count"
  }, sources.length), /*#__PURE__*/React.createElement(Icon, {
    name: open ? 'chevron-up' : 'chevron-down',
    size: 15,
    style: {
      marginLeft: open ? 0 : 0
    }
  })), open && /*#__PURE__*/React.createElement("div", {
    className: "vc-sources__list"
  }, sources.map((s, i) => /*#__PURE__*/React.createElement(SourceRow, {
    key: i,
    qid: s.qid,
    source: s.source,
    page: s.page,
    similarity: s.similarity
  }))));
}
function Answer({
  title,
  children,
  sources
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-answer-wrap"
  }, title && /*#__PURE__*/React.createElement("div", {
    className: "vc-answer-title"
  }, title), /*#__PURE__*/React.createElement("div", {
    className: "vc-answer"
  }, children), sources && /*#__PURE__*/React.createElement(SourcesAccordion, {
    sources: sources
  }));
}
function ChatView({
  messages,
  generating
}) {
  const {
    Spinner
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const endRef = React.useRef(null);
  React.useEffect(() => {
    if (endRef.current) endRef.current.parentNode.scrollTop = endRef.current.offsetTop;
  }, [messages.length, generating]);
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-chat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-chat__inner"
  }, messages.map((m, i) => m.role === 'user' ? /*#__PURE__*/React.createElement(UserMessage, {
    key: i,
    text: m.text
  }) : /*#__PURE__*/React.createElement(AssistantMessage, {
    key: i
  }, /*#__PURE__*/React.createElement(Answer, {
    title: m.title,
    sources: m.sources
  }, m.body))), generating && /*#__PURE__*/React.createElement("div", {
    className: "vc-msg vc-msg--ai"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-msg__avatar vc-msg__avatar--ai"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "cog",
    size: 17
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-generating"
  }, /*#__PURE__*/React.createElement(Spinner, null), " Antwort wird aus den Quellen generiert\u2026")), /*#__PURE__*/React.createElement("div", {
    ref: endRef
  })));
}
Object.assign(window, {
  ChatView,
  Answer,
  UserMessage,
  AssistantMessage
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/ChatView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/Composer.jsx
try { (() => {
/* Sticky composer: question field + format select + send. Strict-RAG note. */
function Composer({
  onSend,
  format,
  onFormat,
  formats,
  onUploadStep
}) {
  const {
    IconButton,
    Select
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [value, setValue] = React.useState('');
  const taRef = React.useRef(null);
  const fileRef = React.useRef(null);
  const pickFile = () => {
    if (fileRef.current) fileRef.current.click();
  };
  const onFile = e => {
    const f = e.target.files && e.target.files[0];
    if (f && onUploadStep) onUploadStep(f);
    e.target.value = '';
  };
  const submit = () => {
    const v = value.trim();
    if (!v) return;
    onSend(v);
    setValue('');
    if (taRef.current) taRef.current.style.height = 'auto';
  };
  const onKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };
  const autosize = e => {
    setValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-composer"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-composer__box"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-composer__row"
  }, /*#__PURE__*/React.createElement("input", {
    ref: fileRef,
    type: "file",
    accept: ".step,.stp,.stp242,.p21,.iges,.igs,model/step",
    style: {
      display: 'none'
    },
    onChange: onFile
  }), /*#__PURE__*/React.createElement("button", {
    className: "vc-composer__attach",
    title: "CAD- / STEP-Datei anh\xE4ngen",
    onClick: pickFile
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "plus",
    size: 20
  })), /*#__PURE__*/React.createElement("textarea", {
    ref: taRef,
    className: "vc-composer__input",
    placeholder: "Fachfrage zur Verzahnung stellen\u2026",
    value: value,
    onChange: autosize,
    onKeyDown: onKey,
    rows: 1
  }), /*#__PURE__*/React.createElement("button", {
    className: "vc-composer__send",
    onClick: submit,
    disabled: !value.trim(),
    "aria-label": "Frage stellen"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "arrow-up",
    size: 19
  }))), /*#__PURE__*/React.createElement("div", {
    className: "vc-composer__meta"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-composer__format"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-composer__fmtlabel"
  }, "Format"), /*#__PURE__*/React.createElement(Select, {
    options: formats,
    value: format,
    onChange: e => onFormat(e.target.value),
    style: {
      height: 28,
      fontSize: 12.5
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-composer__note"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "shield-check",
    size: 12,
    style: {
      color: 'var(--accent-text)'
    }
  }), "Striktes RAG \u2014 nur indexierte Quellen"))));
}
Object.assign(window, {
  Composer
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/Composer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/Inspector.jsx
try { (() => {
/* Right inspector panel: technical drawing, parameter table, metadata JSON. */
function Inspector({
  gear,
  onClose
}) {
  const {
    Tabs,
    ParameterTable,
    CodeBlock,
    Badge
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const [tab, setTab] = React.useState('zeichnung');
  const rows = [{
    key: 'Verzahnungstyp',
    value: gear.verzahnungstyp,
    unit: ''
  }, {
    key: 'Modul',
    value: gear.modul,
    unit: 'mm'
  }, {
    key: 'Zähnezahl',
    value: gear.zaehnezahl,
    unit: ''
  }, {
    key: 'Eingriffswinkel',
    value: gear.eingriffswinkel,
    unit: '°'
  }, {
    key: 'Schrägungswinkel',
    value: gear.schraegungswinkel,
    unit: '°'
  }, {
    key: 'Profilverschiebung',
    value: gear.profilverschiebung,
    unit: 'x'
  }, {
    key: 'Teilkreis d',
    value: gear.teilkreis,
    unit: 'mm'
  }, {
    key: 'Kopfkreis dₐ',
    value: gear.kopfkreis,
    unit: 'mm'
  }, {
    key: 'Fußkreis d_f',
    value: gear.fusskreis,
    unit: 'mm'
  }, {
    key: 'Zahnbreite b',
    value: gear.zahnbreite,
    unit: 'mm'
  }];
  const json = `{
  "verzahnungstyp": "${gear.verzahnungstyp}",
  "modul": ${gear.modul.replace(',', '.')},
  "zaehnezahl": ${gear.zaehnezahl},
  "eingriffswinkel": ${gear.eingriffswinkel.replace(',', '.')},
  "werkstoff": "${gear.werkstoff}",
  "haerte": "${gear.haerte}",
  "verzahnungsqualitaet": ${gear.qualitaet}
}`;
  return /*#__PURE__*/React.createElement("aside", {
    className: "vc-inspector"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__head"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-inspector__title"
  }, "Inspektor"), /*#__PURE__*/React.createElement(Badge, {
    variant: "accent"
  }, gear.verzahnungstyp), /*#__PURE__*/React.createElement("button", {
    className: "vc-inspector__close",
    onClick: onClose,
    "aria-label": "Schlie\xDFen"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "x",
    size: 16
  }))), /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__tabs"
  }, /*#__PURE__*/React.createElement(Tabs, {
    value: tab,
    onChange: setTab,
    items: [{
      id: 'zeichnung',
      label: 'Zeichnung'
    }, {
      id: 'parameter',
      label: 'Parameter'
    }, {
      id: 'meta',
      label: 'Metadaten'
    }]
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__body"
  }, tab === 'zeichnung' && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vc-drawing"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "circle-gauge",
    size: 40,
    style: {
      color: 'var(--text-faint)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "vc-drawing__label"
  }, "Technische Zeichnung"), /*#__PURE__*/React.createElement("div", {
    className: "vc-drawing__sub"
  }, "STEP 242 \xB7 Schnittansicht \u2014 Platzhalter")), /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__caption"
  }, "Quelle: ", gear.verzahnungstyp.toLowerCase(), "_z", gear.zaehnezahl, ".stp")), tab === 'parameter' && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__sectlbl"
  }, "Geometrie & Werkstoff"), /*#__PURE__*/React.createElement(ParameterTable, {
    rows: rows
  }), /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__chips"
  }, /*#__PURE__*/React.createElement(Badge, {
    variant: "success"
  }, gear.haerte), /*#__PURE__*/React.createElement(Badge, {
    square: true,
    variant: "neutral"
  }, "DIN-Qualit\xE4t ", gear.qualitaet), /*#__PURE__*/React.createElement(Badge, {
    variant: "info"
  }, gear.werkstoff))), tab === 'meta' && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vc-inspector__sectlbl"
  }, "CAD-Metadaten (JSON)"), /*#__PURE__*/React.createElement(CodeBlock, {
    caption: "cad_metadata.json"
  }, json))));
}
Object.assign(window, {
  Inspector
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/Inspector.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/Sidebar.jsx
try { (() => {
/* Left sidebar: brand, new chat, chat history, active part + RAG status. */
function Sidebar({
  chats,
  activePart,
  knowledgeBase,
  activeChat,
  onSelectChat,
  onNewChat,
  onHome,
  onUploadStep
}) {
  const {
    Button,
    IconButton,
    Spinner
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  const stepInput = React.useRef(null);
  const groups = {};
  chats.forEach(c => {
    (groups[c.when] = groups[c.when] || []).push(c);
  });
  const pickStep = () => {
    if (stepInput.current) stepInput.current.click();
  };
  const onStepChosen = e => {
    const f = e.target.files && e.target.files[0];
    if (f) onUploadStep(f);
    e.target.value = '';
  };
  return /*#__PURE__*/React.createElement("aside", {
    className: "vc-sidebar"
  }, /*#__PURE__*/React.createElement("button", {
    className: "vc-sidebar__brand",
    onClick: onHome,
    title: "Zur Startseite"
  }, /*#__PURE__*/React.createElement(Logo, null)), /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__section"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    iconLeft: /*#__PURE__*/React.createElement(Icon, {
      name: "plus",
      size: 16
    }),
    style: {
      width: '100%'
    },
    onClick: onNewChat
  }, "Neue Konversation")), /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__scroll"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__label"
  }, "Verlauf"), Object.entries(groups).map(([when, list]) => /*#__PURE__*/React.createElement("div", {
    key: when,
    className: "vc-histgroup"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-histgroup__when"
  }, when), list.map(c => /*#__PURE__*/React.createElement("button", {
    key: c.id,
    className: 'vc-histitem' + (c.id === activeChat ? ' vc-histitem--active' : ''),
    onClick: () => onSelectChat(c.id)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "message-square",
    size: 15
  }), /*#__PURE__*/React.createElement("span", {
    className: "vc-histitem__title"
  }, c.title))))), /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__label",
    style: {
      marginTop: 18
    }
  }, "Aktives Bauteil"), /*#__PURE__*/React.createElement("input", {
    ref: stepInput,
    type: "file",
    accept: ".step,.stp,.stp242,.p21,.iges,.igs,model/step",
    style: {
      display: 'none'
    },
    onChange: onStepChosen
  }), activePart ? /*#__PURE__*/React.createElement("div", {
    className: "vc-part"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-part__ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "box",
    size: 18
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-part__main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-part__name",
    title: activePart.name
  }, activePart.name), activePart.status === 'indexing' ? /*#__PURE__*/React.createElement("div", {
    className: "vc-part__status vc-part__status--idx"
  }, /*#__PURE__*/React.createElement(Spinner, null), " Wird analysiert\u2026") : /*#__PURE__*/React.createElement("div", {
    className: "vc-part__status"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-part__dot"
  }), " Bereit f\xFCr Fragen")), /*#__PURE__*/React.createElement(IconButton, {
    size: "sm",
    title: "Andere STEP-Datei hochladen",
    onClick: pickStep
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "refresh-cw",
    size: 14
  }))) : /*#__PURE__*/React.createElement("button", {
    className: "vc-upload",
    onClick: pickStep
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-upload__ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "box",
    size: 18
  })), /*#__PURE__*/React.createElement("span", {
    className: "vc-upload__main"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-upload__title"
  }, "CAD / STEP hochladen"), /*#__PURE__*/React.createElement("span", {
    className: "vc-upload__hint"
  }, ".step \xB7 .stp \xB7 .iges \u2014 klicken oder ablegen")), /*#__PURE__*/React.createElement(Icon, {
    name: "upload",
    size: 16
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__label",
    style: {
      marginTop: 20
    }
  }, "Wissensbasis"), /*#__PURE__*/React.createElement("div", {
    className: "vc-kb"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-kb__ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "database",
    size: 16
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-kb__main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "vc-kb__title"
  }, "RAG-Wissensbasis verbunden"), /*#__PURE__*/React.createElement("div", {
    className: "vc-kb__meta"
  }, knowledgeBase.docs.toLocaleString('de-DE'), " Dokumente indexiert")), /*#__PURE__*/React.createElement("span", {
    className: "vc-kb__dot"
  })), /*#__PURE__*/React.createElement("p", {
    className: "vc-kb__note"
  }, "Die Wissensbasis wird nicht vollst\xE4ndig angezeigt. Pro Antwort erscheinen nur die tats\xE4chlich verwendeten Quellen.")), /*#__PURE__*/React.createElement("div", {
    className: "vc-sidebar__foot"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-avatar"
  }, "MH"), /*#__PURE__*/React.createElement("span", null, "Dr. Ing. M. Hartmann"), /*#__PURE__*/React.createElement(IconButton, {
    size: "sm",
    title: "Einstellungen",
    style: {
      marginLeft: 'auto'
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "settings",
    size: 15
  }))));
}
Object.assign(window, {
  Sidebar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/Sidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/TopBar.jsx
try { (() => {
/* Top bar: active component context, theme toggle, inspector toggle. */
function TopBar({
  gear,
  dark,
  onToggleTheme,
  inspectorOpen,
  onToggleInspector,
  onToggleSidebar
}) {
  const {
    IconButton,
    Badge
  } = window.VerzahnungsCopilotDesignSystem_c9990b;
  return /*#__PURE__*/React.createElement("header", {
    className: "vc-topbar"
  }, /*#__PURE__*/React.createElement(IconButton, {
    title: "Seitenleiste",
    className: "vc-only-narrow",
    onClick: onToggleSidebar
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "panel-left",
    size: 18
  })), /*#__PURE__*/React.createElement("div", {
    className: "vc-topbar__context"
  }, /*#__PURE__*/React.createElement("span", {
    className: "vc-topbar__icon"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "circle-gauge",
    size: 17
  })), /*#__PURE__*/React.createElement("span", {
    className: "vc-topbar__title"
  }, gear.verzahnungstyp), /*#__PURE__*/React.createElement(Badge, {
    square: true,
    variant: "neutral"
  }, "Modul ", gear.modul), /*#__PURE__*/React.createElement(Badge, {
    square: true,
    variant: "neutral"
  }, "z = ", gear.zaehnezahl), /*#__PURE__*/React.createElement(Badge, {
    square: true,
    variant: "neutral"
  }, gear.werkstoff)), /*#__PURE__*/React.createElement("div", {
    className: "vc-topbar__actions"
  }, /*#__PURE__*/React.createElement(IconButton, {
    title: dark ? 'Light-Mode' : 'Dark-Mode',
    onClick: onToggleTheme
  }, /*#__PURE__*/React.createElement(Icon, {
    name: dark ? 'sun' : 'moon',
    size: 18
  })), /*#__PURE__*/React.createElement(IconButton, {
    title: "Inspector",
    active: inspectorOpen,
    onClick: onToggleInspector
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "panel-right",
    size: 18
  }))));
}
Object.assign(window, {
  TopBar
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/TopBar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/copilot/data.js
try { (() => {
/* Mock domain data for the Verzahnungs-Copilot UI kit. Not production data. */
window.VC_DATA = {
  chats: [{
    id: 'c1',
    title: 'Werkstoffwahl einsatzgehärtete Stirnräder',
    when: 'Heute',
    active: true
  }, {
    id: 'c2',
    title: 'Profilverschiebung — Auslegung x-Faktor',
    when: 'Heute'
  }, {
    id: 'c3',
    title: 'Einfluss Schrägungswinkel auf Laufruhe',
    when: 'Gestern'
  }, {
    id: 'c4',
    title: 'Toleranzklassen ISO 1328 Vergleich',
    when: 'Gestern'
  }, {
    id: 'c5',
    title: 'Fräsparameter Wälzfräsen Modul 3',
    when: '2. Juni'
  }, {
    id: 'c6',
    title: 'Tragfähigkeitsnachweis nach DIN 3990',
    when: '28. Mai'
  }],
  documents: [{
    id: 'd1',
    name: 'DIN3990_Tragfaehigkeit.pdf',
    chunks: 142,
    status: 'ready'
  }, {
    id: 'd2',
    name: 'Werkstoffkunde_Verzahnung.pdf',
    chunks: 88,
    status: 'ready'
  }, {
    id: 'd3',
    name: 'Fraesparameter_Datenblatt.pdf',
    chunks: 54,
    status: 'ready'
  }, {
    id: 'd4',
    name: 'ISO1328_Toleranzen.pdf',
    chunks: 0,
    status: 'indexing'
  }],
  activePart: {
    name: 'stirnrad_z34.stp',
    status: 'ready'
  },
  knowledgeBase: {
    docs: 12480,
    status: 'ready'
  },
  gear: {
    verzahnungstyp: 'Stirnrad',
    modul: '2,500',
    zaehnezahl: '34',
    eingriffswinkel: '20,0',
    schraegungswinkel: '0,0',
    profilverschiebung: '0,00',
    teilkreis: '85,000',
    kopfkreis: '90,000',
    fusskreis: '78,750',
    zahnbreite: '28,0',
    werkstoff: '16MnCr5',
    haerte: 'einsatzgehärtet',
    qualitaet: '7'
  },
  formats: ['kurz', 'standard', 'ausführlich', 'stichpunkte', 'tabellarisch']
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/data.js", error: String((e && e.message) || e) }); }

// ui_kits/copilot/ui.jsx
try { (() => {
/* Shared UI helpers for the copilot kit: Lucide Icon + product Logo. */

function Icon({
  name,
  size = 18,
  color,
  style,
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (ref.current && window.lucide) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      ref.current.appendChild(el);
      window.lucide.createIcons({
        attrs: {
          width: size,
          height: size,
          'stroke-width': 1.75
        },
        nameAttr: 'data-lucide'
      });
    }
  }, [name, size]);
  return /*#__PURE__*/React.createElement("span", {
    ref: ref,
    "aria-hidden": "true",
    style: {
      display: 'inline-flex',
      color,
      ...style
    }
  });
}
function LogoTile({
  size = 34,
  radius = 10,
  iconSize = 19
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-logo__tile",
    style: {
      width: size,
      height: size,
      borderRadius: radius
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "cog",
    size: iconSize
  }));
}
function Logo({
  showWordmark = true
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "vc-logo"
  }, /*#__PURE__*/React.createElement(LogoTile, null), showWordmark && /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "vc-logo__name"
  }, "Verzahnung\xA0Intelligence"), /*#__PURE__*/React.createElement("div", {
    className: "vc-logo__sub"
  }, "Wissensbasis \xB7 KIT")));
}
Object.assign(window, {
  Icon,
  Logo,
  LogoTile
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/copilot/ui.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Citation = __ds_scope.Citation;

__ds_ns.CodeBlock = __ds_scope.CodeBlock;

__ds_ns.ParameterTable = __ds_scope.ParameterTable;

__ds_ns.SourceRow = __ds_scope.SourceRow;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Spinner = __ds_scope.Spinner;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Textarea = __ds_scope.Textarea;

})();
