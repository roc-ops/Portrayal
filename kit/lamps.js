// ANIMATED LAMPS IN 3D.
//
// A compiled face animates a lamp with CSS: `.state-fault { animation:
// portrayal-blink 1s ... }`, keyframes on opacity or fill. The 2D stage is a
// live SVG, so the browser runs those. The 3D stage is a TEXTURE, rasterised
// once through an <img> - one sample of the animation at t=0 - and the blink
// keyframes start at opacity 1, so every blinking lamp in 3D rendered solid ON,
// forever, and a state that differs from another only by blinking looked
// identical to it.
//
// The fix keeps the drawing as the single source of truth for what a state
// looks like. An <img> honours `animation-play-state: paused` together with a
// negative `animation-delay` (measured: an 8x8 blink sampled at -0.75s draws
// alpha 0, at -0.25s alpha 255; the fill alternation follows the same clock),
// so a texture can be drawn at any instant of its animation. Each animated
// lamp is rasterised once per keyframe block - twice for a blink, ten times for
// the control panel's disabled sequence - and the render loop swaps the frame
// whose interval the clock is in. Nothing is re-rasterised per frame.
//
// Two kinds of lamp, one engine:
//   - a lamp that is its own mesh already (a `data-z-dome` cap, a bezel plate)
//     has a restyle entry carrying its material and size; its frames replace
//     that material's map;
//   - a flat lamp painted into a face texture gets a small quad floating 0.06 mm
//     over the face at the lamp's rectangle, carrying the lamp's own art with an
//     unlit copy of itself underneath (a blink's off half is transparent, and
//     the face beneath was sampled with the lamp on).
// A quad is tagged with the lamp's path like every other mesh, so a pulled
// module takes its lamps with it.

import * as THREE from 'three';
import { nodeTools, rasterize, canvasTex, tiltOf, tiltTools, tiltGroupIn, unproject } from './relief.js';

// SOMETHING UNDER THE LIVE ART. A blink is opacity 1 <-> 0 on the lamp, so a
// frame sampled in the off half is transparent - and a transparent dome cap or
// quad shows the face texture through it, which was sampled at t=0 with the
// lamp ON. Two answers to what belongs underneath:
//   - a dome's own art with every state class stripped: a led-dot's lamp is
//     `fill: var(--led-color, #3a3f44)`, so unlit it is the dark grey the 2D
//     stage shows when the same lamp is off;
//   - for a flat lamp, the art of the part it sits on with the lamp itself
//     hidden - the housing behind it - which is exactly what the 2D stage
//     shows through the lamp at opacity 0. A lamp whose fill is a literal
//     (the R740xd control panel's bars) looks the same lit and unlit, and an
//     unlit copy of it would not blink at all.
const artOf = text => {
  const at = text.indexOf('<!--art-->');
  return at < 0 ? null : {head: text.slice(0, at + 10), art: text.slice(at + 10).replace(/<\/svg>\s*$/, '')};
};
/** A node svg with an unlit copy of its art beneath the live one. */
export function withBase(text) {
  const p = artOf(text);
  if (!p) return text;
  const quiet = p.art.replace(/class="([^"]*)"/g,
    (_, c) => `class="${c.split(/\s+/).filter(k => !k.startsWith('state-')).join(' ')}"`);
  return p.head + quiet + p.art + '</svg>';
}
/** A node svg over the art of its host part, with the node hidden in the host. */
export function overHost(text, hostText, path) {
  const p = artOf(text), h = hostText && artOf(hostText);
  if (!p || !h) return withBase(text);
  return p.head + `<style>.portrayal-under [data-path="${path}"]{display:none}</style>` +
    `<g class="portrayal-under">${h.art}</g>` + p.art + '</svg>';
}

/** The same drawing, frozen at `t` seconds into every animation it carries. */
export function phaseSvg(text, t) {
  const css = `<style>*{animation-play-state:paused!important;animation-delay:${-t}s!important}</style>`;
  return text.replace(/<\/svg>\s*$/, css + '</svg>');
}

/** Parse a face or node svg into a measurable, hidden document. */
export function openDoc(text) {
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = text;
  document.body.appendChild(div);
  return {svg: div.querySelector('svg'), div, close: () => div.remove()};
}

// WHERE THE FRAMES ARE. A keyframe block `50%, 100% { opacity: 0 }` holds from
// 50% on, and the block before it ends at 49.9%: the sample instants are the
// starts of the blocks, and a frame lasts until the next block starts. The
// 0.1% between them is a linear ramp one millisecond long; nobody sees it.
/** Fractions (0..1) at which each keyframe block of `name` begins, sorted. */
export function keyframeStops(root, name) {
  const stops = new Set([0]);
  for (const style of root.querySelectorAll('style')) {
    let rules;
    try { rules = style.sheet && style.sheet.cssRules; } catch (e) { rules = null; }
    for (const r of rules || []) {
      if (r.type !== CSSRule.KEYFRAMES_RULE || r.name !== name) continue;
      for (const k of r.cssRules) {
        const starts = k.keyText.split(',').map(s => s.trim())
          .map(s => s === 'from' ? 0 : s === 'to' ? 1 : parseFloat(s) / 100)
          .filter(v => !isNaN(v));
        if (starts.length) stops.add(Math.min(...starts));
      }
    }
  }
  return [...stops].filter(v => v < 1).sort((a, b) => a - b);
}

