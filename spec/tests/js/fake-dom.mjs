// The smallest DOM kit/swap.js actually uses, shared by the node scripts that
// exercise it (cage-seat.mjs, relief-scope.mjs). jsdom is not a dependency
// here, so this is the idiom of nested-bays.mjs, in one place.
//
// A drawing's "text" is a JSON tree - {t: tag, a: {attrs}, c: [children]} -
// and `install()` puts a DOMParser that reads it, and an XMLSerializer that
// writes it, on globalThis. Only elements are modelled: text content is not
// something any seating rule reads.
export class Node {
  constructor(attrs = {}, children = [], tag = 'g') {
    this.tagName = tag;
    this._attrs = {...attrs};
    this.parentNode = null;
    this.children = [];
    for (const c of children) this.appendChild(c);
  }
  get attributes() {
    return Object.entries(this._attrs).map(([name, value]) => ({name, value}));
  }
  get childNodes() { return [...this.children]; }
  get ownerDocument() { return DOC; }
  getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  removeAttribute(k) { delete this._attrs[k]; }
  hasAttribute(k) { return k in this._attrs; }
  appendChild(c) {
    if (c.parentNode) c.remove();
    c.parentNode = this;
    this.children.push(c);
    return c;
  }
  remove() {
    const p = this.parentNode;
    if (!p) return;
    p.children.splice(p.children.indexOf(this), 1);
    this.parentNode = null;
  }
  after(n) {
    if (n.parentNode) n.remove();
    const p = this.parentNode;
    p.children.splice(p.children.indexOf(this) + 1, 0, n);
    n.parentNode = p;
  }
  *descendants() {
    for (const c of this.children) { yield c; yield* c.descendants(); }
  }
  querySelectorAll(sel) {
    const alts = sel.split(',').map(s => s.trim()).map(parseSel);
    return [...this.descendants()].filter(n => alts.some(a => a(n, this)));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  clone() {
    return new Node(this._attrs, this.children.map(c => c.clone()), this.tagName);
  }
}

function parseSel(s) {
  if (s === '*') return () => true;
  // `:scope > [...]` - a direct child of the node queried (applyRearOverrides)
  const child = s.match(/^:scope\s*>\s*(.+)$/);
  if (child) {
    const inner = parseSel(child[1]);
    return (n, scope) => n.parentNode === scope && inner(n);
  }
  const parts = [...s.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)];
  if (!parts.length || parts.map(p => p[0]).join('') !== s)
    throw new Error('unexpected selector ' + s);
  return n => parts.every(([, k, v]) =>
    v === undefined ? n.hasAttribute(k) : n.getAttribute(k) === v);
}

export function build(spec) {
  return new Node(spec.a || {}, (spec.c || []).map(build), spec.t || 'g');
}

export function toSpec(n) {
  return {t: n.tagName, a: {...n._attrs}, c: n.children.map(toSpec)};
}

export const DOC = {
  createElementNS: (ns, tag) => new Node({}, [], tag || 'g'),
  importNode: n => n.clone(),
};

export function install() {
  globalThis.DOMParser = class {
    parseFromString(text) {
      const documentElement = build(JSON.parse(text));
      return {
        documentElement,
        querySelector: () => null,          // never a parsererror
        getElementById: id => [documentElement, ...documentElement.descendants()]
          .find(n => n.getAttribute('id') === id) || null,
      };
    }
  };
  globalThis.XMLSerializer = class {
    serializeToString(n) { return JSON.stringify(toSpec(n.documentElement || n)); }
  };
  globalThis.CSS = {escape: s => s};
}
