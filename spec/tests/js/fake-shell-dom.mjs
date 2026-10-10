// The smallest page kit/shell.js's createShell will mount into under node
// (shell-*.mjs). jsdom is not a dependency here, so this is a permissive
// stand-in: an element holds children and attributes and answers the queries
// the shell makes with nothing found, which is all the load path needs. A
// drawing is an element whose `data-src` is the text it was parsed from, so a
// test can tell which load mounted it.
class ClassList {
  constructor() { this.s = new Set(); }
  add(...c) { c.forEach(x => this.s.add(x)); }
  remove(...c) { c.forEach(x => this.s.delete(x)); }
  toggle(c, on) { on ??= !this.s.has(c); if (on) this.s.add(c); else this.s.delete(c); return on; }
  contains(c) { return this.s.has(c); }
}
export class El {
  constructor(tag = 'div', attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = {...attrs};
    this.children = [];
    this.parentElement = null;
    this.style = {setProperty() {}};
    this.classList = new ClassList();
    this.value = '';
    this.hidden = false;
    this.viewBox = {baseVal: {width: 100, height: 50}};
    this.byQuery = null;          // set on the mount: what the shell's $() finds
  }
  // data-* attributes, camel-cased, as a browser's dataset reads them
  get dataset() {
    const out = {};
    for (const [k, v] of Object.entries(this.attrs))
      if (k.startsWith('data-')) out[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
    return out;
  }
  get firstChild() { return this.children[0] || null; }
  get childNodes() { return [...this.children]; }
  set innerHTML(_) { this.replaceChildren(); }
  get innerHTML() { return ''; }
  set textContent(_) { this.replaceChildren(); }
  get textContent() { return ''; }
  appendChild(c) { c.parentElement?.removeChild(c); c.parentElement = this; this.children.push(c); return c; }
  append(...cs) { cs.forEach(c => this.appendChild(c)); }
  removeChild(c) { this.children = this.children.filter(x => x !== c); c.parentElement = null; return c; }
  remove() { this.parentElement?.removeChild(this); }
  replaceChildren(...cs) { for (const c of [...this.children]) this.removeChild(c); this.append(...cs); }
  insertAdjacentHTML() {}
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  removeAttribute(k) { delete this.attrs[k]; }
  hasAttribute(k) { return k in this.attrs; }
  addEventListener() {}
  removeEventListener() {}
  getBoundingClientRect() { return {left: 0, top: 0, width: 0, height: 0}; }
  closest() { return null; }
  contains(n) { for (; n; n = n.parentElement) if (n === this) return true; return false; }
  *descendants() { for (const c of this.children) { yield c; yield* c.descendants(); } }
  // the mount answers the shell's $() with an element per selector; a drawing
  // answers attribute selectors only - `[a="v"][b]`, in a comma list - which
  // is every query the field path makes, and finds nothing for anything else
  querySelector(sel) {
    if (this.byQuery) return (this.byQuery[sel] ||= new El('div'));
    return this.querySelectorAll(sel)[0] || null;
  }
  querySelectorAll(sel) {
    const alts = String(sel).split(',').map(s => s.trim()).map(attrTest);
    if (alts.some(a => !a)) return [];
    return [...this.descendants()].filter(n => alts.some(a => a(n)));
  }
}
function attrTest(sel) {
  const parts = [...sel.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)];
  if (!parts.length || parts.map(m => m[0]).join('') !== sel) return null;
  return n => parts.every(([, k, v]) => (v === undefined ? n.hasAttribute(k) : n.getAttribute(k) === v));
}

// `fetch` answers from `routes`: {url suffix: url => text | Promise<text>}, the
// longest matching suffix winning. A test holds a response by returning a
// promise it resolves later.
export function install(routes) {
  const head = new El('head');
  const body = new El('body');
  body.byQuery = {};
  globalThis.document = {
    head, body, documentElement: new El('html'), activeElement: null,
    createElement: t => new El(t),
    createElementNS: (_, t) => new El(t),
    importNode: n => n,
  };
  globalThis.window = globalThis;
  globalThis.parent = {};                 // inside a frame: no device picker
  globalThis.location = {search: '', href: 'http://kit.test/'};
  globalThis.addEventListener = () => {};
  globalThis.localStorage = {getItem: () => null, setItem() {}};
  globalThis.CSS = {escape: s => String(s)};
  // a drawing's text is its name, or JSON {src, parts: [{path, ref}]} for one
  // that draws parts
  globalThis.DOMParser = class {
    parseFromString(txt) {
      const d = txt.startsWith('{') ? JSON.parse(txt) : {src: txt, parts: []};
      const svg = new El('svg', {'data-src': d.src});
      for (const {path, ref} of d.parts) svg.appendChild(new El('g', {'data-path': path, 'data-ref': ref}));
      return {documentElement: svg};
    }
  };
  globalThis.fetch = async url => {
    const hit = Object.keys(routes).filter(k => String(url).endsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    if (!hit) return {ok: false, status: 404, text: async () => '',
                      json: async () => { throw new Error(`404 ${url}`); }};
    const txt = await routes[hit](url);
    return {ok: true, status: 200, text: async () => txt, json: async () => JSON.parse(txt)};
  };
  return {body};
}

// a promise and the function that settles it
export function gate() {
  let open;
  const p = new Promise(r => { open = r; });
  return {p, open};
}
