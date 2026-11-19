// What cablePoints answers over the compiled preview of each plug whose
// contract names wire points: the paths of the previews come in argv, the answer
// goes out as one line of JSON. No DOM and no jsdom: the preview is read by a
// small parser into the few things cablePoints touches.
import {readFileSync} from 'node:fs';

globalThis.location = {search: ''};
globalThis.fetch = async () => ({ok: true, text: async () => '<svg/>'});

const m = await import('../../../kit/relief.js');

const ENT = {'&quot;': '"', '&apos;': "'", '&lt;': '<', '&gt;': '>', '&amp;': '&'};
const unent = s => s.replace(/&(quot|apos|lt|gt|amp);/g, x => ENT[x]);
const camel = k => k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

class El {
  constructor(tagName, attrs, parentElement) {
    this.tagName = tagName;
    this.attrs = attrs;
    this.parentElement = parentElement;
    this.children = [];
    const get = (_, name) => {
      if (typeof name !== 'string') return undefined;
      const k = Object.keys(this.attrs).find(a => a.startsWith('data-') && camel(a.slice(5)) === name);
      return k === undefined ? undefined : this.attrs[k];
    };
    this.dataset = new Proxy({}, {get});
  }
  get id() { return this.attrs.id ?? ''; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  *descendants() { for (const c of this.children) { yield c; yield* c.descendants(); } }
  querySelectorAll(sel) {
    const f = matcher(sel);
    return [...this.descendants()].filter(f);
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  closest(sel) {
    const f = matcher(sel);
    for (let n = this; n; n = n.parentElement) if (f(n)) return n;
    return null;
  }
}

function matcher(s) {
  const parts = [...s.matchAll(/\[([\w-]+)(?:(\^?=)"((?:[^"\\]|\\.)*)")?\]/g)];
  if (!parts.length || parts.map(p => p[0]).join('') !== s) throw new Error('selector ' + s);
  return n => parts.every(([, k, op, v]) => {
    const have = k in n.attrs ? n.attrs[k] : null;
    if (op === undefined) return have !== null;
    const want = v.replace(/\\(.)/g, '$1');
    return have !== null && (op === '^=' ? have.startsWith(want) : have === want);
  });
}

const TOKEN = /<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<!\[CDATA\[[\s\S]*?\]\]>|<!DOCTYPE[^>]*>|<\/([^\s>]+)\s*>|<([^\s\/>]+)((?:\s+[^\s=\/>]+(?:\s*=\s*(?:"[^"]*"|'[^']*'))?)*)\s*(\/?)>/g;
const ATTR = /([^\s=\/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'))?/g;

function parse(text) {
  let root = null, cur = null;
  for (const t of text.matchAll(TOKEN)) {
    if (t[1] !== undefined) { cur = cur && cur.parentElement; continue; }
    if (t[2] === undefined) continue;
    const attrs = {};
    for (const a of t[3].matchAll(ATTR)) attrs[a[1]] = unent(a[2] ?? a[3] ?? '');
    const e = new El(t[2], attrs, cur);
    if (cur) cur.children.push(e); else root = e;
    if (!t[4]) cur = e;
  }
  return root;
}

const out = {};
const warn = console.warn;
for (const f of process.argv.slice(2)) {
  const svg = parse(readFileSync(f, 'utf8'));
  const warned = [];
  console.warn = (...a) => warned.push(a.join(' '));
  const strip = ps => ps.map(({el, ...p}) => p);
  out[f] = {wires: strip(m.wirePoints(svg)), cables: strip(m.cablePoints(svg)), warned};
  console.warn = warn;
}
console.log(JSON.stringify(out));
