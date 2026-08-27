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

export function configureRelief(deps, scope) {
  // THREE and the renderer are genuinely per-page and stay module-level. The
  // raster density and the FRU path set are per-VIEWER, and a second viewer
  // calling this used to reclaim them from under the first.
  ({THREE, renderer, PXMM, FRU_PATHS} = deps);
  const sc = _sc(scope);
  if (deps.PXMM != null) sc.pxmm = deps.PXMM;
  if (deps.FRU_PATHS) sc.fruPaths = deps.FRU_PATHS;
}

// Every view SVG was fetched with cache: 'no-store' from four separate call
// sites - svgCanvas (once per box face), extractRelief, and twice more in the
// page - so switching configuration re-downloaded the same six files dozens of
// times. On the demo host that was 9.4 of the 11.8 seconds a switch took. The
// URL already carries the config name, so memoising per URL is safe; a build
// tool writes new files under new names.
const SVG_CACHE = new Map();
// A FACE CAN BE OVERRIDDEN FOR A BUILD. A runtime bay swap changes what the device
// looks like without changing any file on disk, and everything downstream here -
// svgCanvas, extractRelief, the hit index, the FRU-path scan - reads its text
// through svgSource. Registering the swapped text against the same URL is what
// lets ONE substitution reach all of them; threading a text argument through five
// signatures instead would have meant five chances to miss one, and the one that
// was missed would look like a rendering fault rather than a plumbing gap.
//
// AN OVERRIDE IS AN OPINION, NOT A FACT, and that is what separates it from the
// cache above. `SVG_CACHE` is keyed by URL and shared on purpose - the same URL
// really is the same bytes, for everybody. An override says what that URL should
// render as FOR ONE VIEWER, and a module-level map has exactly one seat.
//
// It cost a downstream consumer real work: a before/after comparison of one rack
// with two occupant sets could not be built in one page, because whichever
// viewer swapped last won for both. They ran two iframes - two documents, two
// WebGL contexts - to get two copies of this module. Worse than a race, the old
// `clearSvgOverrides()` took no argument and emptied everything, so one viewer
// starting a build silently discarded another's swaps.
//
// So a viewer may own a SCOPE: its swapped faces and its lit lamps, the two
// things here that are per-document rather than per-page. THREE, the renderer
// and the fetch cache stay module-level, because those genuinely are shared.
// Passing no scope uses the default one, which is what every existing caller
// does and what this module did before - so nothing had to change to keep working.
export function createReliefScope(deps = {}) {
  return {overrides: new Map(), states: new Map(),
          pxmm: deps.PXMM, fruPaths: deps.FRU_PATHS};
}
const DEFAULT_SCOPE = createReliefScope();
const _sc = scope => scope || DEFAULT_SCOPE;
// A scope that was never configured falls back to the module-level injection,
// which is what every pre-scope caller relies on.
const _px = scope => _sc(scope).pxmm ?? PXMM;
const _fru = scope => _sc(scope).fruPaths ?? FRU_PATHS;

export function setSvgOverride(url, text, scope) {
  const m = _sc(scope).overrides;
  if (text == null) m.delete(url);
  else m.set(url, text);
}
export function clearSvgOverrides(scope) { _sc(scope).overrides.clear(); }
export function svgSource(url, scope) {
  const ov = _sc(scope).overrides;
  if (ov.has(url)) return Promise.resolve(ov.get(url));
  if (!SVG_CACHE.has(url))
    SVG_CACHE.set(url, fetch(url, {cache: 'no-store'}).then(r => r.text()));
  return SVG_CACHE.get(url);
}
export function clearSvgCache() { SVG_CACHE.clear(); }

// A STATE SET AT RUNTIME IS A CHANGE TO THE DOCUMENT, exactly like a bay swap,
// and it reached 3D exactly as well: not at all. The chip in the tree adds
// `state-10g` to an element in the LIVE SVG the page is showing, and everything
// in here rasterises a document FETCHED from dist/ - a different DOM that has
// never carried a state class in its life. Zero of the library's 390 compiled
// faces do; the class only ever exists in the browser. So every lamp on every
// device painted its unlit fallback in 3D while 2D showed it lit.
//
// The registry is by `data-path` rather than by id or by element, because that
// is the one name the live drawing and the compiled file agree on - the page
// knows what the user clicked by path, and both documents label the same part
// with it. Values are the classes to apply, space-separated, as the page has
// them.
//
// This is deliberately NOT a lamp feature. Nothing here knows what an LED is:
// the classes are applied to whatever elements carry those paths, and any rule
// the drawing's own stylesheet keys off them - a fill, an opacity, an animation,
// a colour on a cylinder's cap - takes effect for the same reason. `data-z-dome`
// is how these lamps happen to be modelled today, and a fix that could only see
// domes would light some of a device's indicators and not others.
// Scoped for the same reason overrides are: which lamps a viewer has lit is that
// viewer's opinion about the document, and two comparisons side by side are
// exactly the case where they differ.

