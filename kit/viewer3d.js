// The Portrayal 3D device viewer, as something you can mount in a div.
//
// This is `demo/3d.html`'s scene with the page taken away. The v2 Explorer swaps
// its stage between an SVG and this canvas inside one document, which a page
// could not do, so the scene had to stop being a page. Everything that used to
// live above the canvas - the config dropdown, the FRU eject buttons, the GLB
// and USDZ buttons, the capability HUD - stays with the host. This module
// renders and reports; the numbers and lists the host needs to rebuild that
// chrome come back through the viewer object.
//
// The bodies below are deliberately the same code that has been running in the
// device viewer, reparented from module scope into a per-viewer closure. The
// tuning in here is not obvious from reading it - depth range, pixel-ratio cap,
// face tint, alphaTest, the LOD budget - and its failure mode is a regression
// visible only at one camera angle, so the extraction was checked pixel for
// pixel against the frozen page at ten poses rather than reasoned about.
//
// Per-viewer state is also what makes dispose() possible, and dispose() is what
// stops a page that toggles between 2D and 3D from stacking up WebGL contexts:
// browsers keep about sixteen alive and drop the oldest without warning.
//
// The host page must supply an import map for `three` and `three/addons/`.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { toGLB, toUSDZ } from './share.js';
import { configureRelief, createReliefScope, svgCanvas, canvasTex, rasterize, svgSource, setSvgOverride, clearSvgOverrides,
         setNodeStates, nodeStates, setNodeFields, restyleText,
         setNodeLampColors, nodeLampColors, LAMP_HEX,
         setPulled as setReliefPulled, pulledPaths,
         buildFaceRelief, bodyBoxes, fruFor,
         nodeTools, tiltOf, tiltTools, tiltGroupIn, unproject, openFrameFaces } from './relief.js';
import { seatViews, seatBack, refusalReason } from './swap.js';
import { jdist, faceFile } from './dist.js';
import { createLamps } from './lamps.js';

const CLS_LABEL = {fan: 'Fan module', psu: 'Power supply', tab: 'Info tab'};
// box-face shading, in +x -x +y -y +z -z order: sides darker, lid lifted,
// underside in shadow. Multiplies the face texture on an unlit material.
const FACE_TINT = [0.65, 0.65, 1.25, 0.45, 1, 1];

// relief.js is configured once, globally, with the renderer and the FRU set it
// should tag owners against. Two viewers building at the same time would hand it
// two different renderers mid-await, so builds take a turn - across instances,
// not just within one.
let buildLock = Promise.resolve();
const serialise = fn => (buildLock = buildLock.then(fn, fn)); // a failed build must not jam the queue

// Free everything a subtree owns. three disposes nothing on remove(): a config
// switch that drops a 40MB set of face textures without this just leaks them.
function disposeTree(root) {
  root.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    for (const m of [].concat(o.material || [])) {
      if (!m) continue;
      for (const k of ['map', 'alphaMap', 'lightMap']) m[k] && m[k].dispose();
      m.dispose();
    }
  });
}

const save = (data, filename, type) => {
  const url = URL.createObjectURL(new Blob([data], {type}));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);   // Safari is still reading it
};

/**
 * Mount a viewer into `container`.
 *
 * @param opts.dist       where the compiled SVGs and indexes live ('../dist/')
 * @param opts.pxmm       base face raster density (4)
 * @param opts.background scene background
 * @param opts.highlight  selection colour
 */
