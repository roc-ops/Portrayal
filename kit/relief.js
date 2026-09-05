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

// A BODY THAT IS NOT ONE BOX. A module's `body` is a box the size of its face
// (or its `footprint`) and `depth` deep; a riser is a plate with a 1.6 mm PCB
// standing behind it and three connectors on the PCB, and a box that size hid
// the chassis interior while a box cut to the plate left the PCB behind when
// the riser was ejected. `body.boxes` lists the pieces instead, each in the
// face's own frame, starting `from` mm behind the plane. This resolves either
// form to a list the two builders (the FRU in a chassis, the part alone) draw
// the same way; it is pure, so it is checked under node.
// A rect in a module's own frame, mapped through the module's placement (its
// translate, and its reflection when `mirror: true`) into face mm. Corners
// through the matrix, then the min/max, so a mirrored module's box comes out
// on the mirrored side with a positive width.
export function localToFace(m, r) {
  if (!m) return {x: r.x, y: r.y, w: r.w, h: r.h};
  const pt = (x, y) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f});
  const p = pt(r.x, r.y), q = pt(r.x + r.w, r.y + r.h);
  return {x: Math.min(p.x, q.x), y: Math.min(p.y, q.y), w: Math.abs(q.x - p.x), h: Math.abs(q.y - p.y)};
}

