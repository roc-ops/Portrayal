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
         setNodeStates, nodeStates, restyleText,
         setPulled as setReliefPulled, pulledPaths,
         buildFaceRelief, squareFaceplate } from './relief.js';
import { applyOverrides } from './swap.js';
import { jdist } from './dist.js';

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

  async function refineFace(rec, pxmm) {
    if (rec.busy || rec.level === pxmm || !box) return;
    rec.busy = true;
    try {
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
    } catch (e) {
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
  async function applyBayOverrides(cfg) {
    clearSvgOverrides(SCOPE);
    if (COMP || !devIndex?.bays || !Object.keys(OVERRIDES).length) return 0;
    const byRef = ref => (COMP_INDEX || []).find(
      c => `${c.ns}/${c.name}@${c.major.slice(1)}` === ref.split(':')[0]);
    const loadSkin = async ref => {
      const c = byRef(ref);
      if (!c) return null;
      const skin = c.skins?.includes('default') ? 'default' : c.skins?.[0];
      const url = `${DIST}components/${c.ns}--${c.name}--${c.major}--${skin}.svg`;
      return {comp: c, text: await svgSource(url, SCOPE)};
    };
    let total = 0;
    for (const [view, bays] of Object.entries(devIndex.bays)) {
      if (!bays.some(b => Object.prototype.hasOwnProperty.call(OVERRIDES, b.id))) continue;
      const url = `${DIST}${DEV}.${cfg}.${view}.svg`;
      let text;
      try { text = await svgSource(url, SCOPE); } catch { continue; }
      const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
      if (doc.querySelector('parsererror')) continue;
      const n = await applyOverrides(doc.documentElement, bays, OVERRIDES, loadSkin);
      if (!n) continue;
      setSvgOverride(url, new XMLSerializer().serializeToString(doc), SCOPE);
      total += n;
    }
    return total;
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
    const f = v => `${DIST}${DEV}.${cfg}.${v}.svg`;
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
    lodPaused = performance.now() + 500;   // no refinement while the build is in flight
    _punchCache.clear();
    // Relief is built in LOCAL face coordinates (x right, y up, z out of the face,
    // face plane at z=0) and oriented by a per-face group transform. flipLY handles
    // views whose y axis runs opposite to the face's local up (top view).
    const FACES = COMP ? [
      {view: 'comp', url: DIST + COMP_ENTRY.files[cfg],
       fw: () => W, fh: () => H, pos: () => [0, 0, D / 2], rot: [0, 0, 0]},
    ] : [
      {view: 'front', fw: () => W, fh: () => H, pos: () => [0, 0, D / 2], rot: [0, 0, 0]},
      {view: 'rear',  fw: () => W, fh: () => H, pos: () => [0, 0, -D / 2], rot: [0, Math.PI, 0]},
      {view: 'right', fw: () => D, fh: () => H, pos: () => [W / 2, 0, 0], rot: [0, Math.PI / 2, 0]},
      {view: 'left',  fw: () => D, fh: () => H, pos: () => [-W / 2, 0, 0], rot: [0, -Math.PI / 2, 0]},
      {view: 'top',   fw: () => W, fh: () => D, pos: () => [0, H / 2, 0], rot: [-Math.PI / 2, 0, 0]},
    ];
    const built = {};
    for (const F of FACES) {
      const before = meshes.length;
      await buildFaceRelief(F, {src: F.url || f(F.view), faceCv, faceSvg, facePunch,
                                meshes, FRU_GROUPS, FRU_META, BODY_META, D, bodyBoxMesh,
                                restyle: RESTYLE, scope: SCOPE});
      // a face with no drawing falls back to flat colour and contributes no group
      if (meshes.length > before) built[F.view] = meshes[meshes.length - 1];
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
      // the underside gets no relief pass, so square its faceplate here too
      const bottomTxt = squareFaceplate(await svgSource(f('bottom'), SCOPE));
      const bottomCv = await rasterize(bottomTxt, W, D, PXMM, true, true);
      faceSvg.bottom = bottomTxt;
      mats = [faceCv.right, faceCv.left, faceCv.top, bottomCv, faceCv.front, faceCv.rear]
        .map((c, i) => {
          const m = new THREE.MeshBasicMaterial(
            // alphaTest: punched pixels must not write depth, or they occlude interiors
            {map: canvasTex(c), transparent: i !== 3, alphaTest: i !== 3 ? 0.1 : 0,
             alphaToCoverage: i !== 3});
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
    if (reliefGroup) { scene.remove(reliefGroup); disposeTree(reliefGroup); }
    for (const k of Object.keys(faceGroups)) delete faceGroups[k];
    Object.assign(faceGroups, built);
    const fp = COMP && COMP_ENTRY.body && COMP_ENTRY.body.footprint;
    if (fp) {
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
    } else {
      box = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), mats);
      scene.add(box);
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
         ['rear',   5, W, H, [0, 0, -D / 2], [0, Math.PI, 0],      false, false]];
    for (const [k, matIndex, wmm, hmm, pos, rot, flipX, flipY] of lodFaces) {
      if (!faceSvg[k]) continue;   // face fell back to flat colour - nothing to sharpen
      LOD.push({key: k, matIndex, wmm, hmm, svgText: faceSvg[k], flipX, flipY,
                punches: facePunch[k] || [],
                frame: FRAME(pos, rot), level: PXMM, busy: false, gen});
    }
    reliefGroup = new THREE.Group();
    meshes.forEach(m => reliefGroup.add(m));
    scene.add(reliefGroup);
  }

  // hit-testing: hidden inline SVGs give us component boxes in mm via getBBox/CTM
  const hitIndex = {front: [], rear: []};
  const pathIndex = {front: [], rear: []};
  async function buildHitIndex(cfg) {
    for (const view of ['front', 'rear']) {
      const div = document.createElement('div');
      div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
      div.innerHTML = await svgSource(`${DIST}${DEV}.${cfg}.${view}.svg`, SCOPE);
      document.body.appendChild(div);
      const svg = div.querySelector('svg');
      const inv = svg.getScreenCTM().inverse();
      const rec = el => {
        const b = el.getBBox();
        const m = inv.multiply(el.getScreenCTM());
        const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
          .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
        return {path: el.dataset.path, cls: el.dataset.class || '',
                model: el.dataset.model || '', x0: Math.min(pts[0].x, pts[1].x), y0: Math.min(pts[0].y, pts[1].y),
                x1: Math.max(pts[0].x, pts[1].x), y1: Math.max(pts[0].y, pts[1].y)};
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
    const hit = ray.intersectObject(box)[0];
    if (!hit) return null;
    const view = hit.face.materialIndex === 4 ? (COMP ? 'comp' : 'front')
               : hit.face.materialIndex === 5 ? 'rear' : null;
    if (!view || COMP) return {view: view || SIDE_NAMES[hit.face.materialIndex], path: null};
    const x = hit.uv.x * W, y = (1 - hit.uv.y) * H;
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
      for (const view of ['front', 'rear']) {
        const c = pathIndex[view].find(e => e.path === p);
        if (c) return {view, c, exact: n === parts.length};
      }
    }
    return null;
  }

  function select(path, o = {}) {
    clearHighlight();
    selected = path || null;
    if (!path) return false;
    const found = locate(path);
    if (!found) return false;
    const {view, c} = found;
    const grp = faceGroups[view];
    if (!grp) return false;
    const w = Math.max(c.x1 - c.x0, 0.4), h = Math.max(c.y1 - c.y0, 0.4);
    const lx = c.x0 + w / 2 - W / 2, ly = H / 2 - (c.y0 + h / 2);
    hl = new THREE.Group();
    const geo = new THREE.PlaneGeometry(w, h);
    // depthTest off, drawn last: the same argument hl.js makes in 2D - a halo that
    // neighbours can paint over is not a halo. Here the neighbour is a handle or a
    // cage standing proud of the face.
    const fillMat = new THREE.MeshBasicMaterial({color: HL_COLOR, transparent: true,
      opacity: 0.18, depthTest: false, depthWrite: false});
    const lineMat = new THREE.LineBasicMaterial({color: HL_COLOR, depthTest: false,
      transparent: true});
    hl.add(new THREE.Mesh(geo, fillMat));
    hl.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo), lineMat));
    hl.traverse(o2 => { o2.renderOrder = 999; });
    hl.position.set(lx, ly, 0.8);
    // ride with the module if it is a FRU, so ejecting it does not leave the
    // marker behind on the chassis
    const owner = FRU_GROUPS[path.split('/')[0]];
    (owner || grp).add(hl);
    if (o.frame !== false) frameOn(grp, lx, ly, w, h);
    return true;
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
    });
  }

  // --- loop -------------------------------------------------------------------
  let raf = 0;
  (function loop(now) {
    raf = requestAnimationFrame(loop);
    stepTweens(now || 0);
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
  async function setPulled(paths) {
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
    for (const [path, g] of Object.entries(FRU_GROUPS)) g.visible = !isOff(path);
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
      const at = rec.level;
      rec.level = 0;                    // refineFace no-ops at the level it holds
      await refineFace(rec, at);
      n++;
    }
    return n;
  }

  async function setStates(map) {
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
      const at = rec.level;
      rec.level = 0;                    // refineFace no-ops at the level it holds
      await refineFace(rec, at);
      n++;
    }
    return n;
  }

  return {
    load, select, on, resize, dispose, setStates,
    states: () => ({...STATES}),
    setPulled,
    pulled: () => new Set(PULLED),
    // what a host needs to rebuild the chrome this module gave up
    frus, toggleFru, download, exportData, exportName,
    // every path select() can find, for a host without its own tree
    paths: () => ['front', 'rear'].flatMap(view =>
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
    three: {THREE, scene, camera, renderer, controls, LOD},
  };
}