/** Replace the runtime state classes, keyed by data-path. */
export function setNodeStates(map, scope) {
  const st = _sc(scope).states;
  st.clear();
  for (const [path, cls] of map instanceof Map ? map : Object.entries(map || {}))
    if (cls) st.set(path, String(cls));
}
export function clearNodeStates(scope) { _sc(scope).states.clear(); }
export function nodeStates(scope) { return new Map(_sc(scope).states); }

// Applied by CLEARING FIRST, over the whole document rather than over the paths
// in the registry. Turning a state off is a state change like any other, and it
// arrives as a path that is no longer in the map - so a version that only
// visited registered paths would light lamps correctly and never put one out.
/** Put the registered classes onto the matching elements of a parsed document. */
export function applyNodeStates(root, scope) {
  if (!root) return root;
  for (const el of root.querySelectorAll('[data-path][class]'))
    for (const c of [...el.classList]) if (c.startsWith('state-')) el.classList.remove(c);
  for (const [path, cls] of _sc(scope).states)
    for (const el of root.querySelectorAll(`[data-path="${CSS.escape(path)}"]`))
      el.classList.add(...cls.split(/\s+/).filter(Boolean));
  return root;
}

// Re-apply the registry to an already-serialised fragment. A state change repaints
// and never re-shapes, so a texture can be redrawn from the text it was built
// from without re-extracting any geometry - which is the whole reason clicking a
// state chip does not cost a rebuild.
export function restyleText(text, scope) {
  if (!text) return text;
  const div = document.createElement('div');
  div.innerHTML = text;
  applyNodeStates(div, scope);
  return div.innerHTML;
}