export function createViewer(container, opts = {}) {
  const DIST = opts.dist || '../dist/';
  const PXMM = opts.pxmm || 4;
  const HL_COLOR = opts.highlight || '#f59e0b';
  // how a mark is drawn when it does not say (#664): 'plate', the selection's
  // translucent plate and outline, or 'ring', 2D marks.js's pair of rings
  const MARK_STYLE = opts.markStyle === 'ring' ? 'ring' : 'plate';

  let DEV = null, CFG = null, disposed = false;
  // Runtime bay swaps, bay id -> ref (or null for an emptied bay). The 3D scene
  // is extracted from the COMPILED face files, which know only what the built
  // configuration says, so without these a swap made in the 2D inspector is
  // invisible here - on every device, in both directions.
  let OVERRIDES = {}, COMP_INDEX = null;
  // Runtime lamp/element states, data-path -> the state classes the page has on
  // that element. Same story as the swaps above and for the same reason: the
  // scene is rasterised from the compiled files, which carry the RULES for every
  // state a part declares and have never carried one APPLIED. Held here so a
  // rebuild - a config change, a swap - repaints the states that were set rather
  // than quietly reverting the device to all-dark.
  let STATES = {};
  // WHAT THE HOST HAS TAKEN OFF, by data-path. Same story as STATES above and for
  // the same reason: the scene is rasterised from the compiled faces, which know
  // what the device HAS and have never known what a viewer has removed from it.
  // Held here so a rebuild - a config change, a swap, turning the chassis around -
  // does not quietly bolt every cover back on.
  let PULLED = new Set();
  // How to redraw each texture that came from a node's own art, collected during
  // the build. Emptied on every rebuild: the materials it points at are disposed.
  let RESTYLE = [];
  let FIELDS = {};   // path -> {key: value}, what the host has written on parts
  let COMP = null, COMP_ENTRY = null;     // lone-component mode, as ?component= gave
  let W = 438.4, H = 43.5, D = 515;
  // animated FRUs: paths discovered per build, groups tweened along their face normal
  const FRU_PATHS = new Set(), FRU_GROUPS = {}, FRU_META = {}, TWEENS = [];
  let BODY_META = {};
  let devIndex = null;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(opts.background ?? 0x16181b);
  // near/far set the depth-buffer resolution: at 600mm a near of 0.1 resolves only
  // ~0.21mm, so anything sitting a few hundredths of a mm off a face z-fights.
  // near 5 / far 3000 resolves ~0.004mm, comfortably finer than any relief offset.
  const camera = new THREE.PerspectiveCamera(40, 1, 5, 3000);
  camera.position.set(420, 260, 620);
  const renderer = new THREE.WebGLRenderer({antialias: true});
  const caps = (() => {
    const gl = renderer.getContext();
    const w2 = renderer.capabilities.isWebGL2;
    const aniso = renderer.capabilities.getMaxAnisotropy();
    const samples = gl.getParameter(gl.SAMPLES);
    // WebGL1 means NPOT textures cannot be mipmapped, and msaa 0 means antialias:true
    // was not honoured - either one produces shimmer that no material setting fixes
    return {webgl2: w2, aniso, samples, warn: !w2 || samples === 0 || aniso < 4,
            text: `WebGL${w2 ? 2 : 1} · aniso ${aniso} · msaa ${samples}`};
  })();
  // cap the pixel ratio: at DPR 2+ an integrated laptop GPU allocates 4x the
  // fragments and drivers commonly reduce or silently drop MSAA, which shows up
  // as aliased silhouette edges - worst where two edges converge, i.e. corners -
  // while textured face interiors still look clean because they are anisotropic
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.domElement.style.display = 'block';
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  // keep the camera outside the near plane so raising near cannot clip geometry
  // Closest a selection is ever framed from: a hand's length, the distance a
  // person holds a chassis at to read a port label. Not a collision limit -
  // controls.minDistance below is that, and letting it double as a framing floor
  // is what put the eye 60 mm from an 18.5 mm cage.
  const INSPECT_MM = 230;
  controls.minDistance = 40;
  controls.maxDistance = 2500;
  // lights shade only the relief geometry (Lambert); face textures stay unlit art
  scene.add(new THREE.AmbientLight(0xffffff, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(0.4, 1, 0.7);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.9);
  fill.position.set(-0.5, -0.3, -1);
  scene.add(fill);

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (w < 1 || h < 1) return;          // hidden stage: leave the last good size
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  resize();
  // the host is told to call resize(), but a stage that is shown, hidden and
  // shown again is exactly the case a host forgets; observing costs nothing and
  // the observer is disconnected in dispose()
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  // --- events -----------------------------------------------------------------
  const listeners = {select: [], hover: [], lod: []};
  function on(event, fn) {
    (listeners[event] || (listeners[event] = [])).push(fn);
    return () => { const a = listeners[event]; const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); };
  }
  function emit(event, ...args) {
    for (const fn of (listeners[event] || []).slice()) {
      try { fn(...args); } catch (e) { console.warn('[portrayal] viewer3d listener', event, e); }
    }
  }

  // --- FRU animation ----------------------------------------------------------
  function stepTweens(now) {
    for (let i = TWEENS.length - 1; i >= 0; i--) {
      const t = TWEENS[i];
      const k = Math.min(1, (now - t.t0) / t.dur);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;   // ease in-out
      t.g.position.z = t.from + (t.to - t.from) * e;
      if (k >= 1) TWEENS.splice(i, 1);
    }
  }

  function fruState(path) {
    const meta = FRU_META[path], g = FRU_GROUPS[path];
    if (!meta || !g) return null;
    const out = g.position.z > meta.pull / 2;
    const [outIcon, inIcon] = meta.captive ? ['⤒', '⤓'] : ['⏏', '⏎'];
    return {path, cls: meta.cls, view: meta.view, label: CLS_LABEL[meta.cls] || meta.cls,
            captive: meta.captive, travel: meta.pull, out, icon: out ? inIcon : outIcon};
  }

  // Every FRU, not just one per class - the page could only fit three buttons,
  // a host with a tree can address all eight.
  function frus() {
    const order = ['fan', 'psu', 'tab'];
    return Object.keys(FRU_META)
      .sort((a, b) => (order.indexOf(FRU_META[a].cls) - order.indexOf(FRU_META[b].cls)) ||
                      a.localeCompare(b))
      .map(fruState).filter(Boolean);
  }

  function toggleFru(path) {
    const g = FRU_GROUPS[path], meta = FRU_META[path];
    if (!g || !meta) return null;
    const out = meta.pull;
    const target = g.position.z > out / 2 ? 0 : out;
    TWEENS.push({g, from: g.position.z, to: target, t0: performance.now(), dur: 900});
    const verb = meta.captive ? (target ? 'extending' : 'retracting')
                              : (target ? 'removing' : 'inserting');
    const st = fruState(path);
    // the eased tween has not run yet, so report where it is going
    st.out = !!target;
    const [outIcon, inIcon] = meta.captive ? ['⤒', '⤓'] : ['⏏', '⏎'];
    st.icon = target ? inIcon : outIcon;
    st.verb = verb;
    st.text = `${path} — ${verb} (${Math.round(out)}mm travel${meta.captive ? ', captive' : ''})`;
    return st;
  }

  // --- adaptive face resolution -----------------------------------------------
  // Face art is baked into a canvas at PXMM, which puts a 1.5mm port label at ~6px:
  // legible from a metre, mush from 100mm. Rasterising every face at the sharpest
  // useful density is not an option - all six at ~28px/mm is roughly 380MB - so
  // instead measure how many screen pixels each face actually covers and re-raster
  // only the one being looked at. Faces turned away fall back to base density, so
  // the high-resolution canvas exists for at most a face or two at a time.
  //
  // This keeps the SVG as the single source of truth: refinement runs the exact
  // same rasteriser at a higher density, so 3D text can never drift from 2D text.
  const LOD_STEPS = [PXMM, 8, 16, 32];
  const MAX_FACE_TEXELS = 16e6;     // ~64MB RGBA: a 440x44mm faceplate reaches 16px/mm,
                                    // and a 440x548mm top/bottom still reaches 8 - enough
                                    // for the compliance and serial labels down there
  const MAX_TOTAL_TEXELS = 40e6;    // a 3/4 view lights up three faces at once
  const LOD = [];
  // blinking and alternating lamps: frames per keyframe block, swapped per tick
  const LAMPS = createLamps();
  let lodPaused = 0, lodSummary = '';

  const texelsAt = (rec, px) => rec.wmm * rec.hmm * px * px;
  function lodClamp(rec, want) {
    const maxDim = renderer.capabilities.maxTextureSize || 4096;
    // what everything else is already holding, so one face cannot blow the budget
    const others = LOD.reduce((n, r) => n + (r === rec ? 0 : texelsAt(r, r.level)), 0);
    while (want > PXMM && (Math.max(rec.wmm, rec.hmm) * want > maxDim ||
                           texelsAt(rec, want) > MAX_FACE_TEXELS ||
                           others + texelsAt(rec, want) > MAX_TOTAL_TEXELS)) {
      want = LOD_STEPS[LOD_STEPS.indexOf(want) - 1];
    }
    return want;
  }

  // screen pixels per mm across this face, at the drawing-buffer resolution that
  // actually gets sampled (not CSS pixels - a DPR-2 display samples twice as finely)
  const _v = () => new THREE.Vector3();
  function faceDensity(rec) {
    const bw = renderer.domElement.width, bh = renderer.domElement.height;
    const o = _v().applyMatrix4(rec.frame);
    const n = _v().set(0, 0, 1).transformDirection(rec.frame);
    if (n.dot(_v().copy(camera.position).sub(o).normalize()) <= 0.05) return 0;  // turned away
    const scr = v => { const p = v.project(camera); return [p.x * 0.5 * bw, p.y * 0.5 * bh]; };
    const [ox, oy] = scr(_v().applyMatrix4(rec.frame));
    const [ax, ay] = scr(_v().set(1, 0, 0).applyMatrix4(rec.frame));
    const [bx, by] = scr(_v().set(0, 1, 0).applyMatrix4(rec.frame));
    return Math.max(Math.hypot(ax - ox, ay - oy), Math.hypot(bx - ox, by - oy));
  }

  // Punch masks repeat heavily - a 54-port faceplate uses a handful of distinct
  // cavity shapes - so memoise per (shape, density) and reuse across placements.
  const _punchCache = new Map();
  async function punchMask(svg, wmm, hmm, pxmm) {
    const key = `${pxmm}|${wmm}x${hmm}|${svg}`;
    if (!_punchCache.has(key)) _punchCache.set(key, rasterize(svg, wmm, hmm, pxmm));
    return _punchCache.get(key);
  }

  // `rev` counts changes to rec.svgText and `painted` says which one the texture
  // shows. A state change used to zero rec.level and call this, and if the face
  // was mid-refine for the camera it returned at once - the refine in flight had
  // captured the OLD text, painted it, and left the lamp dark until the next
  // zoom. Now a refine re-runs while the text moved under it.
  async function refineFace(rec, pxmm) {
    if (rec.busy || !box) return;
    if (rec.level === pxmm && rec.painted === rec.rev) return;
    rec.busy = true;
    try { do {
      const rev = rec.rev;
      const cv = await rasterize(rec.svgText, rec.wmm, rec.hmm, pxmm, rec.flipX, rec.flipY);
      // The build punches apertures out of the face after rasterising it; a fresh
      // raster is opaque again, which would seal every cavity behind a flat wall.
      const ctx = cv.getContext('2d');
      const R = v => Math.round(v * pxmm);
      for (const p of rec.punches) {
        if (p.kind === 'rect') { ctx.clearRect(R(p.x), R(p.y), R(p.w), R(p.h)); continue; }
        ctx.globalCompositeOperation = 'destination-out';
        ctx.drawImage(await punchMask(p.svg, p.w, p.h, pxmm), R(p.x), R(p.y));
        ctx.globalCompositeOperation = 'source-over';
      }
      if (rec.gen !== gen) return;      // a rebuild landed while this was rasterising
      const mat = (Array.isArray(box.material) ? box.material : [box.material])[rec.matIndex];
      if (!mat) return;
      const old = mat.map;
      const tex = canvasTex(cv);
      // the component-plate path retargets the face texture onto a trimmed plate
      if (old) { tex.repeat.copy(old.repeat); tex.offset.copy(old.offset); }
      mat.map = tex;
      mat.needsUpdate = true;
      if (old) old.dispose();
      rec.level = pxmm;
      rec.painted = rev;
    } while (rec.painted !== rec.rev); } catch (e) {
      console.warn('[portrayal] face refine failed', rec.key, e);
    } finally { rec.busy = false; }
  }

  function updateFaceLOD() {
    if (!box || performance.now() < lodPaused) return;
    for (const rec of LOD) {
      const need = faceDensity(rec);
      let want = LOD_STEPS.find(s => s >= need) || LOD_STEPS[LOD_STEPS.length - 1];
      want = lodClamp(rec, want);
      // hysteresis: drop a level only well below it, so nudging the camera around a
      // threshold cannot trigger a re-raster on every frame
      if (want < rec.level && need > rec.level / 2) continue;
      if (want !== rec.level) refineFace(rec, want);
    }
    const shown = LOD.filter(r => r.level > PXMM)
                     .map(r => `${r.key} ${r.level}px/mm`).join(' · ');
    if (shown !== lodSummary) { lodSummary = shown; emit('lod', shown); }
  }

  // Re-rasterising a face is main-thread work, so only do it once the camera has
  // settled - mid-orbit the extra sharpness is not perceptible anyway.
  let _lodCamKey = '', _lodSettledAt = 0, _lodRanAt = 0;
  function lodTick() {
    const now = performance.now();
    const k = camera.position.toArray().map(v => v.toFixed(1)).join(',');
    if (k !== _lodCamKey) { _lodCamKey = k; _lodSettledAt = now; return; }
    if (now - _lodSettledAt < 200 || now - _lodRanAt < 400) return;
    _lodRanAt = now;
    updateFaceLOD();
  }

  // --- build ------------------------------------------------------------------
  // THIS VIEWER'S OWN SWAPS AND LAMPS. Two viewers on one page - a before/after
  // of the same rack - each need their own; without this the second to build
  // took the first's occupants, and either one tearing down emptied both.
  // THREE, the renderer and the fetch cache are still shared, which is right.
  const SCOPE = createReliefScope();
  let box = null, reliefGroup = null, gen = 0;
  const faceGroups = {};        // view -> the group buildFaceRelief filled
  // view -> [w, h] of the face's DRAWING, which is not always the plane's. The
  // R740xd's front is the 482.6 mm rack face over a 434 mm body; relief is laid
  // out against the drawing (relief.js: "the drawing's own size wins"), so
  // anything that maps between the drawing and the face - a pick, a halo -
  // has to use the same number or it lands one ear off. Kept here rather
  // than inside load() because pick() and select() run long after it.
  const FACE_MM = {};
  // view -> [flipX, flipY]: whether the face's texture is the drawing mirrored.
  // Only the bottom is (its art is authored as seen from below), and relief
  // negates its local x/y to match - see LX/LY in relief.js. A pick has to
  // un-mirror and a halo has to mirror, or both land on the wrong side.
  const FACE_FLIP = {};
  const ALL_VIEWS = ['front', 'rear', 'right', 'left', 'top', 'bottom'];
  // BoxGeometry material index -> face; the order three.js builds them in
  const FACE_OF_INDEX = ['right', 'left', 'top', 'bottom', 'front', 'rear'];

  async function bodyBoxMesh(body, faceW, faceH) {
    const plain = () => new THREE.MeshLambertMaterial({color: body.color || '#3a3f44'});
    const sideMat = async (name, wmm, hmm, flipX, flipY) => {
      if (!body.sides || !body.sides[name]) return plain();
      const c = await svgCanvas(DIST + body.sides[name], wmm, hmm, flipX, flipY, SCOPE);
      return new THREE.MeshBasicMaterial({map: canvasTex(c)});
    };
    const fp = body.footprint || {at: [0, 0], size: [faceW, faceH]};
    const [bw, bh] = fp.size, d = body.depth;
    const mats = [
      await sideMat('right', d, bh),
      await sideMat('left', d, bh),
      await sideMat('top', bw, d),
      await sideMat('bottom', bw, d, true, true),
      new THREE.MeshBasicMaterial({visible: false}),   // face art plane covers this
      await sideMat('rear', bw, bh),
    ];
    return {mesh: new THREE.Mesh(new THREE.BoxGeometry(bw, bh, d), mats), fp, d};
  }

  // Rewrite the fetched faces to match the runtime swaps, BEFORE anything reads
  // them. Everything downstream - the FRU-path scan, every face texture, every
  // cavity, the hit index - goes through svgSource, so one substitution per face
  // reaches all of them.
  //
  // The overrides are cleared first ON PURPOSE: svgSource consults the override
  // map ahead of its cache, so reading a face here while a previous build's
  // override still stood would re-swap an already-swapped document.
  //
  // A CAGE SWAP IS SEATED HERE TOO, not only a bay swap. Before this, `swap.js`
  // could put an optic into a cage on the LIVE 2D DOM (shell.js) but this
  // module never called it, so a port's chosen occupant applied in 2D and
  // stayed whatever the configuration built in 3D - the same divergence a bay
  // swap had before `applyAllOverrides` existed, one seat lower.
  const byRef = ref => (COMP_INDEX || []).find(
    c => `${c.ns}/${c.name}@${c.major.slice(1)}` === String(ref).split(':')[0]);
  const loadSkin = async ref => {
    const c = byRef(ref);
    if (!c) return null;
    const skin = c.skins?.includes('default') ? 'default' : c.skins?.[0];
    const url = `${DIST}components/${c.ns}--${c.name}--${c.major}--${skin}.svg`;
    return {comp: c, text: await svgSource(url, SCOPE)};
  };
  async function applyBayOverrides(cfg) {
    clearSvgOverrides(SCOPE);
    if (COMP || !Object.keys(OVERRIDES).length) return 0;
    // EVERY FACE AT ONCE, through the one pass node can run (swap.js
    // `seatViews`): each face `viewsToRewrite` names, and every face with a
    // rear hole, goes through `seatFace` - the device's bays at every level
    // (applyAllOverrides), then every slot of the face as it now stands, the
    // cards' and the backs' included (#484, B3 Task 10a/10b), then the rear
    // holes of the bays the map swapped (applyRearOverrides). A key on the
    // back of a cassette nobody swapped reaches the rear face too; the old
    // rear pass here re-seated swapped bays only (B3 Task 10c).
    const roots = {};
    for (const view of ALL_VIEWS) {
      const url = `${DIST}${faceFile(devIndex, cfg, view)}`;
      let text;
      try { text = await svgSource(url, SCOPE); } catch { continue; }
      if (!text) continue;
      const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
      if (doc.querySelector('parsererror')) continue;
      roots[view] = doc.documentElement;
    }
    const seated = await seatViews(roots, {bays: devIndex.bays || {}, cages: devIndex.cages || {}},
                                   OVERRIDES, loadSkin, byRef);
    let total = 0;
    for (const [view, res] of Object.entries(seated)) {
      const {applied: viewApplied, dropped = [], refused = [], failed = [], cages: faceCages = []} = res;
      if (dropped.length)
        console.warn(`[portrayal] ${DEV}.${cfg}.${view}: ${dropped.length} nested `
                     + `bay override(s) never applied - the drawing nests deeper `
                     + `than the walk goes, so 2D and 3D will disagree`, dropped);
      // A REFUSED CAGE OVERRIDE is the cage counterpart of a dropped bay one -
      // `applyOccupantOverrides` will not half-seat an optic into a cage the
      // build does something to that the kit does not (see swap.js
      // `refusalReason`: mirrored, or in a group carrying states), so
      // it leaves the cage empty rather than guess with no real build to check
      // against. The cage shows nothing seated in 2D and 3D alike; only the
      // CHOSEN swap silently failed, and that is worth saying. A FAILED one is
      // a skin that did not load: the cage keeps what the build seated. A key
      // on a back that was rebuilt is reported here too (seatFace merges the
      // rear pass's).
      if (refused.length)
        console.warn(`[portrayal] ${DEV}.${cfg}.${view}: ${refused.length} cage `
                     + `override(s) refused - the kit does not seat an optic into `
                     + `a mirrored cage, or one whose group carries `
                     + `states, so the cage is left empty`,
                     refused.map(id => `${id} (${refusalReason(faceCages.find(c => c.id === id)) || 'rear'})`));
      if (failed.length)
        console.warn(`[portrayal] ${DEV}.${cfg}.${view}: ${failed.length} cage `
                     + `override(s) not applied - the optic's skin did not load, `
                     + `so the cage keeps what the build seated`, failed);
      if (!viewApplied) continue;
      // Keyed by the file, which other configurations may share. The
      // overrides are cleared at the top of every pass and a pass is one
      // configuration, so no other configuration reads this one's.
      setSvgOverride(`${DIST}${faceFile(devIndex, cfg, view)}`,
                     new XMLSerializer().serializeToString(roots[view].ownerDocument), SCOPE);
      total += viewApplied;
    }
    return total;
  }

  // THE BACK A MODULE HOLDS, for relief.js's back pass (B3 Task 10c). A
  // cassette's back in 3D is built from the module's own back drawing
  // (`body.sides.rear`), not from the rear face's flat projection, so a key
  // on a back (`bay-1/module/mtp1`) is seated into a copy of that drawing
  // (swap.js `seatBack`: at the slot's lift, its `out`s as published) and
  // relief builds the copy, one per bay - two cassettes of one kind share a
  // shipped drawing and not a choice. Every key under the bay counts,
  // whether or not the bay itself was swapped. With no key, or nothing
  // seated, the shipped drawing is built, as before.
  async function backSource(bay, moduleRef, url) {
    if (COMP || !Object.keys(OVERRIDES).some(k => k.startsWith(`${bay}/module/`))) return url;
    const text = await svgSource(url, SCOPE);
    const doc = text ? new DOMParser().parseFromString(text, 'image/svg+xml') : null;
    if (!doc || doc.querySelector('parsererror')) return url;
    const res = await seatBack(doc.documentElement, {bay, moduleRef}, OVERRIDES, loadSkin, byRef);
    const missed = [...res.refused, ...res.failed, ...res.dropped];
    if (missed.length)
      console.warn(`[portrayal] ${DEV}: the back of ${bay} did not take `
                   + `${missed.length} key(s) - a plug whose skin did not load keeps `
                   + `what the back shipped, and a key naming no slot of this back `
                   + `(or one a front part shadows) seats nothing`, missed);
    if (!res.applied) return url;
    const own = `${url}#${bay}`;
    setSvgOverride(own, new XMLSerializer().serializeToString(doc), SCOPE);
    return own;
  }

  async function build(cfg) {
    // THREE and the renderer are genuinely shared; the per-document state is not,
    // and rides on SCOPE rather than being claimed from under the other viewer.
    // That now includes the raster density and the FRU path set - until it did,
    // two viewers at different pxmm could rasterise each other's side faces.
    configureRelief({THREE, renderer, PXMM, FRU_PATHS}, SCOPE);
    await applyBayOverrides(cfg);
    // the states go in BEFORE anything is extracted, so the faces and the relief
    // are cut from a document that already carries them; a rebuild that dropped
    // them would put out every lamp the user had lit
    setNodeStates(STATES, SCOPE);
    // and what is off stays off, for the same reason and at the same moment: the
    // faces and the relief are both cut from a document that already knows
    setReliefPulled(PULLED, SCOPE);
    RESTYLE = [];
    gen++;
    const f = v => `${DIST}${faceFile(devIndex, cfg, v)}`;
    const meshes = [];
    FRU_PATHS.clear();
    for (const k of Object.keys(FRU_GROUPS)) delete FRU_GROUPS[k];
    for (const k of Object.keys(FRU_META)) delete FRU_META[k];
    TWEENS.length = 0;
    if (!COMP) {
      // FRU paths must be known during extraction (owner tagging)
      for (const view of ['front', 'rear']) {
        const txt = await svgSource(f(view), SCOPE);
        for (const m of txt.matchAll(/data-path="([^"\/]+)"[^>]*data-class="(psu|fan|tab)"/g))
          FRU_PATHS.add(m[1]);
        for (const m of txt.matchAll(/data-class="(psu|fan|tab)"[^>]*data-path="([^"\/]+)"/g))
          FRU_PATHS.add(m[2]);
        for (const m of txt.matchAll(/data-path="([^"]+)\/module"/g)) FRU_PATHS.add(m[1]);
      }
    }
    const faceCv = {};
    const faceSvg = {};   // source text per face, for adaptive re-rasterisation
    const facePunch = {}; // apertures cleared from each face, replayed on refinement
    // The size each face's DRAWING declares, which is not always the plane's.
    // A rack face with integral ears is wider than the body behind it.
    for (const k of Object.keys(FACE_MM)) delete FACE_MM[k];
    const faceMM = FACE_MM;
    lodPaused = performance.now() + 500;   // no refinement while the build is in flight
    _punchCache.clear();
    // Relief is built in LOCAL face coordinates (x right, y up, z out of the face,
    // face plane at z=0) and oriented by a per-face group transform. flipLY handles
    // views whose y axis runs opposite to the face's local up (top view).
    // `deep` is how far INTO the box this face looks, and it is a different number
    // per face - the depth on front and rear, the width on the sides, the height on
    // the top and the bottom. It used to be the depth everywhere.
    // A PART WITH NO DEPTH OF ITS OWN - no `body`, no `size.d`, as a face
    // component must not have one (a `d` on a fixed part is a pit) - is drawn
    // alone on a 2 mm plate (D above), and that plate is a placeholder, not a
    // wall its relief runs into. Handed as the depth relief may reach, it made
    // every cavity 0 deep (buildFaceRelief keeps a cavity `INTO - 2` short of
    // the far side), which puts a bore's textured floor 0.1 mm IN FRONT of
    // its own mouth: common/lc-duplex-shuttered-adapter@2 alone drew its open
    // bores over its shutters (the floor at +3.275, the doors at +2.725),
    // while every device holding it drew the doors (B3 Task 10c). Such a part
    // is not clamped; a part that declares a depth is, as before.
    const compDeep = () => (COMP_ENTRY.body || COMP_ENTRY.size?.d) ? D : Infinity;
    const FACES = COMP ? [
      {view: 'comp', url: DIST + COMP_ENTRY.files[cfg], sizeBox: true,
       fw: () => W, fh: () => H, deep: compDeep, pos: () => [0, 0, D / 2], rot: [0, 0, 0]},
    ] : [
      {view: 'front', fw: () => W, fh: () => H, deep: () => D, pos: () => [0, 0, D / 2], rot: [0, 0, 0]},
      {view: 'rear',  fw: () => W, fh: () => H, deep: () => D, pos: () => [0, 0, -D / 2], rot: [0, Math.PI, 0]},
      {view: 'right', fw: () => D, fh: () => H, deep: () => W, pos: () => [W / 2, 0, 0], rot: [0, Math.PI / 2, 0]},
      {view: 'left',  fw: () => D, fh: () => H, deep: () => W, pos: () => [-W / 2, 0, 0], rot: [0, -Math.PI / 2, 0]},
      {view: 'top',   fw: () => W, fh: () => D, deep: () => H, pos: () => [0, H / 2, 0], rot: [-Math.PI / 2, 0, 0]},
      // THE UNDERSIDE GETS A RELIEF PASS TOO NOW. It was the one face left flat, and
      // 70 components are placed on it - more than on the top. Its art is authored
      // mirrored in both axes, which is what flipLX/flipLY carry through.
      {view: 'bottom', fw: () => W, fh: () => D, deep: () => H, pos: () => [0, -H / 2, 0],
       rot: [Math.PI / 2, 0, 0], flipLX: true, flipLY: true},
    ];
    const built = {};
    for (const F of FACES) {
      const before = meshes.length;
      await buildFaceRelief(F, {src: F.url || f(F.view), faceCv, faceSvg, facePunch,
                                faceMM,
                                meshes, FRU_GROUPS, FRU_META, BODY_META, D, deep: F.deep(),
                                bodyBoxMesh, dist: DIST, backSource,
                                restyle: RESTYLE, scope: SCOPE});
      // a face with no drawing falls back to flat colour and contributes no group
      if (meshes.length > before) built[F.view] = meshes[meshes.length - 1];
      FACE_FLIP[F.view] = [!!F.flipLX, !!F.flipLY];
    }
    let mats;
    if (COMP) {
      const body = COMP_ENTRY.body || {};
      const plain = new THREE.MeshLambertMaterial({color: body.color || '#3a3f44'});
      const sideMat = async (name, wmm, hmm, flipX, flipY) => {
        if (!body.sides || !body.sides[name]) return plain;
        const c = await svgCanvas(DIST + body.sides[name], wmm, hmm, flipX, flipY, SCOPE);
        return new THREE.MeshBasicMaterial({map: canvasTex(c)});
      };
      mats = [
        await sideMat('right', D, H),               // +x: face end at image left -> front
        await sideMat('left', D, H),                // -x: authored face-at-image-right (photo convention)
        await sideMat('top', W, D),                 // +y: front at image bottom
        await sideMat('bottom', W, D, true, true),  // -y: device bottom convention
        new THREE.MeshBasicMaterial({map: canvasTex(faceCv.comp), transparent: true, alphaTest: 0.1, alphaToCoverage: true}),
        await sideMat('rear', W, H),                // -z: as seen from behind
      ];
    } else {
      // The underside used to be rasterised here because it got no relief pass. It
      // gets one now, so it comes from faceCv like every other face - and if its
      // drawing is missing, buildFaceRelief falls back to flat colour the same way
      // the others do rather than this branch having its own answer.
      mats = [faceCv.right, faceCv.left, faceCv.top, faceCv.bottom, faceCv.front, faceCv.rear]
        .map((c, i) => {
          const m = new THREE.MeshBasicMaterial(
            // alphaTest: punched pixels must not write depth, or they occlude interiors
            {map: canvasTex(c), transparent: true, alphaTest: 0.1,
             alphaToCoverage: true});
          // The faces are unlit, so with the faceplate outline gone nothing marks a
          // corner: front and side are the same flat grey and the box loses its
          // form. Tint each face instead - the lid catches light, the sides fall
          // away, the underside is in shadow. It reads as a box without putting a
          // black line where two faces meet.
          m.color.setScalar(FACE_TINT[i]);
          return m;
        });
    }
    // the old scene stayed up while the new one was rasterising; swap it now
    clearHighlight();
    if (box) {
      scene.remove(box); disposeTree(box);
      if (box.userData && box.userData.bodyBox) {
        scene.remove(box.userData.bodyBox); disposeTree(box.userData.bodyBox);
      }
    }
    LAMPS.clear();
    if (reliefGroup) { scene.remove(reliefGroup); disposeTree(reliefGroup); }
    for (const k of Object.keys(faceGroups)) delete faceGroups[k];
    Object.assign(faceGroups, built);
    const fp = COMP && COMP_ENTRY.body && COMP_ENTRY.body.footprint;
    const bx = COMP && COMP_ENTRY.body && COMP_ENTRY.body.boxes;
    if (bx && bx.length) {
      // A BODY IN PIECES: the face on a thin plate and each box behind it
      // where the part says it is - the riser alone shows its PCB and its
      // connectors standing off the plate, as it does in the chassis.
      const plain = () => new THREE.MeshLambertMaterial({color: COMP_ENTRY.body.color || '#3a3f44'});
      // `body.plate` TRIMS THE SLAB here as it does for a footprint. A PCIe
      // card's face is its bracket, which is not a rectangle: a full-face slab
      // showed its sides as L-shaped fins round the tip tab and the keyed
      // flange, where the drawing is transparent. The texture is cloned before
      // it is retargeted, so the full-face plane that paints the outline keeps
      // its own mapping.
      const pl = COMP_ENTRY.body.plate || {at: [0, 0], size: [W, H]};
      const plateMats = mats.map((m, i) => i === 4 ? m : plain());
      if (COMP_ENTRY.body.plate && mats[4] && mats[4].map) {
        const face = mats[4].clone();
        face.map = mats[4].map.clone();
        face.map.repeat.set(pl.size[0] / W, pl.size[1] / H);
        face.map.offset.set(pl.at[0] / W, 1 - (pl.at[1] + pl.size[1]) / H);
        face.map.needsUpdate = true;
        plateMats[4] = face;
      }
      box = new THREE.Mesh(new THREE.BoxGeometry(pl.size[0], pl.size[1], 1.2), plateMats);
      box.position.set(pl.at[0] + pl.size[0] / 2 - W / 2,
                       H / 2 - (pl.at[1] + pl.size[1] / 2), D / 2 - 0.6);
      const bodyBox = new THREE.Group();
      for (const b of bodyBoxes(COMP_ENTRY.body, W, H)) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(b.w, b.h, b.z1 - b.z0),
          new THREE.MeshLambertMaterial({color: b.color}));
        m.position.set(b.x + b.w / 2 - W / 2, H / 2 - (b.y + b.h / 2),
                       D / 2 - b.z0 - (b.z1 - b.z0) / 2);
        bodyBox.add(m);
      }
      scene.add(box);
      box.userData.bodyBox = bodyBox;
      scene.add(bodyBox);
    } else if (fp) {
      // thin faceplate carries the face (and its mounting tabs); the body box
      // sits behind it within the footprint
      const plateMats = mats.map((m, i) => i === 4 ? m :
        new THREE.MeshLambertMaterial({color: COMP_ENTRY.body.color || '#3a3f44'}));
      const pl = COMP_ENTRY.body.plate || {at: [0, 0], size: [W, H]};
      box = new THREE.Mesh(new THREE.BoxGeometry(pl.size[0], pl.size[1], 1.2), plateMats);
      box.position.set(pl.at[0] + pl.size[0] / 2 - W / 2,
                       H / 2 - (pl.at[1] + pl.size[1] / 2), D / 2 - 0.6);
      // face texture must stay full-face aligned on the trimmed plate
      const ftex = mats[4].map;
      ftex.repeat.set(pl.size[0] / W, pl.size[1] / H);
      ftex.offset.set(pl.at[0] / W, 1 - (pl.at[1] + pl.size[1]) / H);
      const bodyMats = mats.map((m, i) => i === 4 ?
        new THREE.MeshLambertMaterial({color: COMP_ENTRY.body.color || '#3a3f44'}) : m);
      const bodyBox = new THREE.Mesh(
        new THREE.BoxGeometry(fp.size[0], fp.size[1], D - 1.2), bodyMats);
      bodyBox.position.set(fp.at[0] + fp.size[0] / 2 - W / 2,
                           H / 2 - (fp.at[1] + fp.size[1] / 2), -0.6);
      scene.add(box);
      box.userData.bodyBox = bodyBox;
      scene.add(bodyBox);
    } else if (faceMM.front && faceMM.front[0] > W + 0.5) {
      // A RACK FACE IS WIDER THAN THE BODY IT BOLTS TO. Dell builds the mounting
      // flanges into the R740xd's faceplate and puts the VGA, the power button
      // and the health lamp in them, so the front drawing is 482.6 mm over a
      // 434 mm chassis - both numbers right, and lint and the grader accept the
      // pair. Textured onto a 434-wide box face the artwork squashed and the
      // ear's ports hung in mid-air off the end.
      // So the face gets a plate of its own width and the body box sits behind
      // it - the same construction the component branch above uses for
      // `body.plate` over `body.footprint`, which is the same shape at another
      // scale.
      // THE FOLD LINES ARE NOT GUESSED. The ear span is measured nowhere, and
      // splitting the 48.6 mm difference would be assuming the answer, so this
      // draws ONE plate the width of the drawing and lets the drawing paint its
      // own ears onto it. True whatever the split.
      const [fwmm, fhmm] = faceMM.front;
      // THE EAR IS ABOUT AN INCH THICK, and 2 mm was a placeholder. At 2 mm the
      // backs of the ear-mounted ports came out the other side: measured off an
      // export, a USB on the flange is 13.70 mm deep and the VGA 6.73, with
      // nothing behind either but the plate, because the body box stops at the
      // fold. 25.4 is the operator's figure for the real flange - they have the
      // machine - and it contains the deepest of those with room over.
      // It is NOT derived from the ports: a number chosen to just clear 13.70
      // would look right today and fail the next thing bolted into a flange.
      const PLATE = 25.4;
      // the same default the component branch uses; configs.json carries the
      // chassis box but not its colour
      const plain = new THREE.MeshLambertMaterial({color: '#3a3f44'});
      const plateMats = mats.map((m, i) => i === 4 ? m : plain);
      box = new THREE.Mesh(new THREE.BoxGeometry(fwmm, fhmm, PLATE), plateMats);
      box.position.set(0, 0, D / 2 - PLATE / 2);
      const bodyMats = mats.map((m, i) => i === 4 ? plain : m);
      const bodyBox = new THREE.Mesh(
        new THREE.BoxGeometry(W, H, D - PLATE), bodyMats);
      bodyBox.position.set(0, 0, -PLATE / 2);
      scene.add(box);
      box.userData.bodyBox = bodyBox;
      scene.add(bodyBox);
    } else {
      box = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), mats);
      scene.add(box);
    }
    // AN OPEN FRAME HAS AN INSIDE. Its empty slots are punched through front
    // and rear and build no pockets (relief.js cavityShell), so through one you
    // would look past the inside of a box whose faces are drawn only from
    // outside - the lid and the flanks would vanish too. A lining of the four
    // long faces, seen from inside only and open at both ends, is the chassis's
    // interior; what a slot shows beyond it is whatever is behind the rear. A
    // child of the box so it is disposed with it, and never a pick target.
    if (!COMP && openFrameFaces(faceSvg).length) {
      const lining = new THREE.MeshLambertMaterial({color: 0x1b1d20, side: THREE.BackSide});
      const none = new THREE.MeshBasicMaterial({visible: false});
      const liner = new THREE.Mesh(new THREE.BoxGeometry(W - 0.6, H - 0.6, D - 0.6),
        [lining, lining, lining, lining, none, none]);
      liner.position.copy(box.position).negate();
      liner.raycast = () => {};
      box.add(liner);
    }
    // register faces for adaptive refinement
    LOD.length = 0;
    lodSummary = '';
    const FRAME = (pos, rot) => new THREE.Matrix4().compose(
      new THREE.Vector3(...pos),
      new THREE.Quaternion().setFromEuler(new THREE.Euler(...rot)),
      new THREE.Vector3(1, 1, 1));
    const lodFaces = COMP
      ? [['comp', 4, W, H, [0, 0, D / 2], [0, 0, 0], false, false]]
      : [['right',  0, D, H, [W / 2, 0, 0],  [0, Math.PI / 2, 0],  false, false],
         ['left',   1, D, H, [-W / 2, 0, 0], [0, -Math.PI / 2, 0], false, false],
         ['top',    2, W, D, [0, H / 2, 0],  [-Math.PI / 2, 0, 0], false, false],
         ['bottom', 3, W, D, [0, -H / 2, 0], [Math.PI / 2, 0, 0],  true,  true],
         ['front',  4, W, H, [0, 0, D / 2],  [0, 0, 0],            false, false],
         ['rear',   5, W, H, [0, 0, -D / 2], [0, Math.PI, 0],      false, false]]
        // A REFINED FACE IS RASTERISED AT THE DRAWING'S SIZE, LIKE THE FIRST ONE.
        // The base texture comes from buildFaceRelief, which takes its width from
        // the drawing (482.6 on the R740xd's front); these records fed refineFace
        // the box's width instead (434). Zoom in on a port and the refined raster
        // painted the 482.6 mm drawing into a 434 mm canvas: everything slid 10%
        // left and the right ear - the last 48 mm - came back bare. Same mistake
        // as the pick and the halo, third place it was made.
        .map(([k, mi, wmm, hmm, ...rest]) => [k, mi, ...(faceMM[k] || [wmm, hmm]), ...rest]);
    for (const [k, matIndex, wmm, hmm, pos, rot, flipX, flipY] of lodFaces) {
      if (!faceSvg[k]) continue;   // face fell back to flat colour - nothing to sharpen
      LOD.push({key: k, matIndex, wmm, hmm, svgText: faceSvg[k], flipX, flipY,
                punches: facePunch[k] || [],
                frame: FRAME(pos, rot), level: PXMM, busy: false, gen, rev: 0, painted: 0});
    }
    reliefGroup = new THREE.Group();
    meshes.forEach(m => reliefGroup.add(m));
    scene.add(reliefGroup);
    await syncLamps(null);
  }

  // hit-testing: hidden inline SVGs give us component boxes in mm via getBBox/CTM
  // SIX FACES, NOT TWO. Indexing only the front and rear meant a part on the
  // top, bottom or either side could not be picked, located, highlighted or
  // framed in 3D at all - which made a merged tree pointless, since four of
  // its six sections would have done nothing when clicked.
  const hitIndex = Object.fromEntries(ALL_VIEWS.map(v => [v, []]));
  const pathIndex = Object.fromEntries(ALL_VIEWS.map(v => [v, []]));
  async function buildHitIndex(cfg) {
    for (const view of ALL_VIEWS) {
      hitIndex[view] = []; pathIndex[view] = [];
      const text = await svgSource(`${DIST}${faceFile(devIndex, cfg, view)}`, SCOPE);
      if (!text) continue;                 // a face the device does not draw
      const div = document.createElement('div');
      div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
      div.innerHTML = text;
      document.body.appendChild(div);
      const svg = div.querySelector('svg');
      if (!svg) { div.remove(); continue; }
      const inv = svg.getScreenCTM().inverse();
      // A PART ON A FACET carries its tilt (relief.js tiltTools), so the halo
      // can stand in the same frame its relief was built in
      let TT = null;
      const tiltAt = el => {
        const t = tiltOf(el);
        if (!t) return null;
        if (!TT) { const T = nodeTools(svg);
                   TT = tiltTools(svg, {mmRect: T.mmRect, liftOf: T.liftOf,
                                        ctmOf: n => inv.multiply(n.getScreenCTM())}); }
        const r = TT.tiltRec(t);
        return r ? r.tilt : null;
      };
      const rec = el => {
        const b = el.getBBox();
        const m = inv.multiply(el.getScreenCTM());
        const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
          .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
        const r = {path: el.dataset.path, cls: el.dataset.class || '',
                model: el.dataset.model || '', x0: Math.min(pts[0].x, pts[1].x), y0: Math.min(pts[0].y, pts[1].y),
                x1: Math.max(pts[0].x, pts[1].x), y1: Math.max(pts[0].y, pts[1].y)};
        const tilt = tiltAt(el);
        if (tilt) r.tilt = tilt;
        return r;
      };
      hitIndex[view] = [...svg.children]
        .filter(el => el.dataset && el.dataset.path && el.dataset.class !== 'region')
        .map(rec);
      // hover keeps the page's shallow index (top-level children only, smallest
      // box wins); select() needs every addressable path, because the host's tree
      // has rows for parts nested inside a module
      pathIndex[view] = [...svg.querySelectorAll('[data-path]')].map(rec);
      div.remove();
    }
  }

  // --- picking ----------------------------------------------------------------
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  const SIDE_NAMES = ['right', 'left', 'top', 'bottom'];
  function pick(ev) {
    if (!box) return null;
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set((ev.clientX - r.left) / r.width * 2 - 1,
              -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    // A rack face is two meshes - the plate carries the front, the body box
    // the other five - so both are asked and the nearer hit wins.
    const targets = [box, box.userData && box.userData.bodyBox].filter(Boolean);
    const hit = ray.intersectObjects(targets)[0];
    if (!hit) return null;
    if (COMP) return {view: hit.face.materialIndex === 4 ? 'comp' : SIDE_NAMES[hit.face.materialIndex], path: null};
    const view = FACE_OF_INDEX[hit.face.materialIndex];
    if (!view || !hitIndex[view] || !hitIndex[view].length) return {view, path: null};
    // uv runs 0..1 across the mesh that was hit, and for a rack face that
    // mesh is the plate at the drawing's width, not the body's. Scaling by W
    // put every hit 10% short of where the pointer was - nothing at the left
    // edge, a whole ear at the right.
    const [fw, fh] = FACE_MM[view] || [W, H];
    const [flipX, flipY] = FACE_FLIP[view] || [false, false];
    // uv is read off the TEXTURE, and a mirrored face's texture is the drawing
    // reversed - so undo the mirror to get back to drawing coordinates.
    let x = hit.uv.x * fw, y = (1 - hit.uv.y) * fh;
    if (flipX) x = fw - x;
    if (flipY) y = fh - y;
    // smallest containing box wins — the chassis faceplate contains every point
    const c = hitIndex[view]
      .filter(c => x >= c.x0 && x <= c.x1 && y >= c.y0 && y <= c.y1)
      .sort((a, b) => (a.x1 - a.x0) * (a.y1 - a.y0) - (b.x1 - b.x0) * (b.y1 - b.y0))[0];
    return c ? {view, path: c.path, cls: c.cls, model: c.model} : {view, path: null};
  }

  let hovered = null, hoverKey = '';
  function onPointerMove(ev) {
    const h = pick(ev);
    // fire on change only: a host that rebuilds a tree row per event cannot take
    // one per mousemove. Keyed on the face too, so sliding off the front onto the
    // lid still reports, even though both carry no path.
    const k = h ? `${h.view}/${h.path || ''}` : '';
    if (k === hoverKey) return;
    hoverKey = k;
    hovered = h ? h.path : null;
    emit('hover', hovered, h);
  }
  function onPointerLeave() {
    if (hoverKey === '') return;
    hoverKey = ''; hovered = null;
    emit('hover', null, null);
  }
  // a click is a pointerup that did not orbit: OrbitControls owns the drag
  let down = null;
  const onPointerDown = ev => { down = {x: ev.clientX, y: ev.clientY}; };
  function onPointerUp(ev) {
    if (!down || Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) { down = null; return; }
    down = null;
    const h = pick(ev);
    emit('select', h ? h.path : null, h);
  }
  const el = renderer.domElement;
  el.addEventListener('pointermove', onPointerMove);
  el.addEventListener('pointerleave', onPointerLeave);
  el.addEventListener('pointerdown', onPointerDown);
  el.addEventListener('pointerup', onPointerUp);

  // --- selection --------------------------------------------------------------
  let hl = null, selected = null;
  function clearHighlight() {
    if (!hl) return;
    hl.parent && hl.parent.remove(hl);
    disposeTree(hl);
    hl = null;
  }

  // exact path, else the nearest ancestor that is drawn: a tree row for
  // `psu-0/handle/latch` should still light up the module it belongs to
  function locate(path) {
    const parts = path.split('/');
    for (let n = parts.length; n > 0; n--) {
      const p = parts.slice(0, n).join('/');
      for (const view of ALL_VIEWS) {
        const c = pathIndex[view].find(e => e.path === p);
        if (c) return {view, c, exact: n === parts.length};
      }
    }
    return null;
  }

  // ONE HALO, TWO USERS (#664): the selection and every mark. A halo stands on
  // the part's face or facet, with its tilt and its flip, inside the FRU group
  // that owns it so it rides a pulled module out, drawn last with the depth test
  // off - only its colour differs. Built here once so the two cannot drift.
  // Returns {obj, grp, lx, ly, w, h, exact} with `obj` already in the scene, or
  // null for a path no face draws.
  // THE RING STYLE, 2D marks.js's halo() in 3D: a soft wide ring under a
  // crisp narrow one, each a rounded rectangle band around the part at the
  // same outsets, widths and opacities in the same millimetres (ring(): pad,
  // stroke width, stroke opacity, corner radius min(0.9, pad)). A band is the
  // stroke drawn as a surface: the rounded rectangle at pad + width/2 with the
  // one at pad - width/2 cut out of it, so it is exactly the 2D stroke.
  const RINGS = [{pad: 1.35, width: 1.8, opacity: 0.28, order: 999},
                 {pad: 0.45, width: 0.7, opacity: 1, order: 1000}];
  function roundedRect(target, w, h, r) {
    const x = -w / 2, y = -h / 2, rr = Math.max(0, Math.min(r, w / 2, h / 2));
    target.moveTo(x + rr, y);
    target.lineTo(x + w - rr, y);
    target.absarc(x + w - rr, y + rr, rr, -Math.PI / 2, 0, false);
    target.lineTo(x + w, y + h - rr);
    target.absarc(x + w - rr, y + h - rr, rr, 0, Math.PI / 2, false);
    target.lineTo(x + rr, y + h);
    target.absarc(x + rr, y + h - rr, rr, Math.PI / 2, Math.PI, false);
    target.lineTo(x, y + rr);
    target.absarc(x + rr, y + rr, rr, Math.PI, Math.PI * 1.5, false);
    return target;
  }
  function ringBand(w, h, {pad, width, opacity, order}, colour) {
    const corner = Math.min(0.9, pad);
    const outer = pad + width / 2, inner = Math.max(pad - width / 2, 0);
    const shape = roundedRect(new THREE.Shape(), w + 2 * outer, h + 2 * outer, corner + width / 2);
    shape.holes.push(roundedRect(new THREE.Path(), w + 2 * inner, h + 2 * inner,
                                 Math.max(corner - width / 2, 0)));
    const mesh = new THREE.Mesh(new THREE.ShapeGeometry(shape, 6),
      // transparent at any opacity: three.js draws every opaque mesh before
      // every transparent one whatever its renderOrder, so an opaque crisp ring
      // was drawn first and the soft ring painted over its edge. One pass, and
      // renderOrder puts the crisp band on top.
      new THREE.MeshBasicMaterial({color: colour, transparent: true, opacity,
                                   depthTest: false, depthWrite: false, side: THREE.DoubleSide}));
    mesh.renderOrder = order;
    return mesh;
  }

  function halo(path, colour, style = 'plate') {
    const found = locate(path);
    if (!found) return null;
    const {view, c, exact} = found;
    const grp = faceGroups[view];
    if (!grp) return null;
    const w = Math.max(c.x1 - c.x0, 0.4), h = Math.max(c.y1 - c.y0, 0.4);
    // Local x=0 is the centre of the face the relief was built on, which for a
    // rack face is the 482.6 mm plate. Centring on the 434 mm body put the
    // halo 24.3 mm to the right of everything on the front - one ear.
    const [fw, fh] = FACE_MM[view] || [W, H];
    const [flipX, flipY] = FACE_FLIP[view] || [false, false];
    // the same LX/LY relief.js places a part with, mirror and all
    const lx = (flipX ? -1 : 1) * (c.x0 + w / 2 - fw / 2);
    const ly = (flipY ? -1 : 1) * (fh / 2 - (c.y0 + h / 2));
    // A PART ON A FACET: the halo takes the part's true box and stands in its
    // tilt frame - inside the owning FRU's group when that is tilted already,
    // so it rides the optic out. The frame below keeps the front-view centre.
    const owner = FRU_GROUPS[fruFor(path, k => Object.prototype.hasOwnProperty.call(FRU_GROUPS, k))];
    let into = owner || grp, hw = w, hh = h, hx = lx, hy = ly;
    if (c.tilt) {
      const u = unproject({x: c.x0, y: c.y0, w, h}, c.tilt);
      hw = u.w; hh = u.h;
      hx = (flipX ? -1 : 1) * (u.x + u.w / 2 - fw / 2);
      hy = (flipY ? -1 : 1) * (fh / 2 - (u.y + u.h / 2));
      into = tiltGroupIn(into, c.tilt, {fw, fh, flipLX: flipX, flipLY: flipY});
    }
    const obj = new THREE.Group();
    // what this is, for a host or a harness counting halos without guessing
    // from a material
    obj.userData.portrayalHalo = {path, colour, style};
    // depthTest off, drawn last: the same argument hl.js makes in 2D - a halo that
    // neighbours can paint over is not a halo. Here the neighbour is a handle or a
    // cage standing proud of the face.
    if (style === 'ring') {
      for (const r of RINGS) obj.add(ringBand(hw, hh, r, colour));
    } else {
      const geo = new THREE.PlaneGeometry(hw, hh);
      const fillMat = new THREE.MeshBasicMaterial({color: colour, transparent: true,
        opacity: 0.18, depthTest: false, depthWrite: false});
      const lineMat = new THREE.LineBasicMaterial({color: colour, depthTest: false,
        transparent: true});
      obj.add(new THREE.Mesh(geo, fillMat));
      obj.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), lineMat));
      obj.traverse(o2 => { o2.renderOrder = 999; });
    }
    obj.position.set(hx, hy, 0.8);
    // ride with the module if it is a FRU, so ejecting it does not leave the
    // marker behind on the chassis
    // (the longest prefix that is one - a card's optic is a FRU inside its card)
    into.add(obj);
    return {obj, grp, lx, ly, w, h, exact};
  }

  function select(path, o = {}) {
    clearHighlight();
    selected = path || null;
    if (!path) return false;
    const got = halo(path, HL_COLOR);
    if (!got) return false;
    hl = got.obj;
    if (o.frame !== false) frameOn(got.grp, got.lx, got.ly, got.w, got.h);
    return true;
  }

  // MARKS (#664): many halos at once, each in its own colour, independent of
  // the selection - a reader selects one part while five others stay marked.
  // `list` is the whole truth, [{path, color, style?}], and [] clears. `style`
  // is 'plate' (the selection's look) or 'ring' (2D's pair of rings); a mark
  // that does not say takes the viewer's `markStyle`, 'plate' by default. Paths, never
  // selectors (the host resolves those against its 2D drawing). A mark never
  // moves the camera and never touches `selected`. It is held here and drawn
  // again after every rebuild, as STATES and PULLED are, and a pulled module's
  // marks ride out in its FRU group like the selection halo.
  // Returns what could not be drawn so the host can say "not in 3D":
  //   missing  - no face draws the path, or any ancestor of it
  //   nearest  - drawn on the nearest ancestor that is (the rule select() uses)
  //   invalid  - the colour is not a hex (it lands in a material, never a string)
  let MARKS = [], markObjs = [], markReport = {missing: [], nearest: [], invalid: []};
  function clearMarkObjs() {
    for (const o of markObjs) { o.parent && o.parent.remove(o); disposeTree(o); }
    markObjs = [];
  }
  function drawMarks() {
    clearMarkObjs();
    const r = {missing: [], nearest: [], invalid: []};
    for (const m of MARKS) {
      if (!LAMP_HEX.test(m.color)) { r.invalid.push(m.path); continue; }
      const got = box ? halo(m.path, m.color, m.style) : null;
      if (!got) { r.missing.push(m.path); continue; }
      if (!got.exact) r.nearest.push(m.path);
      markObjs.push(got.obj);
    }
    markReport = r;
    // ON EVERY DRAW, a clean report included: a host that marked before the
    // first load finished was told every path was missing, and when the load
    // then drew them all, an event sent only on trouble never said so - its
    // "not in 3D" note stayed up over parts that were shown
    emit('marks', r);
    return r;
  }
  function setMarks(list) {
    MARKS = (Array.isArray(list) ? list : [])
      .filter(m => m && m.path)
      .map(m => ({path: String(m.path), color: String(m.color || ''),
                  style: m.style === 'ring' || m.style === 'plate' ? m.style : MARK_STYLE}));
    return drawMarks();
  }

  function frameOn(grp, lx, ly, w, h) {
    grp.updateMatrixWorld(true);
    const centre = new THREE.Vector3(lx, ly, 0).applyMatrix4(grp.matrixWorld);
    const normal = new THREE.Vector3(0, 0, 1).transformDirection(grp.matrixWorld);
    const fov = camera.fov * Math.PI / 180;
    const fit = Math.max(h, w / camera.aspect) / 2;
    // HOW CLOSE IS TOO CLOSE. A distance computed from the selected feature alone
    // scales all the way down with it: an 18.5 x 9.58 mm QSFP-DD cage frames at
    // 35 mm and a 3 mm status LED at 9 mm. What rescued those to 60 mm was
    // controls.minDistance - an orbit collision guard doing framing's job by
    // accident, and badly, because it knows nothing about what is being framed.
    //
    // At any of those distances the cage fills the view and its neighbours fall
    // outside it, so the one question selecting a port asks - WHICH port - is the
    // one thing the frame cannot answer. Identifying a part is a comparison with
    // the parts beside it, and a frame with no neighbours in it has thrown that
    // away to show detail nobody asked for.
    //
    // So: no closer than the distance a person actually holds a chassis at to
    // read it. Anything bigger than about a hand's length of panel still frames
    // itself - the floor only reaches features smaller than a fan module, which
    // are exactly the ones that were unreadable.
    const dist = Math.min(Math.max(fit / Math.tan(fov / 2) * 2.2, INSPECT_MM,
                                   controls.minDistance + 20),
                          controls.maxDistance - 10);
    controls.target.copy(centre);
    camera.position.copy(centre).addScaledVector(normal, dist);
    camera.position.y += dist * 0.18;   // a little above face-on, so it reads as 3D
    controls.update();
  }

  // --- loading ----------------------------------------------------------------

  // The component index does NOT depend on the device, so loading it does not
  // belong behind either mode's "did the subject change" guard - that is what
  // made every device switch pull 2 MB of device-independent data down again.
  // Both modes need COMP_INDEX and both need BODY_META with it; jdist means the
  // bytes arrive once per page even with the shell asking for them too.
  async function ensureComponents() {
    if (COMP_INDEX) return;
    const cidx = await jdist(`${DIST}components.json`);
    COMP_INDEX = cidx.components;
    BODY_META = Object.fromEntries(cidx.components.filter(c => c.body)
      .map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c.body]));
  }

  async function loadDevice(device, config) {
    const first = device !== DEV;
    DEV = device;
    COMP = COMP_ENTRY = null;
    await ensureComponents();
    if (first || !devIndex) {
      devIndex = await jdist(`${DIST}${DEV}.configs.json`);
      if (devIndex.chassis && devIndex.chassis.w) {
        W = devIndex.chassis.w; H = devIndex.chassis.h; D = devIndex.chassis.d;
      }
      // THE OPENING VIEW IS SET FROM THE WHOLE BOX, NOT FROM ITS HEIGHT.
      // This was `H * 6`, which reads as a pleasant three-quarter view only
      // while H is small: at 1RU it puts the eye 261 mm up and 362 mm back,
      // about 25 degrees above horizontal. On a 13RU chassis the same formula
      // gives 3426 mm up against 463 mm back - 82 degrees, near plan view - and
      // the C100G opened as a featureless silver diamond that reads as a broken
      // render rather than as its own top panel seen from above. A device's
      // height is the one dimension that varies by more than tenfold across the
      // portfolio, so it is the worst possible thing to scale the camera by.
      // The span is stable: every device now opens at about 22 degrees.
      // The same framing the component path below already uses, rather than a
      // third set of constants: one opening view, two callers.
      const span = Math.max(W, H, D);
      camera.position.set(span * 0.9, span * 0.8, span * 1.6);
      controls.target.set(0, 0, 0);
    }
    CFG = config || devIndex.default;
    await build(CFG);
    await buildHitIndex(CFG);
  }

  async function loadComponent(component, skin) {
    const first = component !== COMP;
    COMP = component;
    DEV = null;
    if (first || !COMP_ENTRY) {
      await ensureComponents();
      COMP_ENTRY = COMP_INDEX.find(e => `${e.ns}/${e.name}@${e.major.slice(1)}` === COMP);
      if (!COMP_ENTRY) throw new Error(`unknown component ${COMP}`);
      W = COMP_ENTRY.size.w; H = COMP_ENTRY.size.h;
      D = COMP_ENTRY.body ? COMP_ENTRY.body.depth : Math.max(COMP_ENTRY.size.d || 2, 2);
      const span = Math.max(W, H);
      camera.position.set(span * 0.9, span * 0.8, span * 1.6);
      camera.near = 5; camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
    }
    CFG = skin || COMP_ENTRY.skins[0];
    await build(CFG);
  }

  function load(spec = {}) {
    return serialise(async () => {
      if (disposed) return;
      if (!spec.component && !spec.device && !DEV)
        throw new Error('viewer3d: load() needs a device or a component');
      // `overrides` is the host's live swap state. Absent leaves the previous set
      // standing, so a caller that does not use the feature never has to mention it.
      if (spec.overrides) OVERRIDES = {...spec.overrides};
      if (spec.component) await loadComponent(spec.component, spec.skin || spec.config);
      else await loadDevice(spec.device || DEV, spec.config);
      // a config switch keeps the host's selection; the boxes were rebuilt
      if (selected) select(selected, {frame: false});
      // and its marks (#664): the halos went with the old scene
      if (MARKS.length) drawMarks();
    });
  }

  // --- loop -------------------------------------------------------------------
  let raf = 0;
  (function loop(now) {
    raf = requestAnimationFrame(loop);
    stepTweens(now || 0);
    LAMPS.step(now || 0);
    controls.update();
    renderer.render(scene, camera);
    lodTick();
  })();

  function exportName() {
    return 'portrayal-' + (DEV || COMP || 'scene').replace(/[^a-z0-9.-]+/gi, '-');
  }
  async function exportData(fmt) {
    const wasVisible = hl && hl.visible;
    if (hl) hl.visible = false;          // a selection marker is not part of the model
    try { return fmt === 'glb' ? await toGLB(scene) : await toUSDZ(scene); }
    finally { if (hl) hl.visible = wasVisible; }
  }
  async function download(fmt) {
    const data = await exportData(fmt);
    const name = `${exportName()}.${fmt}`;
    save(data, name, fmt === 'glb' ? 'model/gltf-binary' : 'model/vnd.usdz+zip');
    return {name, size: data.byteLength ?? data.length};
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(raf);
    ro.disconnect();
    el.removeEventListener('pointermove', onPointerMove);
    el.removeEventListener('pointerleave', onPointerLeave);
    el.removeEventListener('pointerdown', onPointerDown);
    el.removeEventListener('pointerup', onPointerUp);
    controls.dispose();
    clearHighlight();
    clearMarkObjs();
    LAMPS.clear();
    disposeTree(scene);
    scene.clear();
    LOD.length = 0;
    renderer.dispose();
    // a GL context is not released when the last reference drops - the browser
    // keeps ~16 alive and silently kills the oldest, so say so explicitly
    renderer.forceContextLoss();
    el.remove();
    for (const k of Object.keys(listeners)) listeners[k].length = 0;
  }

  // A STATE CHANGE REPAINTS AND NEVER RE-SHAPES, which is the whole reason this
  // is not a rebuild. Re-running the build to light one lamp measured 1.0-1.4 s
  // on the AGR420 - a second and a half of black screen for a click, on a control
  // a user works through a row of ports one at a time. Redrawing only the
  // textures the change actually reaches is ~1.6 ms per node plus one face.
  //
  // WHICH textures is asked of the node's own svg text, not of a lookup: a state
  // class can land on the element being drawn, on an ancestor whose id scopes the
  // rule, or on a descendant with art of its own, and a substring test over the
  // text that carries all three cannot miss the case a table would.
  //
  // The face texture goes through the LOD path rather than a second raster of its
  // own. It already knows how to re-rasterise a face at the current density and
  // re-punch its apertures, and a face repainted by hand here would silently lose
  // its cavities the moment the camera moved.
  // TAKE PARTS OFF, AND PUT THEM BACK. `paths` is the whole set that should be
  // off, not a delta, so a host can hand over its own state and a reset is
  // setPulled([]) rather than a walk over every control.
  //
  // It repaints rather than rebuilding, which is the same bargain a lamp state
  // strikes: a face is a texture drawn from a fragment of SVG, and hiding an
  // element in that fragment and redrawing costs one raster instead of a
  // 1.0-1.4 s rebuild. What it cannot do is un-extrude relief that was already
  // built, so anything with a body gets hidden in the scene as well - and on the
  // NEXT rebuild it is dropped at extraction and the geometry never exists.
  async function applyPulledNow(paths) {
    const next = new Set();
    for (const p of paths || []) if (p) next.add(String(p));
    const changed = new Set();
    for (const p of new Set([...PULLED, ...next]))
      if (PULLED.has(p) !== next.has(p)) changed.add(p);
    PULLED = next;
    if (!changed.size || !box) return 0;
    setReliefPulled(PULLED, SCOPE);
    const isOff = path => {
      for (const p of PULLED) if (path === p || path.startsWith(p + "/")) return true;
      return false;
    };
    // geometry first: a body that was extruded before the part came off is still
    // in the scene, and no amount of repainting a texture removes it
    // A FRU group is keyed by its BAY - 'mid-sff-0' - and the tree pulls the
    // MODULE in it - 'mid-sff-0/module'. The prefix test runs the other way, so
    // an unseated drive kept its body in the scene and the control did nothing.
    for (const [path, g] of Object.entries(FRU_GROUPS))
      g.visible = !isOff(path) && !isOff(path + '/module');
    // AND THE RELIEF OF EVERYTHING THAT IS NOT A FRU, which is where this used
    // to stop. Only modules get a subgroup of their own, because only a module
    // leaves a bay behind it; a bolted-on cover is merged into the shared relief
    // group with everything else on its face. So taking a cover off repainted
    // the face texture underneath it - correctly - and left its extruded body
    // standing there, which reads as a control that does nothing.
    // Every mesh now carries the path it came from, so it can be hidden where it
    // stands without being ejected.
    // THE RELIEF IS NOT UNDER THE CHASSIS BOX. It is its own group on the
    // scene, so a traversal of `box` reached none of it and this hid nothing:
    // a pulled cover only LOOKED gone because its top texture repainted
    // transparent, and its 1 mm of sides stayed. A pulled tray kept its dark
    // back plane and walls, which read as a slab over the board. Walk both.
    for (const root of [box, reliefGroup]) if (root) root.traverse(o => {
      const p = o.userData && o.userData.portrayalPath;
      if (p) o.visible = !isOff(p);
    });
    // a texture is only touched if the change is actually in it
    const touches = text => [...changed].some(p => text.includes(`data-path="${p}"`));
    let n = 0;
    for (const e of RESTYLE) {
      if (!touches(e.svgText)) continue;
      try { await e.run(restyleText(e.svgText, SCOPE)); n++; }
      catch (err) { console.warn('[portrayal] pull repaint failed', err); }
    }
    for (const rec of LOD) {
      if (!touches(rec.svgText)) continue;
      rec.svgText = restyleText(rec.svgText, SCOPE);
      rec.rev++;
      await refineFace(rec, rec.level);
      n++;
    }
    await syncLamps(changed);
    return n;
  }

  // ONE REPAINT AT A TIME, LATEST WINS. Both setters are fire-and-forget from
  // the host and each awaits a chain of rasterisations, so two chip clicks in
  // quick succession ran interleaved: whichever raster finished last won each
  // texture, and it was not always the newer one. A state and a pull change are
  // queued behind builds and behind each other; a setter called while its own
  // job is queued replaces that job's argument rather than adding a second.
  const pending = {};
  function coalesce(kind, arg, run) {
    pending[kind] = {arg};
    if (pending[kind + 'Job']) return pending[kind + 'Job'];
    return (pending[kind + 'Job'] = serialise(async () => {
      pending[kind + 'Job'] = null;
      const {arg} = pending[kind]; pending[kind] = null;
      try { return await run(arg); }
      catch (err) { console.warn(`[portrayal] 3D ${kind} sync failed`, err); return 0; }
    }));
  }
  const setPulled = paths => coalesce('pulled', paths, applyPulledNow);
  const setStates = map => coalesce('states', map, applyStatesNow);
  const setFields = map => coalesce('fields', map, applyFieldsNow);   // same queue: latest wins
  const setLampColors = map => coalesce('lamps', map, applyLampColorsNow);

  // A LAMP IN THE HOST'S COLOUR (#664): `{path: '#ff00ff'}`, the whole map each
  // time, {} clears. The colour goes into the text every texture is painted
  // from (relief.js applyNodeLampColors), so it repaints and never re-shapes,
  // survives a rebuild from the scope's registry, and an animated lamp's frames
  // (lamps.js) are rasterised from the same text. A lamp registered `state-off`
  // stays unlit, as in 2D. Returns the paths whose colour was not a hex.
  let lampRejected = [];
  async function applyLampColorsNow(map) {
    const before = nodeLampColors(SCOPE);
    lampRejected = setNodeLampColors(map, SCOPE);
    const after = nodeLampColors(SCOPE);
    const changed = new Set();
    for (const k of new Set([...before.keys(), ...after.keys()]))
      if (before.get(k) !== after.get(k)) changed.add(k);
    if (!changed.size || !box) return {repainted: 0, rejected: lampRejected};
    const touches = text => [...changed].some(p => text.includes(`data-path="${p}"`));
    let n = 0;
    for (const e of RESTYLE) {
      if (!touches(e.svgText)) continue;
      try { await e.run(restyleText(e.svgText, SCOPE)); n++; }
      catch (err) { console.warn('[portrayal] restyle failed', err); }
    }
    for (const rec of LOD) {
      if (!touches(rec.svgText)) continue;
      rec.svgText = restyleText(rec.svgText, SCOPE);
      rec.rev++;
      await refineFace(rec, rec.level);
      n++;
    }
    await syncLamps(changed);
    return {repainted: n, rejected: lampRejected};
  }

  async function syncLamps(changed) {
    if (!box) return;
    const isOff = path => {
      for (const p of PULLED) if (path === p || path.startsWith(p + '/')) return true;
      return false;
    };
    try {
      await LAMPS.sync({faces: LOD, entries: RESTYLE, faceGroups, fruGroups: FRU_GROUPS,
                        faceFlip: FACE_FLIP, pxmm: Math.max(PXMM, 16),
                        restyle: t => restyleText(t, SCOPE), changed, isOff,
                        tint: rec => FACE_TINT[rec.matIndex] ?? 1});
    } catch (err) { console.warn('[portrayal] lamp animation sync failed', err); }
  }

  async function applyStatesNow(map) {
    const next = {};
    for (const [k, v] of map instanceof Map ? map : Object.entries(map || {}))
      if (v) next[k] = String(v);
    const changed = new Set();
    for (const k of new Set([...Object.keys(STATES), ...Object.keys(next)]))
      if (STATES[k] !== next[k]) changed.add(k);
    STATES = next;
    if (!changed.size || !box) return 0;
    setNodeStates(STATES, SCOPE);
    const touches = text => [...changed].some(p => text.includes(`data-path="${p}"`));
    let n = 0;
    for (const e of RESTYLE) {
      if (!touches(e.svgText)) continue;
      try { await e.run(restyleText(e.svgText, SCOPE)); n++; }
      catch (err) { console.warn('[portrayal] restyle failed', err); }
    }
    for (const rec of LOD) {
      if (!touches(rec.svgText)) continue;
      rec.svgText = restyleText(rec.svgText, SCOPE);
      rec.rev++;
      await refineFace(rec, rec.level);
      n++;
    }
    await syncLamps(changed);
    return n;
  }

  // WRITE ON A PART: `{ 'psu-1/module': {watts: '750W'} }`. A field is a
  // `data-from` text node the part declares; the value replaces it in every
  // texture the part is drawn in. Same route as setStates, and like it the
  // whole map is the new truth - a part left out goes back to its drawing.
  async function applyFieldsNow(map) {
    const next = {};
    for (const [k, vals] of map instanceof Map ? map : Object.entries(map || {}))
      if (vals && Object.keys(vals).length) next[k] = {...vals};
    const changed = new Set();
    for (const k of new Set([...Object.keys(FIELDS), ...Object.keys(next)]))
      if (JSON.stringify(FIELDS[k]) !== JSON.stringify(next[k])) changed.add(k);
    FIELDS = next;
    if (!changed.size || !box) return 0;
    setNodeFields(FIELDS, SCOPE);
    const touches = text => [...changed].some(p => text.includes(`data-path="${p}"`));
    let n = 0;
    for (const e of RESTYLE) {
      if (!touches(e.svgText)) continue;
      try { await e.run(restyleText(e.svgText, SCOPE)); n++; }
      catch (err) { console.warn('[portrayal] field repaint failed', err); }
    }
    for (const rec of LOD) {
      if (!touches(rec.svgText)) continue;
      rec.svgText = restyleText(rec.svgText, SCOPE);
      // the same revision bump the state and pull setters use: a refine already
      // in flight captured the old text, and must not land over this one
      rec.rev++;
      await refineFace(rec, rec.level);
      n++;
    }
    // an animated lamp on that face keys its frames on the entry text
    await syncLamps(changed);
    return n;
  }

  return {
    load, select, on, resize, dispose, setStates, setFields, fields: () => JSON.parse(JSON.stringify(FIELDS)),
    // #664: persistent coloured marks, and a host's lamp colours
    setMarks, marks: () => MARKS.map(m => ({...m})), get markReport() { return {...markReport}; },
    setLampColors, lampColors: () => Object.fromEntries(nodeLampColors(SCOPE)),
    // the backdrop, for a host that lets its reader choose one - the loop
    // redraws every frame, so setting it is all there is to do
    setBackground: c => { scene.background = new THREE.Color(c); },
    states: () => ({...STATES}),
    setPulled,
    pulled: () => new Set(PULLED),
    // what a host needs to rebuild the chrome this module gave up
    frus, toggleFru, download, exportData, exportName,
    // every path select() can find, for a host without its own tree
    paths: () => ALL_VIEWS.flatMap(view =>
      pathIndex[view].map(c => ({view, path: c.path, cls: c.cls, model: c.model}))),
    capabilities: () => caps,
    lod: () => lodSummary,
    // `info` and `selection` are properties, not calls: they are a snapshot of
    // what the viewer currently holds, and a getter cannot go stale in a host's
    // local variable the way a copied object can. The design note writes them
    // as info()/selection(); nothing calls them that way yet, and renaming a
    // pinned name to match a note is the wrong way round.
    get info() {
      return {device: DEV, component: COMP, config: CFG,
              model: devIndex && devIndex.model, chassis: {w: W, h: H, d: D},
              configs: devIndex ? devIndex.configs.map(c => c.name) : [],
              defaultConfig: devIndex && devIndex.default,
              skins: COMP_ENTRY ? COMP_ENTRY.skins : []};
    },
    get selection() { return selected; },
    // debug handle: lets devtools and the pose-diff harness drive the built scene
    // LIVE, NOT A SNAPSHOT. The scene is rebuilt on every load and the camera
    // and controls are recreated with it; a handle that captured them once
    // measured a dead scene - every halo projected to the same pixel and a
    // framing select "moved nothing". Getters read whatever is current.
    three: {THREE, LOD, LAMPS, refine: (rec, px) => refineFace(rec, px),
            get scene() { return scene; }, get camera() { return camera; },
            get renderer() { return renderer; }, get controls() { return controls; }},
  };
}
