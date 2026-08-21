// Shared relief pipeline.
//
// Face art is an SVG whose nodes carry data-cavity / data-z-* attributes saying
// which parts of the faceplate are recessed, raised, domed or vented. This module
// turns that into something a viewer can build geometry from, and rasterises the
// art at a chosen density.
//
// It lives here rather than in 3d.html because rack.html needs exactly the same
// reading of a face, and two copies would drift. Dependencies are injected once
// rather than threaded through every signature, so the function bodies are the
// same code that has been running in the device viewer.

let THREE, renderer, PXMM, FRU_PATHS;

export function configureRelief(deps) {
  ({THREE, renderer, PXMM, FRU_PATHS} = deps);
}

export async function svgCanvas(url, wmm, hmm, flipX = false, flipYax = false) {
  const text = await (await fetch(url, {cache: 'no-store'})).text();
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([text], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  cv.width = Math.round(wmm * PXMM); cv.height = Math.round(hmm * PXMM);
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipYax) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  URL.revokeObjectURL(blobUrl);
  cv._svgText = text;      // kept for adaptive re-rasterisation (see LOD below)
  return cv;
}
// A face canvas is inevitably non-power-of-two (a 548x44mm side is 2192x176 at
// 4px/mm). WebGL2 mipmaps NPOT textures natively, so rescaling to POT buys
// nothing - and it costs: a 2192x176 side squashed to 2048x128 is 1.07x
// horizontally but 1.38x vertically, and that anisotropic resample distorts fine
// repeating detail (the AS5912's 488x5mm vent strips) into something that beats
// against the pixel grid and crawls under motion. Feed the native raster instead.
export function canvasTex(cv) {
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.needsUpdate = true;
  return tex;
}
// crop a mm-rect out of a face canvas (no mirroring: the rear floor plane's
// 180-degree rotation and the box rear-face UVs already reverse X to match)
export function crop(cv, r) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(r.w * PXMM)); c.height = Math.max(1, Math.round(r.h * PXMM));
  const ctx = c.getContext('2d');
  ctx.drawImage(cv, Math.round(r.x * PXMM), Math.round(r.y * PXMM), c.width, c.height, 0, 0, c.width, c.height);
  return c;
}

// standards-relief extraction: cavities (with interior features) + outward protrusions.
// Interior/plate art is re-rendered STANDALONE from its own nodes so bezel plates
// can carry arbitrary shapes (plug-outline apertures, LED holes) via alpha.
export async function extractRelief(url) {
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = await (await fetch(url, {cache: 'no-store'})).text();
  document.body.appendChild(div);
  const svg = div.querySelector('svg');
  const inv = svg.getScreenCTM().inverse();
  const mmRect = el => {
    const b = el.getBBox();
    const m = inv.multiply(el.getScreenCTM());
    const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
    const x0 = Math.min(pts[0].x, pts[1].x), y0 = Math.min(pts[0].y, pts[1].y);
    return {x: x0, y: y0, w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y)};
  };
  const shared = [...svg.querySelectorAll('style, defs')].map(n => n.outerHTML).join('');
  // owning FRU (bay module / pull tab) of a node, for animated removal
  const ownerOf = el => {
    const a = el.closest('[data-path]');
    if (!a) return null;
    const root = a.dataset.path.split('/')[0];
    return FRU_PATHS.has(root) ? root : null;
  };
  const nodeSvg = (el, rect) => {
    const m = inv.multiply(el.getScreenCTM());
    const clone = el.cloneNode(true);
    clone.removeAttribute('transform');   // the CTM below already includes it
    // raised descendants (collars, handles) render as their own geometry -
    // keep them out of cavity floors and plate textures
    for (const r of clone.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]'))
      r.style.display = 'none';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${rect.w} ${rect.h}"` +
      ` width="${rect.w}mm" height="${rect.h}mm">${shared}` +
      `<g transform="matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e - rect.x} ${m.f - rect.y})">` +
      clone.outerHTML + `</g></svg>`;
  };
  const cavities = [...svg.querySelectorAll('[data-depth]')]
    .filter(el => !el.querySelector('[data-depth]'))
    .map(el => {
      const cavNode = el.dataset.cavity &&
        svg.querySelector(`[id="${CSS.escape(el.id + '--' + el.dataset.cavity)}"]`);
      const rect = mmRect(cavNode || el);
      const grpRect = mmRect(el);
      const features = [...el.querySelectorAll('[data-z-top],[data-z-sink]')].map(f => ({
        ...mmRect(f),
        kind: f.dataset.zTop ? 'top' : 'sink',
        val: +(f.dataset.zTop || f.dataset.zSink),
        color: f.dataset.zColor || '#0a0c0e',
      }));
      return {...rect, owner: ownerOf(el), d: +el.dataset.depth, wall: el.dataset.wall || '#a7adb4',
              lift: +(el.dataset.zLift || 0),
              round: !!el.dataset.round, cavSvg: nodeSvg(cavNode || el, rect),
              grpRect, grpSvg: nodeSvg(el, grpRect), features};
    });
  // pressed grooves: shallow standalone cavities whose own art is the floor
  for (const el of svg.querySelectorAll('[data-groove]')) {
    const rect = mmRect(el);
    cavities.push({...rect, owner: ownerOf(el), d: +el.dataset.groove, wall: '#25282c', round: false,
                   cavSvg: nodeSvg(el, rect), grpRect: rect,
                   grpSvg: nodeSvg(el, rect), features: []});
  }
  const outs = [...svg.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), out: el.dataset.zOut && +el.dataset.zOut,
            cyl: el.dataset.zCyl && +el.dataset.zCyl,
            bar: el.dataset.zBar && +el.dataset.zBar,
            uhandle: el.dataset.zUhandle && +el.dataset.zUhandle,
            lift: +(el.dataset.zLift || 0),
            knurl: !!el.dataset.zKnurl,
            thread: el.dataset.zThread && +el.dataset.zThread,
            color: el.dataset.zColor || null,
            svgText: nodeSvg(el, rect)};
  });
  const domes = [...svg.querySelectorAll('[data-z-dome]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), dome: +el.dataset.zDome, svgText: nodeSvg(el, rect)};
  });
  const vents = [...svg.querySelectorAll('[data-vent],[data-z-vent]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), depth: +(el.dataset.vent || el.dataset.zVent),
            svgText: nodeSvg(el, rect)};
  });
  // component instances only (data-ref) - contract elements can share a class
  // name (pull-tab has an element called "tab"), which would shadow the module
  const frus = [];
  for (const el of svg.querySelectorAll('[data-class="psu"],[data-class="fan"],[data-class="tab"]')) {
    if (!el.dataset.ref) continue;
    const path = (el.dataset.path || '').split('/')[0];
    if (!path || frus.some(f => f.path === path)) continue;
    frus.push({path, ref: el.dataset.ref.split(':')[0], cls: el.dataset.class, ...mmRect(el)});
  }
  for (const el of svg.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]'))
    el.style.display = 'none';
  const cleanText = svg.outerHTML;
  div.remove();
  return {cavities, outs, domes, vents, frus, cleanText};
}

export async function rasterize(svgText, wmm, hmm, pxmm = PXMM, flipX = false, flipY = false) {
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([svgText], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  cv.width = Math.max(1, Math.round(wmm * pxmm)); cv.height = Math.max(1, Math.round(hmm * pxmm));
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipY) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  URL.revokeObjectURL(blobUrl);
  return cv;
}

// six-sided FRU body: same art the component tab shows, reused inside the device