// A flat drawing outlines the faceplate and rounds its corners so the sheet
// metal reads as a part on a page. On a box, the outline of a face IS the box's
// edge, and both devices cost us something in 3D: the 0.5mm stroke sits half
// inside each face, so where two textured faces meet - front to side, rear to
// side - you get 0.5mm of near-black that reads as a gap you can see through,
// and rx="1.2" makes the four corners genuinely transparent under alphaTest, so
// at each box vertex you really can. Top edges escaped notice only because the
// lid art paints a bright line along them that swamps the seam. Square and
// de-stroke the faceplate before it becomes a texture; the geometry draws the
// edge.
export function squareFaceplate(text) {
  return text.replace(/<rect\b[^>]*\bid="chassis-faceplate"[^>]*>/,
    m => m.replace(/\s(?:rx|ry|stroke|stroke-width)="[^"]*"/g, ''));
}

export async function svgCanvas(url, wmm, hmm, flipX = false, flipYax = false, scope) {
  const text = await svgSource(url, scope);
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([text], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  const px = _px(scope);
  cv.width = Math.round(wmm * px); cv.height = Math.round(hmm * px);
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
// ?tex=plain drops mipmaps and anisotropy. Edge artefacts at a corner seen
// nearly edge-on are a sampler question, and samplers differ by GPU and browser
// in ways this machine cannot reproduce - so make the suspect switchable rather
// than argue about it. A corner line that survives ?tex=plain is not sampling.
const TEX_MODE = new URLSearchParams(location.search).get('tex') || '';
export function canvasTex(cv) {
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  if (TEX_MODE === 'plain') {
    tex.anisotropy = 1;
    tex.generateMipmaps = false;
    tex.minFilter = THREE.LinearFilter;
  } else {
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
  }
  tex.needsUpdate = true;
  return tex;
}
// Swap the art on a material that is already in the scene, disposing what it
// replaces. Textures are GPU allocations, and a state chip is a control a user
// will click repeatedly; leaking one per click is how a viewer that felt fine in
// review runs a machine out of memory in a demo.
export function remap(mat, cv) {
  const old = mat.map;
  const tex = canvasTex(cv);
  if (old) { tex.repeat.copy(old.repeat); tex.offset.copy(old.offset); }
  mat.map = tex;
  mat.needsUpdate = true;
  if (old) old.dispose();
}

// crop a mm-rect out of a face canvas (no mirroring: the rear floor plane's
// 180-degree rotation and the box rear-face UVs already reverse X to match)
export function crop(cv, r, pxmm = PXMM) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(r.w * pxmm)); c.height = Math.max(1, Math.round(r.h * pxmm));
  const ctx = c.getContext('2d');
  ctx.drawImage(cv, Math.round(r.x * pxmm), Math.round(r.y * pxmm), c.width, c.height, 0, 0, c.width, c.height);
  return c;
}

// standards-relief extraction: cavities (with interior features) + outward protrusions.
// Interior/plate art is re-rendered STANDALONE from its own nodes so bezel plates
// can carry arbitrary shapes (plug-outline apertures, LED holes) via alpha.
export async function extractRelief(url, scope) {
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = await svgSource(url, scope);
  document.body.appendChild(div);
  const svg = div.querySelector('svg');
  // before anything is measured or serialised: cleanText and every nodeSvg below
  // are taken from this document, so applying the runtime states once here is
  // what puts them on the face texture and on every piece of relief at once.
  applyNodeStates(svg, scope);
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
  // HOW FAR OFF THE FACE A FEATURE STARTS, summed up the ANCESTOR CHAIN.
  //
  // `lift` is not always written on the node that carries the feature. A composed
  // part gets its lift on the part's instance GROUP (render.py writes it there,
  // because that is the thing being positioned), while the `cyl` or `dome` that
  // has to move sits on a child of it - and `dataset` does not inherit. So an
  // MCX jack mounted on a block standing 15.9mm proud read lift 0 and drew at
  // the panel, underneath its own block.
  //
  // Sum rather than look one level up: a part on a raised block on a raised
  // bezel is a real shape, and the third case arrives the day after the second
  // is special-cased.
  //
  // THIS IS THE SECOND BUG OF EXACTLY THIS SHAPE IN ONE AFTERNOON, and the
  // pattern is worth naming because there will be a third. This module decides
  // what exists in 3D by QUERYING THE DOM FOR ATTRIBUTES, so every query is a
  // chance to miss data that is correctly present. The other case was the FRU
  // class list below, which asked for psu/fan/tab and so could not see the
  // twelve parts that spell the same classes `power` and `cooling`. In both,
  // the manifest was right, the compiled SVG was right, and the extractor threw
  // the answer away - which looks exactly like a modelling gap and is not one.
  // When something declared does not appear in 3D, suspect the selector first.
  const liftOf = el => {
    let z = 0;
    for (let n = el; n && n !== svg; n = n.parentElement) z += +(n.dataset.zLift || 0);
    return z;
  };
  // owning FRU (bay module / pull tab) of a node, for animated removal
  const ownerOf = el => {
    const a = el.closest('[data-path]');
    if (!a) return null;
    const root = a.dataset.path.split('/')[0];
    return _fru(scope).has(root) ? root : null;
  };
  // A NODE RENDERED ALONE LOSES THE SCOPE ITS RULES WERE WRITTEN IN, and that is
  // the third bug of the shape the `lift` note above names. `shared` carries the
  // face's whole stylesheet into every one of these standalone documents, but
  // the two forms render.py emits for a declared state colour are
  //
  //   #led-p65-a.state-10g          the element itself
  //   #led-p65-a .state-10g         a descendant of it
  //
  // and the element being rasterised here is `led-p65-a--lamp`, a CHILD of that
  // group. Reparented under a bare transform <g>, neither selector can match:
  // the ancestor simply is not in the document any more. Measured - a lamp whose
  // state is set paints rgb(34,197,94) on the face and rgb(60,65,71) in its own
  // node svg, from the same text and the same stylesheet.
  //
  // So the ancestor chain is rebuilt as empty groups carrying ONLY id and class -
  // never `transform`, since the CTM below already accounts for every one of
  // them, and re-applying them would move the art twice. data-path rides along
  // so a later restyle can tell which nodes a change reaches.
  //
  // This is not about states. Any id-scoped rule the compiled sheet carries -
  // a per-instance fill, a group override, a palette on a component - was
  // equally invisible to relief art before this, and looked like a modelling
  // gap rather than a plumbing one.
  const scopeWrap = (el, inner) => {
    for (let p = el.parentElement; p && p !== svg; p = p.parentElement) {
      const id = p.getAttribute('id'), cls = p.getAttribute('class'),
            path = p.getAttribute('data-path');
      if (!id && !cls) continue;      // a pure layout group changes no selector
      inner = `<g${id ? ` id="${id}"` : ''}${cls ? ` class="${cls}"` : ''}` +
              `${path ? ` data-path="${path}"` : ''}>${inner}</g>`;
    }
    return inner;
  };
  const nodeSvg = (el, rect) => {
    const m = inv.multiply(el.getScreenCTM());
    const clone = el.cloneNode(true);
    clone.removeAttribute('transform');   // the CTM below already includes it
    // raised descendants (collars, handles) render as their own geometry -
    // keep them out of cavity floors and plate textures
    for (const r of clone.querySelectorAll(
        '[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle],[data-z-dome][data-z-lift]'))
      r.style.display = 'none';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${rect.w} ${rect.h}"` +
      ` width="${rect.w}mm" height="${rect.h}mm">${shared}` +
      scopeWrap(el,
        `<g transform="matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e - rect.x} ${m.f - rect.y})">` +
        clone.outerHTML + `</g>`) + `</svg>`;
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
              lift: liftOf(el),
              round: !!el.dataset.round, cavSvg: nodeSvg(cavNode || el, rect),
              grpRect, grpSvg: nodeSvg(el, grpRect), features};
    });
  // pressed grooves: shallow standalone cavities whose own art is the floor.
  // `lift` is not optional here even though a groove is always pressed into the
  // face and always reads 0: every consumer of a cavity does arithmetic on it,
  // and `undefined - d / 2` is NaN, which Three.js does not reject - it culls the
  // mesh. Omitting it punched the faceplate and then silently deleted the walls
  // and floor that were supposed to close the hole, so the chassis had seven
  // full-length slits you could see the background through.
  for (const el of svg.querySelectorAll('[data-groove]')) {
    const rect = mmRect(el);
    cavities.push({...rect, owner: ownerOf(el), d: +el.dataset.groove, wall: '#25282c', round: false,
                   lift: liftOf(el),
                   cavSvg: nodeSvg(el, rect), grpRect: rect,
                   grpSvg: nodeSvg(el, rect), features: []});
  }
  const outs = [...svg.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), out: el.dataset.zOut && +el.dataset.zOut,
            cyl: el.dataset.zCyl && +el.dataset.zCyl,
            bar: el.dataset.zBar && +el.dataset.zBar,
            uhandle: el.dataset.zUhandle && +el.dataset.zUhandle,
            lift: liftOf(el),
            knurl: !!el.dataset.zKnurl,
            thread: el.dataset.zThread && +el.dataset.zThread,
            color: el.dataset.zColor || null,
            svgText: nodeSvg(el, rect)};
  });
  const domes = [...svg.querySelectorAll('[data-z-dome]')].map(el => {
    const rect = mmRect(el);
    // a lamp on a raised indicator bezel domes from THAT surface, not the panel
    return {...rect, owner: ownerOf(el), dome: +el.dataset.zDome, lift: liftOf(el),
            svgText: nodeSvg(el, rect)};
  });
  const vents = [...svg.querySelectorAll('[data-vent],[data-z-vent]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), depth: +(el.dataset.vent || el.dataset.zVent),
            svgText: nodeSvg(el, rect)};
  });
  // component instances only (data-ref) - contract elements can share a class
  // name (pull-tab has an element called "tab"), which would shadow the module
  const frus = [];
  // WHICH CLASSES GET A BODY. A component is field-replaceable because of what it
  // IS, and this list is the renderer's view of that. It was psu/fan/tab, which
  // silently excluded two whole classes that behave identically:
  //   power    - power ENTRY modules and trays. NOT a mislabelled psu: a PEM is a
  //              conduit that neither draws nor supplies, and collapsing the two
  //              would lose a distinction the power model depends on. 5 parts.
  //   cooling  - casa/ and cisco/ call a fan `cooling` where edgecore/, ufispace/
  //              and common/ call the same object `fan`. 7 parts against 3. That
  //              duplication is a DATA defect and is recorded in working/notes/;
  //              admitting both here is the renderer refusing to be the place it
  //              gets fixed, not an endorsement of it.
  // The visible symptom was that every Casa and Cisco fan and PEM drew as art
  // painted on the chassis plate, with no body and no ejection - and edgecore
  // "worked in 3D" for no better reason than its choice of word.
  //
  // THAT LIST IS NOW A FALLBACK. A part says how it MOVES - `data-behaviour`,
  // one of fills / occupies / mounts - and a body is owed to anything that comes
  // out, which is `fills` (into an aperture) and `occupies` (into a receptacle).
  // The class list could never say that: it was a catalogue of nouns, so every
  // new removable type meant editing it, and a TRANSCEIVER - removable, and the
  // reason the SFP bail cannot pivot yet - was simply not on it. `mounts` is
  // deliberately excluded: a rack ear, a label and a ground lug attach to the
  // box and do not withdraw from it.
  //
  // The old list stays for drawings compiled before behaviours existed. It costs
  // one selector and means a stale dist/ does not silently lose every FRU.
  const BODY_CLASSES = ['psu', 'fan', 'tab', 'power', 'cooling'];
  const BODY_SELECTOR = ['[data-behaviour="fills"]', '[data-behaviour="occupies"]']
    .concat(BODY_CLASSES.map(c => `[data-class="${c}"]:not([data-behaviour])`)).join(',');
  for (const el of svg.querySelectorAll(BODY_SELECTOR)) {
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

// Build the relief geometry for one face: the recesses, raised parts, domes,
// vents and FRU sub-groups a compiled face describes. Returns nothing - it
// fills the collections the caller owns, because a device viewer wants these
// parented per instance while a rack viewer wants them built once per model.
export async function buildFaceRelief(F, ctx) {
  const {src, faceCv, faceSvg, facePunch, meshes,
         FRU_GROUPS, FRU_META, BODY_META, D, bodyBoxMesh} = ctx;
    // THE ONE THAT WAS MISSED LAST TIME read through ctx and named no scope, and
    // resolved against the default while looking like a rendering fault. Read the
    // density once, here, so every raster below is this viewer's.
    const PX = _px(ctx.scope);
    // Every texture below that was rasterised from a node's OWN art records how
    // to redraw itself. That is the whole cost model for a state change: it
    // repaints and never re-shapes, so nothing here has to be measured, extruded
    // or disposed again - only the handful of canvases the change actually
    // reaches. A full rebuild of this device is 1.0-1.4 s; one lamp is one
    // 1.6 ms raster and one face.
    //
    // Registered by TEXT, not by path, and the affected test is a substring
    // search over that text. A node's svg carries its ancestors (for scope) and
    // its descendants (for their own art), so any of the three can be what the
    // state class lands on - and asking the text is the only version of the
    // question that cannot miss one of the three.
    const restyle = ctx.restyle || [];
    const reg = (svgText, run) => { if (svgText) restyle.push({svgText, run}); };
    const fw = F.fw(), fh = F.fh();
    // a device need not declare every view; fall back to a plain face
    if (!(await fetch(src, {method: 'HEAD', cache: 'no-store'})).ok) {
      const cv0 = document.createElement('canvas');
      cv0.width = Math.round(fw * PX); cv0.height = Math.round(fh * PX);
      const c0 = cv0.getContext('2d');
      c0.fillStyle = '#3a3f44'; c0.fillRect(0, 0, cv0.width, cv0.height);
      faceCv[F.view] = cv0;
      return;
    }
    const {cavities, outs, domes, vents, frus, cleanText} = await extractRelief(src, ctx.scope);
    const faceText = squareFaceplate(cleanText);
    const cv = await rasterize(faceText, fw, fh, PX);
    faceCv[F.view] = cv;
    faceSvg[F.view] = faceText;   // LOD re-rasterises from this; keep it squared
    facePunch[F.view] = [];
    const grp = new THREE.Group();
    grp.position.set(...F.pos());
    grp.rotation.set(...F.rot);
    const LX = (x, w) => x + w / 2 - fw / 2;
    const LY = (y, h) => (F.flipLY ? -1 : 1) * (fh / 2 - (y + h / 2));
    const sideMats = c => Array.from({length: 6},
      () => new THREE.MeshLambertMaterial({color: c}));
    // each FRU gets a subgroup so its art and relief travel together when ejected
    const fruGroups = {};
    for (const f of frus) {
      const fg = new THREE.Group();
      grp.add(fg);
      fruGroups[f.path] = fg;
      FRU_GROUPS[f.path] = fg;
      const bd = BODY_META[f.ref];
      const depth = bd ? bd.depth : 60;
      // captive modules declare how far they pull out; removable FRUs clear the chassis
      const captive = bd && bd.travel;
      FRU_META[f.path] = {cls: f.cls, view: F.view, body: bd, captive: !!captive,
                          pull: Math.min(captive || depth * 1.5 + 25, D - 10)};
    }
    let curOwner = null;
    const addTo = obj => (curOwner && fruGroups[curOwner] ? fruGroups[curOwner] : grp).add(obj);
    for (const c of cavities) {
      curOwner = c.owner;
      const d = Math.min(c.d, D - 2);
      // floor + feature art comes from the cavity group rendered standalone, so
      // raised bezel plates (drawn over the cavity on the face) never leak in
      const gcv = await rasterize(c.grpSvg, c.grpRect.w, c.grpRect.h, PX);
      const floorCv = crop(gcv, {x: c.x - c.grpRect.x, y: c.y - c.grpRect.y, w: c.w, h: c.h}, PX);
      const cavCrops = [];
      const fctx = floorCv.getContext('2d');
      for (const ft of c.features) {
        ft.faceCv = crop(gcv, {x: ft.x - c.grpRect.x, y: ft.y - c.grpRect.y, w: ft.w, h: ft.h}, PX);
        cavCrops.push(ft);
        // remove the feature art from the floor (it lives on its own box now)
        const px = [Math.round((ft.x - c.x) * PX), Math.round((ft.y - c.y) * PX),
                    Math.round(ft.w * PX), Math.round(ft.h * PX)];
        if (ft.kind === 'sink') fctx.clearRect(...px);
        else { fctx.fillStyle = '#0d0f11'; fctx.fillRect(...px); }
      }
      // shape-accurate punch: the cavity node's own art defines the hole
      if (!c.lift) {   // a lifted cavity recesses from a raised part, so the
        // chassis face beneath it is already covered - punching it would leave
        // a hole straight through the faceplate
        const pctx = cv.getContext('2d');
        pctx.globalCompositeOperation = 'destination-out';
        pctx.drawImage(await rasterize(c.cavSvg, c.w, c.h, PX),
                       Math.round(c.x * PX), Math.round(c.y * PX));
        pctx.globalCompositeOperation = 'source-over';
        facePunch[F.view].push({kind: 'shape', svg: c.cavSvg,
                                x: c.x, y: c.y, w: c.w, h: c.h});
      }
      // walls are double-sided: the interior is the recess, and the exterior is
      // the cage/housing body seen through neighboring vent holes. The back face
      // is a separate dark exterior; the textured floor plane sits just inside it
      // (sink pockets punch through the floor's alpha, so the back stays clear
      // of the floor by the sink allowance).
      const wallMat = new THREE.MeshLambertMaterial({color: c.wall, side: THREE.DoubleSide});
      const backMat = new THREE.MeshLambertMaterial({color: 0x23262b, side: THREE.DoubleSide});
      let walls;
      if (c.round) {
        walls = new THREE.Mesh(
          new THREE.CylinderGeometry(c.w / 2, c.w / 2, d, 24, 1, true), wallMat);
        walls.rotation.x = Math.PI / 2;
      } else {
        const noFace = new THREE.MeshBasicMaterial({visible: false});
        walls = new THREE.Mesh(new THREE.BoxGeometry(c.w, c.h, d),
          [wallMat, wallMat, wallMat, wallMat, noFace, noFace]);
      }
      // A NON-FINITE POSITION IS NOT A DRAWING ERROR, IT IS A DISAPPEARANCE.
      // Three.js culls a mesh whose matrix holds a NaN rather than complaining,
      // so the failure looks exactly like geometry nobody wrote - which is how
      // seven see-through slits survived in a shipped drawing. Say it out loud.
      const zc = c.lift - d / 2;
      if (!Number.isFinite(zc) || !Number.isFinite(LX(c.x, c.w)) || !Number.isFinite(LY(c.y, c.h)))
        console.error('relief: cavity has a non-finite position and will not render',
                      {owner: c.owner, x: c.x, y: c.y, d, lift: c.lift});
      walls.position.set(LX(c.x, c.w), LY(c.y, c.h), zc);
      addTo(walls);
      // textured floor: the aperture art, pushed to the back of the recess
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h),
        new THREE.MeshBasicMaterial({map: canvasTex(floorCv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      floor.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d - 0.1));
      addTo(floor);
      // one raster feeds the floor and every raised feature standing in it, so
      // they are redrawn together from the one group svg they were cut from
      const floorMat = floor.material;
      reg(c.grpSvg, async text => {
        const g2 = await rasterize(text, c.grpRect.w, c.grpRect.h, PX);
        remap(floorMat, crop(g2, {x: c.x - c.grpRect.x, y: c.y - c.grpRect.y, w: c.w, h: c.h}, PX));
        for (const ft of cavCrops)
          if (ft.mat) remap(ft.mat,
            crop(g2, {x: ft.x - c.grpRect.x, y: ft.y - c.grpRect.y, w: ft.w, h: ft.h}, PX));
      });
      // closed exterior back, deep enough to clear any sink pockets
      const maxSink = Math.max(0, ...c.features.filter(f => f.kind === 'sink').map(f => f.val));
      const back = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h), backMat);
      back.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d + maxSink + 0.15));
      addTo(back);
      for (const ft of c.features) {
        if (ft.kind === 'top') {
          const hgt = Math.min(ft.val, d - 0.2);
          const mats = sideMats(ft.color);
          mats[4] = new THREE.MeshBasicMaterial({map: canvasTex(ft.faceCv)});
          ft.mat = mats[4];
          const m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, hgt), mats);
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), c.lift - (d - hgt / 2));
          addTo(m);
        } else {   // sink: a deeper pocket beyond the floor
          const m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, ft.val),
            new THREE.MeshLambertMaterial({color: ft.color, side: THREE.DoubleSide}));
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), -(d + ft.val / 2));
          addTo(m);
        }
      }
    }
    // Air vents stay as painted art rather than punched alpha. Punching them made
    // each honeycomb cell an alphaTest cutout, and alphaTest is a binary decision
    // taken AFTER texture filtering - at a grazing angle, with dozens of cells
    // falling in one pixel, the filtered alpha sits near the threshold and speckles.
    // Neither mipmaps nor alphaToCoverage can fix that; both act before the cut.
    // Left as colour, mipmapping averages the cells to smooth shading, which is
    // what you actually see on a real chassis from any distance.
    // Large openings (cavities, FRU bays) are punched elsewhere and do not moire,
    // being a handful of big rectangles rather than a fine repeating lattice.
    for (const v of vents) {
      // Vents are painted into the face art (see above), so the face is opaque
      // here and a box behind it can only ever show through as z-fighting. It sat
      // 0.05mm back, far finer than the depth buffer resolves, which is what was
      // speckling along the side faces. Nothing to draw.
      curOwner = v.owner;
    }
    for (const dm of domes) { // gentle domes: node art draped on a paraboloid cap
      curOwner = dm.owner;
      // (LED lamps, bulged fan guards); apex proud, rim sunk 0.15 into the face
      const dcv = await rasterize(dm.svgText, dm.w, dm.h, PX);
      const geo = new THREE.CircleGeometry(0.5, 48);
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const rr = Math.min(1, Math.hypot(pos.getX(i), pos.getY(i)) * 2);
        pos.setZ(i, 1 - rr * rr);
      }
      geo.computeVertexNormals();
      const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial(
        {map: canvasTex(dcv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      m.scale.set(dm.w, dm.h, dm.dome + 0.15);
      m.position.set(LX(dm.x, dm.w), LY(dm.y, dm.h), (dm.lift || 0) - 0.15);
      addTo(m);
      reg(dm.svgText, async text => remap(m.material, await rasterize(text, dm.w, dm.h, PX)));
    }
    for (const o of outs) {   // protrusions: bezel plates, handles, studs, tubes
      curOwner = o.owner;
      const ocv = await rasterize(o.svgText, o.w, o.h, PX);
      if (!o.color) {   // side color: sample the node's own art
        const px = ocv.getContext('2d').getImageData(
          Math.floor(ocv.width / 2), Math.floor(ocv.height / 2), 1, 1).data;
        o.color = `rgb(${px[0]},${px[1]},${px[2]})`;
      }
      const faceTex = new THREE.MeshBasicMaterial(
        {map: canvasTex(ocv), transparent: true, alphaTest: 0.1, alphaToCoverage: true});
      reg(o.svgText, async text => remap(faceTex, await rasterize(text, o.w, o.h, PX)));
      if (o.uhandle !== undefined && o.uhandle !== '') {
        const far = +o.uhandle;
        const horizontal = o.w >= o.h;
        const dia = Math.min(o.w, o.h), r = dia / 2, Rb = dia;
        const zBar = far - r, legH = Math.max(0.5, zBar - Rb);
        const uLen = Math.max(o.w, o.h);
        const u0 = horizontal ? o.x : o.y;
        const a = u0 + r, b = u0 + uLen - r;          // leg centerlines (svg coords)
        const cc = horizontal ? o.y + o.h / 2 : o.x + o.w / 2;  // cross-axis center
        const mat = new THREE.MeshLambertMaterial({color: o.color});
        const P = (u, z) => horizontal
          ? [u - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - cc), z]
          : [cc - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - u), z];
        for (const u of [a, b]) {                     // legs
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(r, r, legH, 16), mat);
          leg.rotation.x = Math.PI / 2;
          leg.position.set(...P(u, legH / 2));
          addTo(leg);
        }
        const barLen = (b - Rb) - (a + Rb);           // crossbar between the bends
        if (barLen > 0.1) {
          const bar = new THREE.Mesh(new THREE.CylinderGeometry(r, r, barLen, 16), mat);
          if (horizontal) bar.rotation.z = Math.PI / 2;
          bar.position.set(...P((a + b) / 2, zBar));
          addTo(bar);
        }
        for (const [u, near] of [[a + Rb, a], [b - Rb, b]]) {   // continuous bends
          const holder = new THREE.Group();
          holder.position.set(...P(u, zBar - Rb));
          holder.rotation.z = horizontal ? 0 : Math.PI / 2;
          const elbow = new THREE.Mesh(new THREE.TorusGeometry(Rb, r, 12, 16, Math.PI / 2), mat);
          // low-u corner sweeps (-u -> +z), high-u corner (+u -> +z), in holder-local xy
          const legLocalU = horizontal ? near : -near;   // svg y runs opposite to local up
          const cornerLocalU = horizontal ? u : -u;
          elbow.rotation.set(Math.PI / 2, 0, legLocalU < cornerLocalU ? Math.PI / 2 : 0);
          holder.add(elbow);
          addTo(holder);
        }
      } else if (o.bar !== undefined && o.bar !== '') {
        // round tube along the node's long axis, lift..lift+bar off the face
        const len = Math.max(o.w, o.h), r = o.bar / 2;
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 16),
          new THREE.MeshLambertMaterial({color: o.color}));
        if (o.w >= o.h) m.rotation.z = Math.PI / 2;   // horizontal bar
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + r);
        addTo(m);
      } else if (o.cyl !== undefined && o.cyl !== '') {
        // cylinder: lift..lift+cyl, top cap carries the node art
        const r = Math.min(o.w, o.h) / 2;
        let side;
        if (o.thread) {
          // single-start helix: one diagonal per tile, tiled once around the
          // circumference and once per pitch along the axis, so the stripe meets
          // itself at the seam and reads as a continuous thread rather than rings
          const tc = document.createElement('canvas');
          tc.width = 32; tc.height = 32;
          const tx = tc.getContext('2d');
          tx.fillStyle = o.color; tx.fillRect(0, 0, 32, 32);
          tx.strokeStyle = 'rgba(0,0,0,0.42)'; tx.lineWidth = 7;
          tx.lineCap = 'butt';
          for (const dy of [-32, 0, 32]) {          // wrap copies keep it seamless
            tx.beginPath(); tx.moveTo(0, 32 + dy); tx.lineTo(32, dy); tx.stroke();
          }
          tx.strokeStyle = 'rgba(255,255,255,0.20)'; tx.lineWidth = 2.5;
          for (const dy of [-32, 0, 32]) {
            tx.beginPath(); tx.moveTo(0, 27 + dy); tx.lineTo(32, dy - 5); tx.stroke();
          }
          const ttex = canvasTex(tc);
          ttex.wrapS = ttex.wrapT = THREE.RepeatWrapping;
          ttex.repeat.set(1, Math.max(1, Math.round(o.cyl / o.thread)));
          side = new THREE.MeshLambertMaterial({map: ttex});
        } else if (o.knurl) {  // fine grip ridges wrapped around the circumference
          const kc = document.createElement('canvas');
          kc.width = 8; kc.height = 8;
          const kctx = kc.getContext('2d');
          kctx.fillStyle = o.color; kctx.fillRect(0, 0, 8, 8);
          kctx.fillStyle = 'rgba(0,0,0,0.45)'; kctx.fillRect(4, 0, 4, 8);
          const ktex = canvasTex(kc);
          ktex.wrapS = THREE.RepeatWrapping;
          ktex.repeat.set(Math.max(12, Math.round(2 * Math.PI * r / 0.5)), 1);
          ktex.magFilter = THREE.NearestFilter;
          side = new THREE.MeshLambertMaterial({map: ktex});
        } else {
          side = new THREE.MeshLambertMaterial({color: o.color});
        }
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, o.cyl, 24),
          [side, faceTex, side]);
        m.rotation.x = Math.PI / 2;
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + o.cyl / 2);
        addTo(m);
      } else {
        // box: lift..out (lift defaults to 0 = sits on the face)
        const depth = o.out - o.lift;
        const mats = sideMats(o.color);
        mats[4] = faceTex;
        const m = new THREE.Mesh(new THREE.BoxGeometry(o.w, o.h, depth), mats);
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + depth / 2);
        addTo(m);
      }
    }
    curOwner = null;
    for (const f of frus) {   // move the FRU's face art into its group; leave a bay
      const fg = fruGroups[f.path];
      const faceCrop = crop(cv, f, PX);
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(f.w, f.h),
        new THREE.MeshBasicMaterial({map: canvasTex(faceCrop), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      plane.position.set(LX(f.x, f.w), LY(f.y, f.h), 0.3);
      fg.add(plane);
      // CLEAR, never fill: an opaque patch on the chassis face would occlude
      // everything behind it (the module's own cavities, pins, bay interior)
      cv.getContext('2d').clearRect(Math.round(f.x * PX), Math.round(f.y * PX),
                                    Math.round(f.w * PX), Math.round(f.h * PX));
      facePunch[F.view].push({kind: 'rect', x: f.x, y: f.y, w: f.w, h: f.h});
      const meta = FRU_META[f.path];
      if (meta.body) {   // full module body travels with the FRU
        const {mesh, fp, d} = await bodyBoxMesh(meta.body, f.w, f.h);
        mesh.position.set(LX(f.x + fp.at[0], fp.size[0]),
                          LY(f.y + fp.at[1], fp.size[1]), -d / 2 - 0.05);
        fg.add(mesh);
      }
      // empty bay: interior surfaces only, so it never occludes the module's
      // own cavities (the C14 inlet pins live inside this volume)
      const bd = meta.body ? meta.body.depth : 60;
      const bay = new THREE.Mesh(new THREE.BoxGeometry(f.w + 0.6, f.h + 0.6, bd),
        new THREE.MeshLambertMaterial({color: 0x0a0c0e, side: THREE.BackSide}));
      bay.position.set(LX(f.x, f.w), LY(f.y, f.h), -bd / 2 - 0.2);
      grp.add(bay);
    }
  meshes.push(grp);
}