// Asked of the browser rather than of the stylesheet, for the same reason
// states.js's paints() is: specificity, scope and inheritance are the
// browser's to resolve, and a rule matched by hand is a rule matched wrong
// somewhere. An element inside an already-animated one is skipped - its art
// is in the outer element's frames.
/** Elements under `el` (inclusive) that the classes now on the document animate. */
export function animatedIn(el) {
  const out = [];
  for (const n of [el, ...el.querySelectorAll('*')]) {
    if (out.some(o => o.el.contains(n))) continue;
    const cs = getComputedStyle(n);
    const name = (cs.animationName || 'none').split(',')[0].trim();
    if (name === 'none') continue;
    const d = (cs.animationDuration || '0s').split(',')[0].trim();
    const dur = parseFloat(d) * (d.endsWith('ms') ? 0.001 : 1);
    if (!(dur > 0)) continue;
    out.push({el: n, name, dur});
  }
  return out;
}

const LIT = /\bstate-[a-z0-9-]+/;
const touches = (text, changed) => !changed || [...changed].some(p => text.includes(`data-path="${p}"`));

/** One engine per viewer: `sync` after a build or a state change, `step` per frame. */
export function createLamps() {
  const recs = new Map();     // key -> {text, mat, frames, stops, dur, i, mesh?, view?}

  function drop(key) {
    const r = recs.get(key);
    if (!r) return;
    recs.delete(key);
    if (r.mesh) {
      if (r.mesh.parent) r.mesh.parent.remove(r.mesh);
      r.mesh.geometry.dispose();
      r.mat.dispose();
    } else if (r.frames.includes(r.mat.map)) {
      // a dome whose lamp stopped animating: leave it showing its first frame,
      // which is the t=0 look a plain restyle would have painted
      r.mat.map = r.frames[0];
      r.frames = r.frames.slice(1);
    }
    for (const f of r.frames) f.dispose();
  }

  async function add(key, r, pxmm) {
    const frames = [];
    for (const s of r.stops)
      frames.push(canvasTex(await rasterize(phaseSvg(r.text, (s + 1e-4) * r.dur), r.w, r.h, pxmm)));
    if (recs.has(key)) { for (const f of frames) f.dispose(); return; } // superseded mid-raster
    const old = r.mat.map;
    if (old && !r.mesh) { for (const f of frames) { f.repeat.copy(old.repeat); f.offset.copy(old.offset); } }
    r.mat.map = frames[0];
    r.mat.needsUpdate = true;
    recs.set(key, {...r, frames, i: 0});
  }

  /**
   * Reconcile the animated set with the drawing.
   *   faces      LOD records: {key(view), svgText(restyled), wmm, hmm, matIndex}
   *   entries    restyle entries: {svgText, anim?: {mat, w, h}}
   *   restyle    text -> text with the current states applied (for entries)
   *   changed    Set of paths that changed, or null to reconcile everything
   */
  async function sync({faces = [], entries = [], faceGroups = {}, fruGroups = {}, faceFlip = {},
                       pxmm = 16, restyle = t => t, changed = null, isOff = () => false,
                       tint = () => 1}) {
    const keep = new Set();
    // meshes of their own: domes, plates
    for (const e of entries) {
      if (!e.anim) continue;
      if (!touches(e.svgText, changed)) { if (recs.has(e)) keep.add(e); continue; }
      const text = withBase(restyle(e.svgText));
      const have = recs.get(e);
      if (have && have.text === text) { keep.add(e); continue; }
      drop(e);
      if (!LIT.test(text)) continue;
      const doc = openDoc(text);
      let a, stops;
      try {
        a = animatedIn(doc.svg)[0];
        if (a) stops = keyframeStops(doc.svg, a.name);
      } finally { doc.close(); }
      if (!a || !stops.length) continue;
      await add(e, {text, mat: e.anim.mat, w: e.anim.w, h: e.anim.h, stops, dur: a.dur}, pxmm);
      keep.add(e);
    }
    // flat lamps in a face texture: a quad each
    for (const rec of faces) {
      const grp = faceGroups[rec.key];
      const mine = [...recs.entries()].filter(([, r]) => r.view === rec.key).map(([k]) => k);
      if (!grp || !touches(rec.svgText, changed)) { for (const k of mine) keep.add(k); continue; }
      if (!LIT.test(rec.svgText)) continue;          // nothing lit: `mine` all drop below
      const doc = openDoc(rec.svgText);
      try {
        const T = nodeTools(doc.svg);
        // A LAMP ON A PART ON A FACET is placed in that part's tilt frame
        // (relief.js tiltTools), at its true size, whether its owner is the
        // optic (a FRU) or the card. Built only when a tilted lamp is met.
        let TT = null;
        const tiltRec = el => {
          const t = tiltOf(el);
          if (!t) return null;
          TT = TT || tiltTools(doc.svg, {mmRect: T.mmRect, liftOf: T.liftOf,
                                         ctmOf: n => T.inv.multiply(n.getScreenCTM())});
          return TT.tiltRec(t);
        };
        const lit = [...doc.svg.querySelectorAll('[data-path][class*="state-"]')]
          .filter(el => !el.closest('[data-projection]'));
        const seen = new Set();
        for (const node of lit) for (const a of animatedIn(node)) {
          // a dome is a mesh of its own and is animated through its entry above
          if (a.el.closest('[data-z-dome]') || seen.has(a.el)) continue;
          seen.add(a.el);
          const rect = T.mmRect(a.el);
          if (!(rect.w > 0 && rect.h > 0)) continue;
          const own = a.el.closest('[data-path]');
          const path = own ? own.dataset.path : node.dataset.path;
          const idx = a.el === node ? -1 : [...node.querySelectorAll('*')].indexOf(a.el);
          const key = `${rec.key}|${node.dataset.path}|${idx}`;
          const host = own && own.parentElement && own.parentElement.closest('[data-path]');
          const text = overHost(T.nodeSvg(a.el, rect), host && T.nodeSvg(host, rect), path);
          const have = recs.get(key);
          if (have && have.text === text) { keep.add(key); continue; }
          drop(key);
          const stops = keyframeStops(doc.svg, a.name);
          if (!stops.length) continue;
          const owner = T.ownerOf(a.el);
          const fg = owner && fruGroups[owner];
          // a module's face art rides 0.3 over the face in its own group; a lamp
          // painted on a cavity floor sits that cavity's depth in
          const cav = fg ? null : a.el.closest('[data-depth]');
          const tr = tiltRec(a.el);
          // `at` is where the quad goes: the true rect in the tilt frame, and a
          // lift measured from the facet (its `base`); `rect` stays the drawn
          // one, which the frames are rasterised from
          const at = tr ? unproject(rect, tr.tilt) : rect;
          const z = T.liftOf(a.el) - (tr ? tr.base : 0) + (fg ? 0.3 : 0)
            - (cav ? +cav.dataset.depth || 0 : 0) + 0.06;
          const [fx, fy] = faceFlip[rec.key] || [false, false];
          const x = (fx ? -1 : 1) * (at.x + at.w / 2 - rec.wmm / 2);
          const y = (fy ? -1 : 1) * (rec.hmm / 2 - (at.y + at.h / 2));
          const mat = new THREE.MeshBasicMaterial({transparent: true, alphaTest: 0.1, alphaToCoverage: true});
          mat.color.setScalar(tint(rec));
          const mesh = new THREE.Mesh(new THREE.PlaneGeometry(at.w, at.h), mat);
          mesh.position.set(x, y, z);
          mesh.userData.portrayalPath = path;
          mesh.visible = !isOff(path);
          (tr ? tiltGroupIn(fg || grp, tr.tilt, {fw: rec.wmm, fh: rec.hmm, flipLX: fx, flipLY: fy})
              : fg || grp).add(mesh);
          await add(key, {text, mat, w: rect.w, h: rect.h, stops, dur: a.dur, mesh, view: rec.key}, pxmm);
          keep.add(key);
        }
      } finally { doc.close(); }
    }
    for (const k of [...recs.keys()]) if (!keep.has(k)) drop(k);
    return recs.size;
  }

  /** Advance the clock; swap any lamp whose keyframe block changed. */
  function step(now) {
    if (!recs.size) return;
    const t = now / 1000;
    for (const r of recs.values()) {
      const f = (t % r.dur) / r.dur;
      let i = 0;
      while (i + 1 < r.stops.length && r.stops[i + 1] <= f) i++;
      if (i !== r.i) { r.i = i; r.mat.map = r.frames[i]; }
    }
  }

  function clear() { for (const k of [...recs.keys()]) drop(k); }

  /** For the debug handle: what is animating, and at which instants. */
  const list = () => [...recs.entries()].map(([k, r]) => ({
    key: typeof k === 'string' ? k : `entry:${r.mat.uuid.slice(0, 8)}`, dur: r.dur, stops: r.stops,
    frame: r.i, frames: r.frames.length, mesh: !!r.mesh, view: r.view || null, w: r.w, h: r.h}));
  return {sync, step, clear, list, get size() { return recs.size; }, phaseSvg};
}