export function bodyBoxes(body, faceW, faceH) {
  const color = body.color || '#3a3f44';
  if (body.boxes && body.boxes.length) {
    return body.boxes.map((b, i) => ({
      id: b.id || `box-${i}`, x: b.at[0], y: b.at[1], w: b.size[0], h: b.size[1],
      z0: b.from || 0, z1: (b.from || 0) + b.depth, color: b.color || color}));
  }
  const fp = body.footprint || {at: [0, 0], size: [faceW, faceH]};
  return [{id: 'body', x: fp.at[0], y: fp.at[1], w: fp.size[0], h: fp.size[1],
           z0: 0, z1: body.depth, color}];
}

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
//
// AND THE FLAG ITSELF IS GONE NOW, for the reason dist.js already gave about the
// JSON: `no-store` kept a rebuilt dist from going stale during development, and
// the memo below does that job within a load - but it also meant the browser
// could not reuse the file across page loads, forever. Entering the 3D tab on
// one switch is 24 requests and 284 KB of face SVG, none of it revalidatable.
// The drawings are much larger than the JSON that argument was made about.
//
// If you are iterating on the build and want the next load to see new bytes,
// hard-reload. That is the tool for it, not a permanent header on every
// drawing.
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
  return {overrides: new Map(), states: new Map(), pulled: new Set(),
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
  // A MISS IS MEMOISED AS THE EMPTY STRING, which does two things at once.
  //
  // It removes the HEAD probe. `buildFaceRelief` used to ask whether a view
  // existed with a HEAD and then fetch the same URL again, so every face cost
  // two round trips and the second proved nothing the first had not. Measured on
  // a six-device rack: 66 requests of which 30 were duplicates, one HEAD and one
  // GET per face per device. On localhost that is 287 ms of a 7.4 s build; over
  // a 50 ms link it is 30 serial round trips, about 1.5 s of pure latency, and
  // it scales with the devices on screen.
  //
  // It also fixes a quieter bug: this used to call `r.text()` whatever the
  // status, so a 404's HTML was handed back as if it were a drawing, to be
  // parsed as SVG and fail somewhere further away from the cause.
  //
  // EMPTY STRING RATHER THAN NULL, because every existing caller then degrades
  // instead of throwing: `''.matchAll` yields nothing, `innerHTML = ''` empties
  // the node, `parseFromString('')` raises a parsererror the caller already
  // checks for, and a Blob of '' fails the image load exactly as a 404 page did.
  if (!SVG_CACHE.has(url))
    SVG_CACHE.set(url, fetch(url).then(r => r.ok ? r.text() : ''));
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

// WHAT A VIEWER HAS WRITTEN ON A PART. A field is a `data-from` text node the
// part declares (`fields` in its contract, carried in components.json): a
// supply's wattage, a drive's capacity. The value replaces the node's text and
// lands on the part's group as `data-<key>`, in the parsed document and in
// every texture redrawn from it - the same route a lamp state takes. Keyed by
// the part's data-path; a map of key -> value per part; an empty value hides
// the node, as render.py's fill does.
export function setNodeFields(map, scope) {
  const st = _sc(scope).fields || (_sc(scope).fields = new Map());
  st.clear();
  for (const [path, vals] of map instanceof Map ? map : Object.entries(map || {}))
    if (vals && Object.keys(vals).length) st.set(path, {...vals});
}
export function nodeFields(scope) { return new Map(_sc(scope).fields || []); }
export function applyNodeFields(root, scope) {
  if (!root) return root;
  const st = _sc(scope).fields;
  if (!st || !st.size) return root;
  for (const [path, vals] of st)
    for (const el of root.querySelectorAll(`[data-path="${CSS.escape(path)}"]`))
      for (const [k, v] of Object.entries(vals)) {
        const val = v == null ? '' : String(v);
        el.setAttribute(`data-${k}`, val);
        for (const t of el.querySelectorAll(`[data-from="${CSS.escape(k)}"]`)) {
          t.textContent = val;
          if (val) t.removeAttribute('display'); else t.setAttribute('display', 'none');
        }
      }
  return root;
}
export function nodeStates(scope) { return new Map(_sc(scope).states); }

// WHAT A VIEWER HAS TAKEN OFF. A cover hides what is behind it, which is the
// whole reason it is on the device and the whole reason someone wants it off. In
// 2D that is a CSS rule; in 3D the face is a rasterised canvas, so the part is
// baked into a texture and an attribute set after the bake changes nothing. That
// is why pulling had no effect in 3D at all.
//
// So it is applied to the TEXT a texture is painted from, which puts it on the
// same path a lamp state already takes - repaint, never re-shape.
//
// display="none" AND NOT REMOVAL, because a repaint has to be able to put the
// part back. `applyNodeStates` gets away with clearing state classes because it
// can always re-add them; an element that has been deleted from the fragment a
// texture is redrawn from is gone for the session. The marker attribute is what
// distinguishes a part this viewer hid from one the author authored hidden.
//
// NESTED PARTS COME WITH IT. Pulling a supply takes its lamps and its ports,
// because they are on it - a tree row pointing at geometry that is no longer
// drawn is exactly the dangling selection this was reported for.
export function setPulled(paths, scope) {
  const s = _sc(scope).pulled;
  s.clear();
  for (const p of paths || []) if (p) s.add(String(p));
}
export function clearPulled(scope) { _sc(scope).pulled.clear(); }
export function pulledPaths(scope) { return new Set(_sc(scope).pulled); }

/** Is `path` the pulled part itself, or something sitting on it? */
function _isPulled(path, pulled) {
  if (!path) return false;
  for (const p of pulled) if (path === p || path.startsWith(p + "/")) return true;
  return false;
}

/** Hide what this viewer has taken off, in a parsed document. */
export function applyPulled(root, scope) {
  if (!root) return root;
  for (const el of root.querySelectorAll("[data-portrayal-pulled]")) {
    el.removeAttribute("data-portrayal-pulled");
    el.removeAttribute("display");
  }
  const pulled = _sc(scope).pulled;
  if (!pulled.size) return root;
  for (const el of root.querySelectorAll("[data-path]"))
    if (_isPulled(el.getAttribute("data-path"), pulled)) {
      el.setAttribute("data-portrayal-pulled", "");
      el.setAttribute("display", "none");
    }
  // a part's projections on other faces go with it
  for (const el of root.querySelectorAll("[data-projection][data-of]"))
    if (_isPulled(el.getAttribute("data-of"), pulled)) {
      el.setAttribute("data-portrayal-pulled", "");
      el.setAttribute("display", "none");
    }
  return root;
}

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
  applyNodeFields(div, scope);
  applyPulled(div, scope);
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
  // A PROJECTION IS FLAT. A part seated on one face may be drawn again on
  // another as `data-projection` (render.py's `plan:`), for the 2D view with
  // the lid off. Its body already stands in the scene from the face that
  // holds it, so nothing inside one is extracted here - it is texture only.
  const q = sel => [...svg.querySelectorAll(sel)].filter(el => !el.closest('[data-projection]'));
  // before anything is measured or serialised: cleanText and every nodeSvg below
  // are taken from this document, so applying the runtime states once here is
  // what puts them on the face texture and on every piece of relief at once.
  applyNodeStates(svg, scope);
  // A part the viewer has taken off is REMOVED here rather than hidden, and only
  // here: this document is built to be measured and then discarded, so nothing
  // has to put it back. Left as display:none it would measure 0x0 and extrude a
  // degenerate feature instead of none at all - a cover that is off should leave
  // no geometry behind, not a flat one.
  applyPulled(svg, scope);
  for (const el of [...q("[data-portrayal-pulled]")]) el.remove();
  const inv = svg.getScreenCTM().inverse();
  const mmRect = el => {
    const b = el.getBBox();
    const m = inv.multiply(el.getScreenCTM());
    const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
    const x0 = Math.min(pts[0].x, pts[1].x), y0 = Math.min(pts[0].y, pts[1].y);
    return {x: x0, y: y0, w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y)};
  };
  const shared = [...q('style, defs')].map(n => n.outerHTML).join('');
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
  // WHICH PART DID THIS COME FROM - which is not the same question as "is this
  // part a FRU", and conflating the two is what made covers unpullable.
  // The answer is used for two different jobs. Grouping into an ejectable
  // subgroup is still FRU-only: a module leaves a BAY behind it, and building
  // one behind a bolted-on cover would punch a hole in the chassis. But TAGGING
  // every mesh with the part that produced it costs nothing and is what lets a
  // cover be hidden without being ejected.
  const ownerOf = el => {
    const a = el.closest('[data-path]');
    if (!a) return null;
    return a.dataset.path.split('/')[0] || null;
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
  // THE OUTLINE OF A NODE, in face millimetres, as closed rings.
  //
  // SAMPLED RATHER THAN PARSED. getPointAtLength walks a path at constant arc
  // length and consumes NO length crossing from one subpath to the next, so two
  // consecutive samples that jump much further than the step are a subpath
  // boundary. That finds the rings without writing a path parser, and it works
  // for curves exactly as well as for lines - which matters, because these
  // outlines are CAD contours and the next one may not be polygonal.
  //
  // A ring whose centroid falls inside another is a HOLE; one that does not is a
  // separate island. That is what makes the screw hole in the rear handle's left
  // foot a hole rather than a second lump of metal.
  //
  // A `fill="none"` path is a stroked centreline - a line, not an area - and
  // extruding it would build a ribbon where the drawing shows a bracket.
  const RING_STEP = 0.25;
  const inRing = (pt, ring) => {
    let hit = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const a = ring[i], b = ring[j];
      if ((a[1] > pt[1]) !== (b[1] > pt[1]) &&
          pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]) hit = !hit;
    }
    return hit;
  };
  const ringsOf = el => {
    const m = inv.multiply(el.getScreenCTM());
    const paths = el.tagName === 'path' ? [el] : [...el.querySelectorAll('path')];
    const rings = [];
    for (const q of paths) {
      if (q.getAttribute('fill') === 'none') continue;
      let total = 0;
      try { total = q.getTotalLength(); } catch (e) { continue; }
      if (!(total > 0)) continue;
      const n = Math.max(8, Math.min(4000, Math.ceil(total / RING_STEP)));
      const step = total / n;
      let cur = [], prev = null;
      for (let i = 0; i <= n; i++) {
        const s = q.getPointAtLength(step * i);
        const pt = [m.a * s.x + m.c * s.y + m.e, m.b * s.x + m.d * s.y + m.f];
        if (prev && Math.hypot(pt[0] - prev[0], pt[1] - prev[1]) > 4 * step) {
          if (cur.length > 2) rings.push(cur);
          cur = [];
        }
        cur.push(pt); prev = pt;
      }
      if (cur.length > 2) rings.push(cur);
    }
    if (!rings.length) return null;
    const area = r => {
      let a = 0;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++)
        a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
      return Math.abs(a / 2);
    };
    const cent = r => [r.reduce((s, c) => s + c[0], 0) / r.length,
                       r.reduce((s, c) => s + c[1], 0) / r.length];
    rings.sort((a, b) => area(b) - area(a));
    const out = [];
    for (const r of rings) {
      const host = out.find(o => inRing(cent(r), o.shell));
      if (host) host.holes.push(r); else out.push({shell: r, holes: []});
    }
    return out;
  };

  const cavities = [...q('[data-depth]')]
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
              wallsInside: el.dataset.walls === 'inside',
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
  for (const el of q('[data-groove]')) {
    const rect = mmRect(el);
    cavities.push({...rect, owner: ownerOf(el), d: +el.dataset.groove, wall: '#25282c', round: false,
                   lift: liftOf(el),
                   cavSvg: nodeSvg(el, rect), grpRect: rect,
                   grpSvg: nodeSvg(el, rect), features: []});
  }
  const outs = [...q('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), out: el.dataset.zOut && +el.dataset.zOut,
            cyl: el.dataset.zCyl && +el.dataset.zCyl,
            bar: el.dataset.zBar && +el.dataset.zBar,
            uhandle: el.dataset.zUhandle && +el.dataset.zUhandle,
            lift: liftOf(el),
            knurl: !!el.dataset.zKnurl,
            thread: el.dataset.zThread && +el.dataset.zThread,
            color: el.dataset.zColor || null,
            rings: el.dataset.zShape ? ringsOf(el) : null,
            profile: el.dataset.zProfile
              ? el.dataset.zProfile.split(',').map(p => p.split(':').map(Number)) : null,
            profileY: el.dataset.zProfileY
              ? el.dataset.zProfileY.split(',').map(p => p.split(':').map(Number)) : null,
            svgText: nodeSvg(el, rect)};
  });
  const domes = [...q('[data-z-dome]')].map(el => {
    const rect = mmRect(el);
    // a lamp on a raised indicator bezel domes from THAT surface, not the panel
    return {...rect, owner: ownerOf(el), dome: +el.dataset.zDome, lift: liftOf(el),
            svgText: nodeSvg(el, rect)};
  });
  const vents = [...q('[data-vent],[data-z-vent]')].map(el => {
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
  // A MODULE INSIDE A MODULE HAS A BODY OF ITS OWN. A card in a riser slot is
  // not a FRU here - it comes out with its riser - but its PCB is real, and
  // it hides on its own path. Collected beside the FRUs and built into the
  // owner's ejection group.
  const subBodies = [];
  for (const el of q(BODY_SELECTOR)) {
    if (!el.dataset.ref) continue;
    const full = el.dataset.path || '';
    const path = full.split('/')[0];
    if (!path) continue;
    // a module in a chassis bay is `bay/module`; one in a module's bay is
    // `bay/module/slot/module` - the third segment is what makes it nested
    if (full.split('/').length > 2) {
      // the body index lives with the builder; every nested module is
      // recorded here and the builder keeps the ones that declare boxes
      const m = inv.multiply(el.getScreenCTM());
      subBodies.push({path: full, owner: path, ref: el.dataset.ref.split(':')[0], lift: liftOf(el),
                      toFace: {a: m.a, b: m.b, c: m.c, d: m.d, e: m.e, f: m.f}});
      continue;
    }
    if (frus.some(f => f.path === path)) continue;
    // `data-body-depth` IS THE MODULE'S OWN DEPTH and was being thrown
    // away here, so every module without a `body:` block fell back to a
    // hardcoded 60 mm bay below - 60 for a 40 mm control panel, 60 for a
    // 25 mm drive blank. On a part seated in a rack ear that hole runs
    // straight out the back of the flange.
    // A MODULE IN A BAY THAT OPENS IN A WELL IS NOT AT THE FACE. The bay
    // carries the well's floor as a negative z-lift (render.py's `in:`), and
    // the module's plane, body and bay box all sit that far down.
    const frect = mmRect(el);
    // A SHELF LEAVES NO HOLE. A bay with a `floor:` is a shelf in a well - a
    // card on its riser slot - and the dark box the kit leaves behind a pulled
    // module would stand on the card below it. Read off the bay, which is the
    // module's parent.
    const shelf = !!(el.parentElement && el.parentElement.dataset && el.parentElement.dataset.shelf);
    frus.push({path, ref: el.dataset.ref.split(':')[0],
               cls: el.dataset.class, lift: liftOf(el), shelf,
               bodyDepth: +el.dataset.bodyDepth || null, ...frect,
               // its own art, so the plane can be cut to the module's SHAPE
               svgText: nodeSvg(el, frect),
               // THE MODULE'S OWN FRAME, not its drawn box. A riser's slot
               // brackets hang 13.4 mm outboard of its plate, so the bbox
               // starts 13.4 left of the contract's origin - and a body box
               // placed from the bbox stood that far out through the chassis
               // wall. This is local mm -> face mm, mirror included, so a box
               // in the contract's frame lands where the contract says.
               toFace: (() => { const m = inv.multiply(el.getScreenCTM());
                                return {a: m.a, b: m.b, c: m.c, d: m.d, e: m.e, f: m.f}; })()});
  }
  for (const el of q('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]'))
    el.style.display = 'none';
  const cleanText = svg.outerHTML;
  div.remove();
  return {cavities, outs, domes, vents, frus, subBodies, cleanText};
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
    // HOW FAR INTO THE BOX THIS FACE LOOKS, which is not the same number on every
    // face and was the device's DEPTH on all of them. Depth is right for front and
    // rear and wrong for the other four: into a top or a bottom you go the chassis
    // HEIGHT, into a side its WIDTH. Nothing caught it because the parts on those
    // faces are shallow - a ground lug does not test a depth clamp - but on a 1U
    // server, H 44 and D 700, a top-face cavity was free to sink 698 mm into a
    // 44 mm box and come out of the underside. Falls back to D so a caller that
    // has not been taught the difference behaves exactly as before.
    const INTO = ctx.deep ?? D;
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
    // `let`, because the drawing may state a different size below and a face
    // is drawn at its own size rather than at its plane's.
    let fw = F.fw(), fh = F.fh();
    // A device need not declare every view; fall back to a plain face. Asked
    // through svgSource so the answer is cached: when the view DOES exist this
    // is the same fetch extractRelief is about to want, and when it does not the
    // miss is remembered rather than re-probed on the next LOD pass.
    if (!(await svgSource(src, ctx.scope))) {
      const cv0 = document.createElement('canvas');
      cv0.width = Math.round(fw * PX); cv0.height = Math.round(fh * PX);
      const c0 = cv0.getContext('2d');
      c0.fillStyle = '#3a3f44'; c0.fillRect(0, 0, cv0.width, cv0.height);
      faceCv[F.view] = cv0;
      return;
    }
    const {cavities, outs, domes, vents, frus, subBodies = [], cleanText} = await extractRelief(src, ctx.scope);
    const faceText = squareFaceplate(cleanText);
    // THE DRAWING'S OWN SIZE WINS, because the face is not obliged to match the
    // plane it sits on. The R740xd's front is the 482.6 mm rack face - Dell
    // builds the flanges into the faceplate and puts the VGA, the power button
    // and the health lamp in them - over a 434 mm body. Taking fw from the
    // chassis squashed the artwork by 10% AND placed every feature against the
    // wrong centre, which threw the ear's ports 36 mm off the end of the box.
    // For every other face in the library the two numbers are already equal, so
    // this changes nothing that was right.
    const vb = /viewBox\s*=\s*"\s*[-\d.eE+]+\s+[-\d.eE+]+\s+([\d.eE+-]+)\s+([\d.eE+-]+)/.exec(faceText);
    if (vb) {
      const dw = parseFloat(vb[1]), dh = parseFloat(vb[2]);
      if (dw > 0 && dh > 0) { fw = dw; fh = dh; }
    }
    if (ctx.faceMM) ctx.faceMM[F.view] = [fw, fh];
    const cv = await rasterize(faceText, fw, fh, PX, !!F.flipLX, !!F.flipLY);
    // THE ART BEFORE ANY HOLE IS PUNCHED IN IT. A cavity punches `cv` with its
    // own outline, and a module whose bay opens inside that cavity - a drive in
    // the mid tray, a DIMM on the board - had its face art punched away before
    // the FRU pass came to crop it, so every such module was a dark rectangle.
    const artCv = document.createElement('canvas');
    artCv.width = cv.width; artCv.height = cv.height;
    artCv.getContext('2d').drawImage(cv, 0, 0);
    faceCv[F.view] = cv;
    faceSvg[F.view] = faceText;   // LOD re-rasterises from this; keep it squared
    facePunch[F.view] = [];
    const grp = new THREE.Group();
    grp.position.set(...F.pos());
    grp.rotation.set(...F.rot);
    // A FACE MAY BE AUTHORED MIRRORED and the underside is - a bottom view is drawn
    // as if the device were rolled towards you, so its art is flipped in both axes
    // against the face's local frame. `flipLY` was here already and no face ever set
    // it; `flipLX` is its partner, and the pair is what lets the bottom carry relief.
    const LX = (x, w) => (F.flipLX ? -1 : 1) * (x + w / 2 - fw / 2);
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
      // a `body:` block is the best answer, the part's own size.d the next, and
      // 60 only when a drawing predates `data-body-depth` entirely
      const depth = bd ? bd.depth : (f.bodyDepth || 60);
      // captive modules declare how far they pull out; removable FRUs clear the chassis
      const captive = bd && bd.travel;
      FRU_META[f.path] = {cls: f.cls, view: F.view, body: bd, captive: !!captive,
                          bodyDepth: f.bodyDepth,
                          pull: Math.min(captive || depth * 1.5 + 25, INTO - 10)};
    }
    let curOwner = null;
    // Tagged on the way in, so `setPulled` can hide a part's relief without the
    // part having to be a FRU. A cover's meshes stay in the shared group - they
    // are not going anywhere - and simply stop being drawn.
    const addTo = obj => {
      if (curOwner) obj.userData.portrayalPath = curOwner;
      return (curOwner && fruGroups[curOwner] ? fruGroups[curOwner] : grp).add(obj);
    };
    for (const c of cavities) {
      curOwner = c.owner;
      const d = Math.min(c.d, INTO - 2);
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
      // A WELL WHOSE SIDES ARE THE CHASSIS SHOWS THEM FROM INSIDE ONLY. The
      // double side is for a port cage, whose housing is seen through the vent
      // next to it. The R740xd's board well is 80 mm deep to the rear metal:
      // drawn double-sided, its rear wall stood a hair behind the rear panel
      // and everything looking in from that face - the C14 inlet's pins, the
      // rear drive bays - ended at a flat plane.
      const wallMat = new THREE.MeshLambertMaterial({color: c.wall,
        side: c.wallsInside ? THREE.BackSide : THREE.DoubleSide});
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
      } else if ((o.profile && o.profile.length >= 2) || (o.profileY && o.profileY.length >= 2)) {
        // A DEPTH THAT VARIES ACROSS THE NODE, BOTH WAYS. `profile` is [x, out]
        // from the left edge, `profile-y` is [y, out] from the top edge, and
        // the surface at any point is the LESSER of the two. The R740xd's
        // bezel is a honeycomb 20 proud whose end caps fall away to 9 at the
        // tips and whose bottom rail sits back at 15 - a section like a
        // football sliced a third through, in both directions - and a box
        // drew it as a slab with the right picture on the front. Built as a
        // height field with the node's art on it and skirts down to the face.
        const px = o.profile && o.profile.length >= 2 ? o.profile : [[0, o.out], [o.w, o.out]];
        const py = o.profileY && o.profileY.length >= 2 ? o.profileY : [[0, o.out], [o.h, o.out]];
        const interp = (pts, t) => {
          if (t <= pts[0][0]) return pts[0][1];
          for (let i = 0; i + 1 < pts.length; i++) {
            const [t0, v0] = pts[i], [t1, v1] = pts[i + 1];
            if (t <= t1) return t1 === t0 ? v1 : v0 + (v1 - v0) * (t - t0) / (t1 - t0);
          }
          return pts[pts.length - 1][1];
        };
        const depthAt = (x, y) => Math.min(interp(px, x), interp(py, y));
        // sample at every knot and every 5 mm, so a knee is a knee and a
        // straight run is straight
        const knots = (pts, len) => {
          const set = new Set([0, len]);
          for (const [t] of pts) if (t > 0 && t < len) set.add(t);
          for (let v = 5; v < len; v += 5) set.add(v);
          return [...set].sort((a, b) => a - b);
        };
        const xs = knots(px, o.w), ys = knots(py, o.h);
        const nx = xs.length, ny = ys.length;
        const pos = [], uvs = [], idx = [];
        for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
          pos.push(LX(o.x + xs[i], 0), LY(o.y + ys[j], 0), depthAt(xs[i], ys[j]));
          uvs.push(xs[i] / o.w, 1 - ys[j] / o.h);
        }
        for (let j = 0; j + 1 < ny; j++) for (let i = 0; i + 1 < nx; i++) {
          const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
          idx.push(a, c, b, b, c, d);
        }
        const front = new THREE.BufferGeometry();
        front.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        front.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
        front.setIndex(idx);
        front.computeVertexNormals();
        faceTex.side = THREE.DoubleSide;   // a mirrored face reverses the winding
        addTo(new THREE.Mesh(front, faceTex));
        // skirts: the perimeter dropped to the face, so the ends and the rails
        // are the slopes the profiles give them and not open edges
        const sp = [], si = [];
        const ring = [];
        for (let i = 0; i < nx; i++) ring.push([xs[i], ys[0]]);
        for (let j = 1; j < ny; j++) ring.push([xs[nx - 1], ys[j]]);
        for (let i = nx - 2; i >= 0; i--) ring.push([xs[i], ys[ny - 1]]);
        for (let j = ny - 2; j > 0; j--) ring.push([xs[0], ys[j]]);
        for (let k = 0; k < ring.length; k++) {
          const [x, y] = ring[k];
          sp.push(LX(o.x + x, 0), LY(o.y + y, 0), depthAt(x, y),
                  LX(o.x + x, 0), LY(o.y + y, 0), o.lift);
        }
        for (let k = 0; k < ring.length; k++) {
          const a = 2 * k, b = a + 1, c = 2 * ((k + 1) % ring.length), d = c + 1;
          si.push(a, b, c, b, d, c);
        }
        const skirt = new THREE.BufferGeometry();
        skirt.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
        skirt.setIndex(si);
        skirt.computeVertexNormals();
        addTo(new THREE.Mesh(skirt, new THREE.MeshLambertMaterial({color: o.color, side: THREE.DoubleSide})));
      } else if (o.rings && o.rings.length) {
        // THE SHAPE, NOT THE BOX. `shape: true` on the feature. The face art was
        // always the node's own; it was the SIDES that followed the bounding box,
        // so a contoured moulding read as a cardboard box with the right picture
        // on the front. Extruding the outline gives it the sides it has.
        const depth = o.out - o.lift;
        const shapes = o.rings.map(r => {
          const s = new THREE.Shape(
            r.shell.map(([x, y]) => new THREE.Vector2(LX(x, 0), LY(y, 0))));
          for (const h of r.holes)
            s.holes.push(new THREE.Path(
              h.map(([x, y]) => new THREE.Vector2(LX(x, 0), LY(y, 0)))));
          return s;
        });
        const geo = new THREE.ExtrudeGeometry(shapes, {depth, bevelEnabled: false});
        // ExtrudeGeometry's UVs are world-space; the face texture is rasterised
        // over the node's rect, so put world coordinates back into face mm and
        // then into that rect. Inverting LX/LY rather than assuming they are the
        // identity is what keeps a flipped face right - `left` and `bottom` are
        // drawn mirrored, and a texture that ignored that would read backwards.
        const unX = wx => (F.flipLX ? -wx : wx) + fw / 2;
        const unY = wy => fh / 2 - (F.flipLY ? -wy : wy);
        const pos = geo.attributes.position, uv = geo.attributes.uv;
        for (let i = 0; i < pos.count; i++) {
          uv.setXY(i, (unX(pos.getX(i)) - o.x) / o.w,
                   1 - (unY(pos.getY(i)) - o.y) / o.h);
        }
        uv.needsUpdate = true;
        const m = new THREE.Mesh(
          geo, [faceTex, new THREE.MeshLambertMaterial({color: o.color})]);
        m.position.set(0, 0, o.lift);
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
      const faceCrop = crop(f.lift ? artCv : cv, f, PX);
      // A MODULE IS ITS SHAPE, NOT ITS BOX. The R740xd's riser 2 is two
      // full-height slots over one low-profile slot - an L - and its box
      // takes in the top-left corner of a power supply; riser 1's brackets
      // reach two millimetres past its plate into the iDRAC jack. Cropping
      // the box moved that corner and that jack-top onto the ejecting riser
      // and left a hole in the panel where they had been. So the crop is
      // masked by the module's own art, exactly as a cavity's punch is: what
      // the module paints comes with it, and what it does not stays.
      const mask = await rasterize(f.svgText, f.w, f.h, PX);
      const mctx = faceCrop.getContext('2d');
      mctx.globalCompositeOperation = 'destination-in';
      mctx.drawImage(mask, 0, 0, faceCrop.width, faceCrop.height);
      mctx.globalCompositeOperation = 'source-over';
      const zf = f.lift || 0;
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(f.w, f.h),
        new THREE.MeshBasicMaterial({map: canvasTex(faceCrop), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      plane.position.set(LX(f.x, f.w), LY(f.y, f.h), zf + 0.3);
      fg.add(plane);
      // A FIELD OR A STATE WRITTEN ON A MODULE REPAINTS ITS PLANE. The crop above
      // is a one-time cut of the face canvas, so a wattage written on a supply
      // after the build changed the face texture and left the supply's own
      // plane reading the old badge. Re-cut from the module's own art, restyled,
      // with the cavities that fall in its rect punched from it again - the
      // C14 inlet's pins live behind one. Taken before the module's own shape
      // punch is recorded below, which is the face's hole and not this plane's.
      const punchesHere = facePunch[F.view].filter(p =>
        p.x < f.x + f.w && p.x + p.w > f.x && p.y < f.y + f.h && p.y + p.h > f.y);
      reg(f.svgText, async text => {
        const c2 = await rasterize(text, f.w, f.h, PX);
        const x2 = c2.getContext('2d');
        for (const p of punchesHere) {
          x2.globalCompositeOperation = 'destination-out';
          x2.drawImage(await rasterize(p.svg, p.w, p.h, PX),
                       Math.round((p.x - f.x) * PX), Math.round((p.y - f.y) * PX));
          x2.globalCompositeOperation = 'source-over';
        }
        remap(plane.material, c2);
      });
      // CLEAR, never fill: an opaque patch on the chassis face would occlude
      // everything behind it (the module's own cavities, pins, bay interior)
      // and the same shape comes out of the face, not the rectangle
      const pctx = cv.getContext('2d');
      pctx.globalCompositeOperation = 'destination-out';
      pctx.drawImage(mask, Math.round(f.x * PX), Math.round(f.y * PX));
      pctx.globalCompositeOperation = 'source-over';
      facePunch[F.view].push({kind: 'shape', svg: f.svgText, x: f.x, y: f.y, w: f.w, h: f.h});
      const meta = FRU_META[f.path];
      if (meta.body && meta.body.boxes) {
        // THE BODY IN PIECES, each a plain box in the FRU's group so the
        // riser's PCB and connectors come out with its plate. Side art is
        // for the one-box form; a PCB is a colour.
        for (const b of bodyBoxes(meta.body, f.w, f.h)) {
          const r = localToFace(f.toFace, b);
          const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, r.h, b.z1 - b.z0),
            new THREE.MeshLambertMaterial({color: b.color}));
          m.position.set(LX(r.x, r.w), LY(r.y, r.h),
                         zf - b.z0 - (b.z1 - b.z0) / 2 - 0.05);
          fg.add(m);
        }
      } else if (meta.body) {   // full module body travels with the FRU
        const {mesh, fp, d} = await bodyBoxMesh(meta.body, f.w, f.h);
        mesh.position.set(LX(f.x + fp.at[0], fp.size[0]),
                          LY(f.y + fp.at[1], fp.size[1]), zf - d / 2 - 0.05);
        fg.add(mesh);
      }
      // empty bay: interior surfaces only, so it never occludes the module's
      // own cavities (the C14 inlet pins live inside this volume)
      // the bay is as deep as the thing that goes in it, not 60 mm
      const bd = meta.body ? meta.body.depth : (meta.bodyDepth || 60);
      if (f.shelf) continue;   // a shelf, not a hole: nothing is left behind
      // a body in pieces is a riser, and behind an unseated riser is the
      // chassis interior, not a hole: nothing is left behind here either
      if (meta.body && meta.body.boxes) continue;
      const bay = new THREE.Mesh(new THREE.BoxGeometry(f.w + 0.6, f.h + 0.6, bd),
        new THREE.MeshLambertMaterial({color: 0x0a0c0e, side: THREE.BackSide}));
      bay.position.set(LX(f.x, f.w), LY(f.y, f.h), zf - bd / 2 - 0.2);
      // THE HOLE BELONGS TO THE BAY, NOT THE MODULE. Tagged with the bay's
      // path so it stays when the module is unseated - that is the point of
      // it - and goes when the bay itself does: the mid tray's four bays are
      // pulled with the tray, and four dark boxes were left hanging where it
      // had been, hiding the board.
      bay.userData.portrayalPath = f.path;
      grp.add(bay);
    }
    for (const s of subBodies) {
      const body = BODY_META[s.ref];
      if (!body || !body.boxes) continue;
      const into = fruGroups[s.owner] || grp;
      for (const b of bodyBoxes(body, 0, 0)) {
        const r = localToFace(s.toFace, b);
        const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, r.h, b.z1 - b.z0),
          new THREE.MeshLambertMaterial({color: b.color}));
        m.position.set(LX(r.x, r.w), LY(r.y, r.h),
                       (s.lift || 0) - b.z0 - (b.z1 - b.z0) / 2 - 0.05);
        m.userData.portrayalPath = s.path;
        into.add(m);
      }
    }
  meshes.push(grp);
}
