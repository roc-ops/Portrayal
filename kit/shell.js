// The shell every device page in v2 is built on: stage, tree, inspector, bar.
//
// v1 grew two pages that were nearly the same page. explore.html and
// interactive.html each built their own tree from the same data and drifted
// until one device read differently on each of them. So the shell is one copy,
// and a page is the shell plus its own panel - that is the whole difference
// between the Explorer and the Annotator.
//
//   const shell = createShell({title: 'Portrayal explorer'});
//   shell.on('row', (row, node) => { ... });     // decorate a tree row
//   shell.on('inspect', ctx => true);            // take over the inspector
//   await shell.ready;
//
// The tree rules in here were all earned. Read the comments before changing
// one: every ordering rule exists because a specific device read badly without
// it, and the comment says which.

import { createDevicePicker } from './devsel.js';
import { nosNameFor } from './nosnames.js';
import { nestedBays, applyOverrides, applyOccupantOverrides, applyRearOverrides, acceptSwaps, decodeSwaps,
         occupantsOf,
         rawParam, liesOver, seatClaims, occupantRef, refusalReason,
         builtOccupants, builtBays, faceCages, cageAt, pruneCarrier,
         freshBaysUnder, seatFace, faceQueue, swapOverrides, faceEntries, faceTree, ownerPath,
         slotOptions, slotResolver } from './swap.js';
import { jdist, faceFile, distResolver } from './dist.js';
import { paintFields, unpaintFields } from './fields.js';
import { fibreOf, farPath, fibreLabel, connectorLabel, moduleOf } from './optical.js';

const NS = 'http://www.w3.org/2000/svg';

export const esc = s => String(s ?? '').replace(/[&<>"]/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

export const SHELL_CSS = `
  :root { --bg:#16181b; --panel:#1c2024; --line:#2b3035; --ink:#d7dbdf; --dim:#8d939a;
          --accent:#4c9aff; --warn:#f59e0b;
          --control:#23272c; --control-line:#3a4046; --control-hover:#2c3137;
          --control-hover-line:#4d545b; --field:#1c1f23; --field-line:#33373c; --hint:#6b7178;
          --on-bg:#2f4a6d; --on-ink:#eaf1fb; --stage:#101214; --sel-ink:#fff;
          --kid-line:#262b30;
          /* selection colour. Deliberately NOT --accent: the halo has to stand out
             against the faceplate it is drawn on, and a chassis can be any colour,
             so this is user-settable and remembered. */
          --hl:#ff2d95; }
  * { box-sizing: border-box; }
  body { margin:0; height:100vh; display:flex; flex-direction:column;
         font-family: system-ui, sans-serif; background:var(--bg); color:var(--ink); }
  header { display:flex; gap:0.7rem; align-items:center; flex-wrap:wrap;
           padding:0.55rem 0.9rem; border-bottom:1px solid var(--line); background:var(--panel); }
  header h1 { font-size:0.86rem; margin:0 0.5rem 0 0; font-weight:600; letter-spacing:0.02em; }
  select, button, input { font:inherit; font-size:0.78rem; background:var(--control); color:var(--ink);
                   border:1px solid var(--control-line); border-radius:6px; padding:0.26rem 0.5rem; }
  button { cursor:pointer; }
  button:hover { background:var(--control-hover); }
  button.on { background:var(--on-bg); border-color:var(--accent); color:var(--on-ink); }
  label.f { font-size:0.72rem; color:var(--dim); display:flex; gap:0.32rem; align-items:center; }
  main { flex:1; display:flex; min-height:0; }
  #stage { flex:1; position:relative; overflow:hidden; background:var(--stage); min-width:0; }
  /* the SVG lives in its own host so a page can put another stage - a 3D canvas -
     beside it and swap which one is showing without the two fighting over
     pointer events or over #stage's children */
  .stage-host { position:absolute; inset:0; overflow:hidden; }
  .stage-host[hidden] { display:none; }
  #stage svg { position:absolute; transform-origin:0 0; }
  aside { width:23rem; border-left:1px solid var(--line); background:var(--panel);
          display:flex; flex-direction:column; min-height:0; }
  #crumb { padding:0.5rem 0.7rem; border-bottom:1px solid var(--line); font-size:0.76rem;
           color:var(--dim); display:flex; gap:0.3rem; align-items:center; flex-wrap:wrap; }
  #crumb b { color:var(--ink); font-weight:600; }
  #crumb button { padding:0.1rem 0.4rem; font-size:0.7rem; }
  #tree { flex:1; overflow:auto; padding:0.4rem 0.2rem 1rem; }
  .node { display:flex; align-items:center; gap:0.3rem; padding:0.12rem 0.5rem;
          font-size:0.76rem; cursor:pointer; border-radius:4px; white-space:nowrap; }
  .node:hover { background:var(--control); }
  .node.sel { background:var(--hl); color:var(--sel-ink); }
  .node.linked { outline:1px dashed var(--hl); outline-offset:-1px; }
  .node.grp { color:var(--dim); text-transform:uppercase; font-size:0.68rem;
              letter-spacing:0.05em; margin-top:0.25rem; }
  .node.grp .cls { text-transform:none; letter-spacing:0; }
  #hl { display:flex; align-items:center; gap:0.25rem; }
  #hl .sw { width:0.95rem; height:0.95rem; border-radius:3px; cursor:pointer;
            border:1px solid #00000055; }
  #hl .sw.on { outline:2px solid var(--ink); outline-offset:1px; }
  #stagebg { display:flex; align-items:center; gap:0.25rem; }
  #stagebg .sw { width:0.95rem; height:0.95rem; border-radius:3px; cursor:pointer;
                 border:1px solid var(--control-line); }
  #stagebg .sw.on { outline:2px solid var(--ink); outline-offset:1px; }
  #hl input[type=color] { width:1.5rem; height:1.2rem; padding:0; border:none;
            background:none; cursor:pointer; }
  .node .tw { width:0.85rem; color:var(--dim); flex:none; text-align:center; }
  .node .cls { color:var(--dim); font-size:0.68rem; margin-left:auto; padding-left:0.5rem; }
  /* TAKE IT OFF AND LOOK BEHIND IT. A cover is a real part that hides real parts -
     the C40G's filter cover sits over four power supplies - and the only way to see
     what it covers used to be to not draw it. The control appears on rows whose
     component says how it comes out, so it arrives on every removable part in the
     library at once rather than being wired up per device. */
  .node .pull { color:var(--dim); font-size:0.72rem; padding:0 0.35rem; cursor:pointer;
                border-radius:3px; flex:none; opacity:0.55; }
  .node .pull:hover { opacity:1; background:var(--hl); color:#fff; }
  .node.pulled .nm { opacity:0.45; text-decoration:line-through; }
  .node.pulled .pull { opacity:1; color:var(--warn); }
  /* Absent entirely when nothing is off: a chip that always reads "0 removed" is
     one more thing to read past on a header that is already seven items wide. */
  #pulled { color:var(--warn); cursor:pointer; border:1px solid var(--warn);
            border-radius:4px; padding:0.1rem 0.4rem; font-size:0.74rem; }
  #pulled:hover { background:var(--warn); color:#16181b; }
  [data-portrayal-pulled] { display:none !important; }
  .node.empty .nm { color:var(--warn); font-style:italic; }
  /* a target in another view: the row cannot nest under it, so it says it */
  .node .xref { color:var(--dim); font-size:0.68rem; padding-left:0.5rem;
            white-space:nowrap; }
  .kids { margin-left:0.72rem; border-left:1px solid var(--kid-line); }
  .kids.hid { display:none; }
  /* the About panel is long, and the tree above it must not be squeezed to a
     sliver by it - so the inspector scrolls in its own right */
  #inspect { border-top:1px solid var(--line); padding:0.6rem 0.7rem; font-size:0.76rem;
             max-height:55%; overflow:auto; }
  #inspect h2 { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--dim); margin:0 0 0.4rem; }
  #inspect h3 { font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em;
                color:var(--dim); margin:0.8rem 0 0.3rem; border-top:1px solid var(--line);
                padding-top:0.5rem; }
  #inspect .row { display:flex; gap:0.4rem; align-items:baseline; margin-bottom:0.35rem; }
  #inspect .row span { color:var(--dim); min-width:5rem; flex:none; }
  /* a value is prose - a description, a provenance citation - so it wraps and it
     is allowed to shrink. Without min-width:0 a flex item refuses to go below its
     content width and the whole panel scrolls sideways instead. */
  #inspect .row .v { white-space:pre-wrap; flex:1 1 auto; min-width:0; }
  .hint { color:var(--dim); font-size:0.72rem; padding:0.5rem 0.7rem; line-height:1.5; }
  .halo { fill:none; stroke:var(--hl); stroke-width:1.4; vector-effect:non-scaling-stroke;
          pointer-events:none; }
  .halo.pulse { animation: p 1.1s ease-out 2; }
  /* THE FAR END OF A FIBRE is a dashed ring, not an outline on the part: an
     outline is drawn in the drawing's units (mm), and on a 0.075 mm fibre dot
     it was a solid block over half the ferrule that said nothing about which
     fibre. Its stroke, dashes and padding are set per zoom in screen px by
     sizeFarRing: non-scaling-stroke does not see the stage's CSS zoom, so at
     20x a 1.4 "px" stroke was 28 px and filled the ring solid. */
  .halo.linked { vector-effect:none; }
  @keyframes p { 0%,100%{ stroke-opacity:1 } 50%{ stroke-opacity:0.25 } }
`;

const SHELL_HTML = `
<header>
  <h1></h1>
  <span class="f" id="devpick"></span>
  <label class="f">config <select id="cfg"></select></label>
  <label class="f">view <select id="view"></select></label>
  <span class="f" id="hl" title="Selection colour - pick one that stands out against this chassis"></span>
  <span class="f" id="stagebg" title="Background - a dark chassis reads better on a light stage"></span>
  <button id="fit">Fit</button>
  <span class="f" id="pulled" hidden></span>
  <span class="f" id="status"></span>
</header>
<main>
  <div id="stage"><div class="stage-host" id="stage-svg"></div></div>
  <aside>
    <div id="crumb"></div>
    <div id="tree"></div>
    <div id="inspect"></div>
  </aside>
</main>`;

// The two indexes are the same for every shell on the page, and there is only
// ever one, but caching them keeps a re-mount cheap.
let DEVICES = [], COMPONENTS = [], LISTINGS = {};

export function createShell(opts = {}) {
  let picker = null;
  // a build directory's base, or a path -> URL function (dist.js)
  const distAt = distResolver(opts.dist, '../dist');
  const body = opts.mount || document.body;
  // shared with the 3D viewer mounted in the same page - see dist.js
  const j = p => jdist(distAt(p));

  document.head.appendChild(Object.assign(document.createElement('style'),
                                          {textContent: SHELL_CSS}));
  body.insertAdjacentHTML('afterbegin', SHELL_HTML);
  const $ = s => body.querySelector(s);
  const el = {
    header: $('header'), main: $('main'), stage: $('#stage'), svgHost: $('#stage-svg'),
    aside: $('aside'), crumb: $('#crumb'), tree: $('#tree'), inspect: $('#inspect'),
    status: $('#status'), pulled: $('#pulled'), dev: $('#devpick'), cfg: $('#cfg'), view: $('#view'), fit: $('#fit'),
  };
  $('header h1').textContent = opts.title || 'Portrayal';

  // `cfgGen` counts every wholesale replacement of cfgBays/cfgOccupants/touched
  // (syncCfgBays, the only place that does it - see there). It exists because
  // that replacement runs SYNCHRONOUSLY, strictly before the loadStage() that
  // follows it gets as far as its own `await fetch` and reassigns `state.svg`:
  // a seat() started on the old configuration, captured mid-flight, can have
  // its skin resolve inside that window, when the claim is still live and
  // `state.svg` has not moved yet either. `svg === state.svg` alone cannot see
  // that window; `cfgGen` can, because it changes at the exact moment the
  // objects a stale write would land in are swapped out from under it.
  // `listing` is the NOS vendor's entry the reader chose, `<ns>/<id>` from
  // listings.json, or null for the hardware's own (#709). It never changes
  // what is drawn - a listing draws nothing - only whose box this is.
  const state = {device: null, listing: null, cfg: null, view: null, module: null, sel: null,
                 svg: null, meta: null, cfgBays: {}, cfgOccupants: {}, cfgFields: {},
                 touched: new Set(), refused: {}, failed: {}, cfgGen: 0};

  const handlers = {};
  const on = (name, fn) => { (handlers[name] ||= []).push(fn); };
  const emit = (name, ...a) => (handlers[name] || []).map(fn => fn(...a));

  const compByRef = ref => {
    const [ns, rest] = ref.split('/');
    const [name, major] = rest.split('@');
    return COMPONENTS.find(c => c.ns === ns && c.name === name && c.major === 'v' + major);
  };

  // A BAY ON THE DEVICE, OR A BAY INSIDE WHATEVER IS SEATED IN ONE. The first
  // is in the manifest; the second cannot be, because which nested bays exist
  // depends on what is currently populated. swap.js reads those off the drawing
  // - see `nestedBays` there for why they are resolved rather than merged into
  // `meta.bays`, which the status line counts.
  const bayFor = path => (state.meta?.bays?.[bayView()] || []).find(b => b.id === path)
    || (state.svg ? nestedBays(state.svg, compByRef).find(b => b.id === path) : null)
    || null;

  // A CAGE OF THE FACE ON SCREEN, found from the port OR from the optic in it.
  // `meta.cages` is keyed by view exactly as `meta.bays` is, so it is read
  // through bayView() for the same reason. An optic the build (or a swap) seated
  // names its cage with `data-for` and `data-behaviour="occupies"`, so a path
  // inside one resolves to its host, and clicking the optic offers the same
  // select as clicking the port. `data-for` alone is not enough: the port's
  // LED is `data-for` it too, and must stay the LED.
  //
  // A CAGE ON A SEATED CARD is one too (#484): `front-6/module/xg0`, read off
  // the drawing by swap.js's `nestedCages` as `bayFor` reads a nested bay, for
  // the same reason - which cages exist depends on what the bays hold. The
  // rule for both kinds, and for a click inside either optic, is swap.js's
  // `cageAt` over `faceCages`, the list the 3D pass seats through as well.
  //
  // A SLOT AT ANY DEPTH is one too (B3 Task 10a): a cassette's duplex
  // adapter, its bores, an adapter placed on the device - swap.js's
  // `nestedSlots`. `cageFor` offers only the FREE level of a duplex adapter
  // (cageAt); `cagesOnFace` is every slot, because a swap seats through it
  // and a reload re-seats an emptied level and the filled one in any order.
  const cagesHere = () => (state.module ? [] : state.meta?.cages?.[bayView()] || []);
  const cagesOnFace = () => (state.module ? [] : faceCages(state.svg, cagesHere(), compByRef));
  function cageFor(path) {
    if (path == null || state.module) return null;
    return cageAt(state.svg, path, cagesHere(), compByRef);
  }

  // THE REF OF A DEVICE PLACEMENT, off whichever face draws it - the one fact
  // about a slot on the device (`xc01/1`) that no index publishes
  // (configs.json's cages carry no ref). What swap.js's slotResolver asks
  // when there is no drawing to read the slot off.
  // Only faces of the device and configuration on screen: `syncCfgBays` runs
  // before the new device's first face is mounted, when what is held is the
  // last device's. (The mounted face is always among `state.faces`.)
  function placementRef(path) {
    if (state.facesFor !== `${state.device}.${state.cfg}`) return null;
    for (const f of Object.values(state.faces || {})) {
      // with a ref: a group without one (a label, a cutout) at the same path
      // must not shadow the placement
      const r = f?.querySelector?.(`[data-path="${CSS.escape(path)}"][data-ref]`)?.getAttribute('data-ref');
      if (r) return r.split(':')[0];
    }
    return null;
  }
  const allOf = o => Object.values(o || {}).flat();
  // what the configuration on screen seats in each slot it keys, at the
  // drawing's path (a deep key walked through its bays - builtOccupants)
  const builtOccOf = cfg => builtOccupants(cfg, allOf(state.meta?.cages),
                                           {bays: allOf(state.meta?.bays), compByRef, placementRef});

  // ---------------------------------------------------------------- stage

  let zoom = 1, panX = 0, panY = 0;
  // one dashed ring per far end of a selected fibre (select); here because
  // applyTransform re-pads them on every zoom
  let farHalos = [];
  // set while the pointer is panning, so the click that ends a drag does not
  // also change the selection
  let dragged = false;
  function applyTransform() {
    if (state.svg) state.svg.style.transform = `translate(${panX}px,${panY}px) scale(${zoom})`;
    padFarRings();
  }
  function fit() {
    const svg = state.svg; if (!svg) return;
    const st = el.svgHost.getBoundingClientRect();
    // a hidden host measures 0x0, and fitting to that produces a zoom of 0 that
    // the next fit cannot recover from. The page re-fits when it shows us again.
    if (!st.width || !st.height) return;
    const vb = svg.viewBox.baseVal;
    zoom = Math.min(st.width / vb.width, st.height / vb.height) * 0.92;
    panX = (st.width - vb.width * zoom) / 2;
    panY = (st.height - vb.height * zoom) / 2;
    svg.style.width = `${vb.width}px`; svg.style.height = `${vb.height}px`;
    applyTransform();
  }
  el.fit.onclick = fit;
  el.pulled.onclick = restoreAllPulled;
  el.svgHost.addEventListener('wheel', e => {
    e.preventDefault();
    const k = e.deltaY < 0 ? 1.12 : 1 / 1.12;
    const r = el.svgHost.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    panX = mx - (mx - panX) * k; panY = my - (my - panY) * k;
    zoom *= k; applyTransform();
  }, {passive: false});
  (() => {                              // drag to pan
    let on = false, sx = 0, sy = 0, px = 0, py = 0;
    const st = el.svgHost;
    st.addEventListener('pointerdown', e => { on = true; sx = e.clientX - panX; sy = e.clientY - panY;
                                              px = e.clientX; py = e.clientY; dragged = false; });
    st.addEventListener('pointermove', e => { if (!on) return;
                                              // released outside the stage before it became a drag, so
                                              // nothing captured the pointerup
                                              if (!e.buttons) { on = false; return; }
                                              // a few pixels of travel is a tremor, not a drag; without
                                              // this every click on a part reads as a pan and never
                                              // reaches the selection handler
                                              if (!dragged && Math.abs(e.clientX - px) + Math.abs(e.clientY - py) > 4) {
                                                dragged = true;
                                                // CAPTURE ONLY ONCE IT IS A DRAG. Captured on pointerdown,
                                                // the pointerup - and so the click - lands on this host
                                                // div, and the <svg>'s click listener never hears a real
                                                // mouse click on a part: only tree clicks selected.
                                                st.setPointerCapture(e.pointerId);
                                              }
                                              panX = e.clientX - sx; panY = e.clientY - sy; applyTransform(); });
    st.addEventListener('pointerup', () => { on = false; });
  })();

  // ---------------------------------------------------------------- tree

  // The compiled SVG carries the hierarchy already: every meaningful node has a
  // data-path, '/' separated. Build the tree from that rather than from the
  // contracts, so what you see listed is exactly what is drawn - including
  // what only a projection draws, a cassette's rear MTPs (swap.js faceEntries).
  // The nesting itself is swap.js's `faceTree`, which render.py's elements
  // file follows too (#727), so the published tree and this one are one rule.
  function buildTree(root) {
    const entries = faceEntries(root);
    // document order = manifest order, and the manifest is now written in the order
    // the part is made. That is a better group ordering than the alphabet: it put
    // qsfp28 (ports 4-21) ahead of qsfpdd-400g (ports 0-3) purely on spelling.
    entries.forEach(({el: e}, i) => { if (e.__docIdx === undefined) e.__docIdx = i; });
    return faceTree(root, entries);
  }

  // A row that just says "front-0--module" makes you look at the drawing to find
  // out what is in the slot, which is the opposite of the point. Name the card.
  function modelOf(e) {
    const ref = e.dataset.ref;
    if (!ref) return null;
    const c = compByRef(ref.split(':')[0]);
    return c?.attrs?.model || c?.name || null;
  }
  // A row reads "id — model". The id is the thing you already know (port-7,
  // front-6); the model is the thing you are checking. Model alone gave 54 rows
  // all reading "SFP module", which is why this used to need clicking to use.
  // A port row has to say what the PORT is, not what its cage is. SFP, SFP+ and
  // SFP28 share one cage component because the geometry is genuinely identical -
  // SFF-8433 says so in as many words, "applies to SFP28 too, same cage
  // mechanicals" - so the component name cannot tell you which of the three you
  // are looking at. Twenty-four SFP28 ports were reading "port-4 - sfp-ganged":
  // wrong, and misleading twice over, because "module" there means one position
  // in a ganged block and every reader hears "transceiver". The port already
  // declares itself in data-media/data-speed; read that.
  //
  // Falling back to the component name when a port declares no media is
  // deliberate. It leaves the old label visible on exactly the ports that are
  // genuinely undeclared, which is how you find them.
  const MEDIA = {
    'sfp-plus': 'SFP+', 'qsfp-dd': 'QSFP-DD', 'rj45-serial': 'RJ45 serial',
    'coax-sma': 'SMA', 'coax-smb': 'SMB', 'coax-bnc': 'BNC',
    'coax-din-1-0-2-3': '1.0/2.3', 'coax-f': 'F', 'coax-mcx': 'MCX',
    'micro-usb-b': 'micro-USB B',
    'usb-a': 'USB-A', 'usb-c': 'USB-C', 'sc-apc': 'SC/APC', 'fiber': 'fibre',
    'coax': 'coax', 'ac': 'AC',
    // AC cord ends (#785). `c13` and `c19` read right upper-cased; the
    // Saf-D-Grid plug's key would read SAF-D-GRID.
    'c13': 'C13', 'c19': 'C19', 'saf-d-grid': 'Saf-D-Grid',
    // D-sub and VGA cable plugs (#787) state the key their connector states.
    // Each reads right upper-cased; they are written out so the row a plug
    // adds is labelled by the table and not by the fallback.
    'db9': 'DB9', 'vga': 'VGA', 'da15': 'DA15', 'db25': 'DB25',
    // Pluggable terminal headers and their screw-clamp plugs (#789). The
    // fallback would read TERMINAL-BLOCK and DC-TERMINAL.
    'terminal-block': 'terminal block', 'dc-terminal': 'DC terminal',
    // The DC barrel plug (#789) states `barrel`: `dc-barrel` would make `dc` a
    // connector word for lint L62.
    'barrel': 'DC barrel',
  };
  // A speed is one of spec/schemas/speeds.yaml's closed set (lint L110), and
  // every one of those reads right upper-cased - 1G, 2.5G, 1.6T - so there is
  // no per-value table to keep in step. USB generation and PON flavour are
  // their own attrs (data-usb, data-pon), so they are read on their own:
  // "USB-A 3.0", "SC/APC 10G XGS-PON".
  const mediaLabel = m => MEDIA[m] || m.toUpperCase();
  function portLabel(e) {
    const m = e.dataset.media;
    if (!m) return null;
    const d = e.dataset;
    return [mediaLabel(m), d.usb, d.speed && d.speed.toUpperCase(),
            d.pon && d.pon.toUpperCase()].filter(Boolean).join(' ');
  }

  // The targets of this node that live in another view, spelled as the manifest
  // spells them. Only these need saying out loud - a same-view target is already
  // said by the nesting.
  function xrefOf(e) {
    return (e.dataset.for || '').split(' ')
      .filter(t => t[0] === '/').map(t => t.slice(1));
  }

  function labelFor(n) {
    const e = n.el;
    const own = n.path.split('/').pop();
    // A MARK IS ITS WORDS. `silk:12` names nothing a reader recognises, and the
    // printing is right there in the element - so a legend rows as what it says.
    // A printed line or symbol has no words, and says so rather than showing an
    // index: a leader between a breaker and its terminal is a real mark with
    // nothing to quote.
    if (e.dataset.class === 'silkscreen') {
      const t = (e.textContent || '').trim().replace(/\s+/g, ' ');
      return t ? `“${t}”` : 'printed line';
    }
    if (e.dataset.class === 'bay') {
      const occ = e.querySelector('[data-ref]');
      const m = occ && modelOf(occ);
      return m ? `${own} — ${m}` : own;
    }
    // A REAR HOLE A SLOT IS SEEN THROUGH IS THAT SLOT (render.py stamps it).
    // "open" means no occupant (no data-rear-ref); a ref that compByRef
    // cannot resolve is not open - it is unresolved, so it labels with the
    // ref itself rather than claiming the slot is empty.
    if (e.dataset.rearOf) {
      const ref = e.dataset.rearRef;
      const c = ref && compByRef(ref.split(':')[0]);
      const m = c?.attrs?.model || c?.name;
      return `${e.dataset.rearOf} — ${ref ? (m || ref) : 'open'} (rear)`;
    }
    // A FIBRE ROW SAYS WHERE IT GOES; A REAR CONNECTOR, WHICH FRONT PORTS IT CARRIES
    const mod = moduleOf(n.path);
    if (mod) {
      const entry = moduleEntry(mod);
      const f = entry && fibreOf(n.path, entry, compByRef);
      if (f) return fibreLabel(entry, f.endpoint) || own;
      const rel = n.path.slice(mod.length + 1);
      if (entry && !rel.includes('/') && n.projected) {
        const carries = connectorLabel(entry, rel, 'rear');
        if (carries) return `${own} — ${carries}`;
      }
    }
    const port = portLabel(e);
    if (port) return `${own} — ${port}`;
    const model = modelOf(e);
    if (model && model !== own) return `${own} — ${model}`;
    // an internal id (`cutout--3`) is not a name; the row's own id reads better
    const title = e.querySelector(':scope > title')?.textContent.trim();
    return title && !title.includes('--') ? title : own;
  }

  // Ordering rules. Tier comes from the component's class, never from the author,
  // so it cannot drift between devices:
  //   1  things you connect to or replace   bays, ports, PSUs, fans, cards
  //   2  things you read                    LEDs, buttons, displays
  //   3  furniture                          ears, swoops, cable managers, grounding
  // Within a tier: group, then rel-pos, then a numeric-aware id sort. Never a
  // plain string sort, which is what put 52 LEDs in front of 54 ports.
  const TIER = {
    bay: 1, port: 1, transceiver: 1, psu: 1, fan: 1, cooling: 1, power: 1, inlet: 1,
    'line-card': 1, switch: 1, supervisor: 1, module: 1, filter: 1,
    led: 2, button: 2, display: 2,
    region: 0,          // regions are containers the author drew; they stay on top
    chassis: -1,        // the device itself is always the first row
  };
  function tierOf(e) {
    const c = e.dataset.class || '';
    return c in TIER ? TIER[c] : 3;
  }
  // WHAT A BLOCK IS FOR, which is the one thing data-class cannot say. A PSU bay,
  // a fan bay and a line-card bay are all class `bay` - the same hole with a
  // module in it - so ranking by class left the order to however the placements
  // happened to be written, and the C40G opened with its power supplies while the
  // AGR420 opened with its air filters.
  //
  // `management` is its own rank rather than part of `traffic` because on five
  // devices the management block is written FIRST in the manifest; folding it in
  // with the ports still opened the tree with a console socket. Within a rank,
  // document order stands - it already reads correctly, which is why the Edgecore
  // switches were right all along and needed nothing.
  // `marking` is printing, and it is last on purpose. It is not `indicator` -
  // a lamp reports a changing state, a legend never changes - and it is not
  // `furniture` either, because furniture is what you neither connect to nor
  // read, and reading is the whole job of a legend.
  // `fabric` ranks WITH traffic: on a distributed chassis the interconnect
  // ports are the other half of why the box exists, and on a fabric box they are
  // all of it. The group's document order places them within the rank.
  const ROLE = {traffic: 0, fabric: 0, management: 1, service: 2, indicator: 3,
                furniture: 4, marking: 5};
  function roleOf(e) {
    const r = e && e.dataset.groupRole;
    return r in ROLE ? ROLE[r] : 0;
  }
  function relPos(e) {
    const v = e.dataset.relPos;
    return v === undefined ? Number.POSITIVE_INFINITY : +v;
  }
  function cmpNode(a, b) {
    return tierOf(a.el) - tierOf(b.el)
        || (a.el.dataset.group || '~').localeCompare(b.el.dataset.group || '~')
        || relPos(a.el) - relPos(b.el)
        || a.path.localeCompare(b.path, undefined, {numeric: true});
  }

  // Fold a flat list into one row per data-group. Groups were always in the data
  // - the renderer has emitted data-group for a long time - the tree just never
  // read them, so 118 placements became 118 rows.
  function groupNodes(list, atRoot = true) {
    const out = [], seen = new Map();
    for (const n of list.sort(cmpNode)) {
      const g = n.el.dataset.group;
      if (!g) { out.push(n); continue; }
      if (!seen.has(g)) {
        const head = {path: `${n.path.slice(0, n.path.lastIndexOf('/') + 1)}${g}`,
                      el: null, kids: [], group: g, tier: tierOf(n.el),
                      role: roleOf(n.el),
                      doc: n.el.__docIdx ?? Infinity};
        seen.set(g, head); out.push(head);
      }
      const head = seen.get(g);
      head.kids.push(n);
      head.doc = Math.min(head.doc, n.el.__docIdx ?? Infinity);
    }
    const docOf = x => x.doc ?? x.el?.__docIdx ?? Infinity;
    const ordered = out.sort((a, b) => (a.tier ?? tierOf(a.el)) - (b.tier ?? tierOf(b.el))
                                     || (a.role ?? roleOf(a.el)) - (b.role ?? roleOf(b.el))
                                     || docOf(a) - docOf(b));
    // A HEADING THAT NAMES ONE ROW EARNS NOTHING. Nested under the thing it
    // belongs to, `sfp28-leds > led-p1` says what `led-p1` already said and
    // charges a fold and a level of indent to say it. On the AS7326-56X that was
    // 48 such headings over one lamp each - and, on the same device, a second and
    // third `mgmt` heading over a single management lamp on each of two ports.
    // That is the SAME "why is this group listed three times" the chassis lamps
    // were reported for, arriving from nesting rather than from parenting.
    //
    // At the ROOT a one-member group still earns its row, because nothing else up
    // there says what category it is: `grounding 1` and `doors 1` are the only
    // word the tree ever offers for those. Under a parent, the parent is that word.
    return atRoot ? ordered
                  : ordered.map(n => (!n.el && n.kids.length === 1) ? n.kids[0] : n);
  }

  // WHAT IS OFF, SAID ONCE, WHERE IT CAN BE SEEN. Thirteen controls on one C40G
  // face is enough that a struck-through row scrolls out of sight and a viewer
  // forgets a cover is off - which is the same wrong picture the cover was hiding.
  // The chip is absent when nothing is pulled rather than reading "0 removed",
  // and it restores on click, so the indication and the way back are one control.
  function refreshPulled() {
    const off = pulledPaths();
    const n = off.length;
    el.pulled.hidden = !n;
    el.pulled.textContent = `\u27f2 ${n} removed`;
    el.pulled.title = n === 1 ? 'one part is off - click to put it back'
                              : `${n} parts are off - click to put them all back`;
  }

  function restoreAllPulled() {
    if (!state.svg) return;
    for (const e of pulledEls()) e.removeAttribute('data-portrayal-pulled');
    if (state.autoPulled) state.autoPulled.clear();
    for (const r of el.tree.querySelectorAll('.node.pulled')) r.classList.remove('pulled');
    refreshPulled();
    emit('pulled', {paths: []});
  }

  function renderTree(roots, {clear = true, heading = null} = {}) {
    const box = el.tree;
    if (clear) box.innerHTML = '';
    // a face's section in a merged tree: a fold row like a group's, so the six
    // sections read the way the groups inside them already do
    if (heading) {
      const row = document.createElement('div');
      row.className = 'node grp face';
      row.innerHTML = `<span class="tw">▾</span><span class="nm">${heading}</span>`
        + `<span class="cls">${roots.length}</span>`;
      box.appendChild(row);
    }
    // `fold` is true for a fresh list and false for a group's own children: those
    // all carry the same data-group, so folding them again would build the same
    // head again, and again. That is the crash the first version of this had.
    const draw = (list, into, depth, fold = true) => {
      for (const n of (fold ? groupNodes(list, depth === 0) : list.sort(cmpNode))) {
        const row = document.createElement('div');
        row.className = 'node';
        // a group row is a fold, not a thing - it has no element and selects nothing
        if (!n.el) {
          row.classList.add('grp');
          row.innerHTML = `<span class="tw">▾</span>`
            + `<span class="nm">${n.group}</span>`
            + `<span class="cls">${n.kids.length}</span>`;
          into.appendChild(row);
          const kids = document.createElement('div');
          // PRINTING STARTS CLOSED. Every other group at the root is what the
          // device IS and should be in front of you; a legend block annotates
          // that, and the AS5912-54X has 58 marks claiming no owner, which
          // expanded pushes the ports off the screen to show you the words
          // printed next to them. Open on request, not by default.
          const shut = n.role === ROLE.marking;
          kids.className = 'kids' + (shut ? ' hid' : '');
          if (shut) row.querySelector('.tw').textContent = '▸';
          into.appendChild(kids);
          row.onclick = () => {
            kids.classList.toggle('hid');
            row.querySelector('.tw').textContent = kids.classList.contains('hid') ? '▸' : '▾';
          };
          draw(n.kids, kids, depth + 1, false);
          continue;
        }
        row.dataset.path = n.path;
        const cls = n.el.dataset.class || '';
        const isBay = cls === 'bay';
        const occupied = isBay ? !!n.el.querySelector('[data-ref]') : true;
        if (isBay && !occupied) row.classList.add('empty');
        const xref = xrefOf(n.el);
        row.innerHTML = `<span class="tw">${n.kids.length ? '▸' : ''}</span>`
          + `<span class="nm">${labelFor(n)}${isBay && !occupied ? ' — open' : ''}</span>`
          + (xref.length ? `<span class="xref" title="in another view of this device">`
                           + `→ ${xref.join(', ')}</span>` : '')
          + `<span class="cls">${cls}</span>`;
        // `behaviour` already says whether this part comes out and how - `mounts`
        // for a bolted cover, `fills` for a module, `occupies` for an optic. A part
        // that says nothing does not come out, so it gets no control.
        const behaviour = n.el.dataset.behaviour;
        if (behaviour) {
          const pull = document.createElement('span');
          pull.className = 'pull';
          pull.textContent = '\u25c9';
          // A COVER AND A MODULE COME OFF FOR DIFFERENT REASONS, and `behaviour`
          // already knows which this is. Taking a filter cover off to look behind
          // it and unseating a line card are not the same intent, and a person
          // reading a tree of thirteen of these can tell them apart by the verb.
          pull.title = behaviour === 'mounts' ? 'take off this cover to see behind it'
                                              : 'unseat this module to see behind it';
          pull.onclick = ev => {
            ev.stopPropagation();
            const off = !n.el.hasAttribute('data-portrayal-pulled');
            if (off) n.el.setAttribute('data-portrayal-pulled', '');
            else n.el.removeAttribute('data-portrayal-pulled');
            row.classList.toggle('pulled', off);
            // WHAT STANDS IN A WELL COMES OUT WITH IT. A bay or a part that says
            // `in:` this one (render.py emits it as data-in) is carried by it -
            // the mid tray's four drives lift out with the tray - so they go
            // off and come back with it, in the drawing and in the tree.
            for (const w of state.svg.querySelectorAll(`[data-in="${CSS.escape(n.path)}"]`)) {
              if (off) w.setAttribute('data-portrayal-pulled', '');
              else w.removeAttribute('data-portrayal-pulled');
              const wr = el.tree.querySelector(`.node[data-path="${CSS.escape(w.dataset.path)}"]`);
              if (wr) wr.classList.toggle('pulled', off);
            }
            refreshPulled();
            // a host driving a 3D scene needs the whole set, not this one part:
            // viewer3d's setPulled takes what should be off, so a reset is []
            emit('pulled', {paths: pulledPaths()});
          };
          row.querySelector('.cls').before(pull);
        }
        into.appendChild(row);
        const kids = document.createElement('div');
        kids.className = 'kids' + (depth >= 1 ? ' hid' : '');
        into.appendChild(kids);
        if (n.kids.length) {
          row.querySelector('.tw').textContent = depth >= 1 ? '▸' : '▾';
          row.querySelector('.tw').onclick = ev => {
            ev.stopPropagation();
            kids.classList.toggle('hid');
            row.querySelector('.tw').textContent = kids.classList.contains('hid') ? '▸' : '▾';
          };
        }
        row.onclick = () => select(n.path === state.sel ? null : n.path, true);
        // a page decorates its own rows here - state chips, mark counts - rather
        // than re-walking the tree afterwards and guessing which row is which
        emit('row', row, n);
        draw(n.kids, kids, depth + 1);
      }
    };
    draw(roots, box, 0);
  }

  // ---------------------------------------------------------------- selection

  // Selection colour picker. A fixed highlight fails on some hardware - a light
  // blue halo vanishes on a blue-grey faceplate, and a yellow one would vanish on
  // a yellow chassis - so the colour is chosen by whoever is looking at it.
  const HL_KEY = 'portrayal.hl';
  const HL_SWATCHES = ['#ff2d95', '#00e676', '#ffd400', '#00d5ff', '#ff6d00', '#ffffff'];
  let hlColor = '#ff2d95';
  function setHl(c) {
    hlColor = c;
    document.documentElement.style.setProperty('--hl', c);
    try { localStorage.setItem(HL_KEY, c); } catch (e) { /* private mode */ }
    for (const sw of body.querySelectorAll('#hl .sw'))
      sw.classList.toggle('on', sw.dataset.c === c);
    const inp = body.querySelector('#hl input');
    if (inp && inp.value.toLowerCase() !== c.toLowerCase()) inp.value = c;
    emit('hl', c);
  }
  (function mountHl() {
    const host = $('#hl');
    let cur = hlColor;
    try { cur = localStorage.getItem(HL_KEY) || cur; } catch (e) { /* ignore */ }
    for (const c of HL_SWATCHES) {
      const b = document.createElement('span');
      b.className = 'sw'; b.dataset.c = c; b.style.background = c;
      b.title = c;
      b.onclick = () => setHl(c);
      host.appendChild(b);
    }
    const inp = document.createElement('input');
    inp.type = 'color'; inp.title = 'custom';
    inp.oninput = () => setHl(inp.value);
    host.appendChild(inp);
    setHl(cur);
  })();

  // Stage background. The same argument as the selection colour, from the
  // other side: a near-black stage suits a silver chassis and swallows a black
  // one - the MaiaEdge PBC-2000's face is #1f2226 on a #101214 stage. So the
  // backdrop is chosen by whoever is looking, remembered, and announced so a
  // 3D view beside the drawing can follow it. Black is the stage as it was.
  const STAGE_KEY = 'portrayal.stage';
  const STAGE_SWATCHES = [['#ffffff', 'white'], ['#c5c9ce', 'light grey'],
                          ['#3b3f45', 'dark grey'], ['#101214', 'black']];
  let stageColor = '#101214';
  function setStage(c) {
    stageColor = c;
    document.documentElement.style.setProperty('--stage', c);
    try { localStorage.setItem(STAGE_KEY, c); } catch (e) { /* private mode */ }
    for (const sw of body.querySelectorAll('#stagebg .sw'))
      sw.classList.toggle('on', sw.dataset.c === c);
    emit('stage', c);
  }
  (function mountStage() {
    const host = $('#stagebg');
    if (!host) return;
    let cur = stageColor;
    try { cur = localStorage.getItem(STAGE_KEY) || cur; } catch (e) { /* ignore */ }
    for (const [c, name] of STAGE_SWATCHES) {
      const b = document.createElement('span');
      b.className = 'sw'; b.dataset.c = c; b.style.background = c;
      b.title = `${name} background`;
      b.onclick = () => setStage(c);
      host.appendChild(b);
    }
    setStage(cur);
  })();

  let halo = null;
  // ── what is over a part, and taking it off to see the part ───────────────
  // Every face the shell holds, mounted or not - a pull on the lid is a fact
  // about the device, not about which drawing happens to be on screen.
  function faceDocs() {
    return [state.svg, ...Object.values(state.faces || {})]
      .filter((d, i, a) => d && a.indexOf(d) === i);
  }
  function elOf(path) {
    const q = `[data-path="${CSS.escape(path)}"]`;
    for (const d of faceDocs()) { const e = d.querySelector(q); if (e) return e; }
    return null;
  }
  // THE MODULE A PATH IS IN, as components.json knows it. The front draws it
  // with its ref; the rear draws only a projection, whose ref sits on the
  // cutout it is seen through (render.py `data-rear-ref`, kept by swaps).
  function moduleEntry(module) {
    if (!module) return null;
    const drawn = elOf(module)?.dataset.ref;
    const bay = module.slice(0, module.lastIndexOf('/module'));
    const seen = drawn ? null : faceDocs().map(d => d.querySelector(
      `[data-rear-of="${CSS.escape(bay)}"][data-rear-ref]`)).find(Boolean);
    const ref = (drawn || seen?.dataset.rearRef || '').split(':')[0];
    return ref ? compByRef(ref) : null;
  }
  function pulledEls() { return faceDocs().flatMap(d => [...d.querySelectorAll('[data-portrayal-pulled]')]); }
  function pulledPaths() { return pulledEls().map(e => e.dataset.path).filter(Boolean); }
  function isPulled(path) { return !!elOf(path)?.hasAttribute('data-portrayal-pulled'); }

  // WHAT LIES OVER A PART, from two things the drawing DECLARES and nothing it
  // does not. `data-under` on a part is the schema's `under:` - the ids that
  // lie over it, the shroud naming the lid that closes over it. `data-for` on
  // a cover is what it hides - the bezel naming its twenty-four drives. Walked
  // transitively, so a heatsink under a shroud under a lid names both. Boxes
  // are not consulted: two parts whose boxes overlap are not thereby stacked,
  // and guessing that once turned every click on the front into "bezel".
  function over(path) {
    const out = new Set(), seen = new Set();
    // ONLY WHAT THE TREE WOULD LET YOU PULL is taken off. The system board is
    // walked THROUGH - what is over it is over the DIMMs seated in it - but a
    // board is not a cover and hiding it would be a hole, not a reveal.
    const found = o => { if (elOf(o)?.dataset.behaviour) out.add(o); visit(o); };
    const visit = p => {
      if (!p || seen.has(p)) return;
      seen.add(p);
      const e = elOf(p);
      if (!e) return;
      // declared on the part: the ids that lie over it (schema `under:`)
      for (const o of (e.dataset.under || '').split(/\s+/).filter(Boolean)) found(o);
      // NOT the well it sits in. A well's `under:` names everything standing
      // in it - the board lists the heatsinks beside the DIMMs as well as the
      // shroud over them - and the schema cannot tell a neighbour from a lid.
      // Reading it as "over the contents" pulled heatsink-2 to reveal
      // heatsink-1. What lies over a part is what the PART declares.
      // declared on a cover: what it hides (the bezel and its drives)
      const doc = e.ownerSVGElement || e.closest('svg');
      // - and NOT an occupant, which is `for` its host too but sits in it,
      // not over it (see liesOver in swap.js)
      for (const c of doc.querySelectorAll('[data-behaviour][data-for]'))
        if (liesOver(c, p)) found(c.dataset.path);
    };
    visit(path);
    if (path.includes('/')) visit(path.split('/')[0]);   // a port is under what its module is under
    out.delete(path);
    return [...out];
  }

  // Take parts off or put them back by path, the way the tree's control does,
  // so a host driving a scene hears about it the same way.
  function setPulled(paths, on) {
    let changed = false;
    for (const p of paths) {
      const e = elOf(p);
      if (!e || e.hasAttribute('data-portrayal-pulled') === on) continue;
      if (on) e.setAttribute('data-portrayal-pulled', ''); else e.removeAttribute('data-portrayal-pulled');
      el.tree.querySelector(`.node[data-path="${CSS.escape(p)}"]`)?.classList.toggle('pulled', on);
      changed = true;
    }
    if (!changed) return;
    refreshPulled();
    emit('pulled', {paths: pulledPaths()});
  }

  // REVEAL WHAT YOU SELECTED. Selecting a DIMM under the lid and being shown
  // the lid is a selection you cannot see, so whatever is declared to lie over
  // the selection comes off, and goes back when the selection moves on. Only
  // covers this took off are put back: one the reader pulled by hand stays
  // off, because that was their decision and not this function's.
  function reveal(path) {
    state.autoPulled = state.autoPulled || new Set();
    // AND THE PART ITSELF IS SHOWN. Selecting something you took off - the lid,
    // a module, a port on a pulled module - is a selection of a thing that is
    // not drawn, which is nothing to look at. So a pulled selection, or a
    // pulled ancestor of it, goes back on. That includes one pulled by hand:
    // the reader's later decision was to select it.
    if (path) {
      const back = pulledEls().map(e => e.dataset.path)
        .filter(p => p && (path === p || path.startsWith(p + '/')));
      if (back.length) { for (const p of back) state.autoPulled.delete(p); setPulled(back, false); }
    }
    const need = new Set(path ? over(path) : []);
    const back = [...state.autoPulled].filter(p => !need.has(p));
    const off = [...need].filter(p => !state.autoPulled.has(p) && !isPulled(p));
    for (const p of back) state.autoPulled.delete(p);
    for (const p of off) state.autoPulled.add(p);
    if (back.length) setPulled(back, false);
    if (off.length) setPulled(off, true);
  }

  // A BOX AROUND A PART, in the mounted drawing's root coordinates. getBBox is
  // in the element's OWN coordinate system and the ring is appended to the
  // root, so the box has to be carried through every transform between them
  // or it lands wherever that offset happens to point - which for a
  // bay-mounted port is several slots away. `pad` is in root units.
  function ringAround(target, cls, pad) {
    // getScreenCTM is null for a target that is not actually rendered (e.g.
    // display:none), which a pulled-away part can be even while its element
    // is still in the DOM - draw no ring rather than crash on a null CTM.
    const tm = target.getScreenCTM();
    if (!tm) return null;
    const b = target.getBBox();
    const m = state.svg.getScreenCTM().inverse().multiply(tm);
    const pt = (x, y) => ({x: m.a*x + m.c*y + m.e, y: m.b*x + m.d*y + m.f});
    const cs = [pt(b.x, b.y), pt(b.x + b.width, b.y),
                pt(b.x, b.y + b.height), pt(b.x + b.width, b.y + b.height)];
    const xs = cs.map(c => c.x), ys = cs.map(c => c.y);
    const r = document.createElementNS(NS, 'rect');
    r.setAttribute('class', cls);
    r._box = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
    padRing(r, pad);
    state.svg.appendChild(r);
    return r;
  }
  function padRing(r, pad) {
    const [x0, y0, x1, y1] = r._box;
    r.setAttribute('x', x0 - pad); r.setAttribute('y', y0 - pad);
    r.setAttribute('width', x1 - x0 + 2 * pad);
    r.setAttribute('height', y1 - y0 + 2 * pad);
  }
  // A FAR RING KEEPS ITS SCREEN SIZE AT ANY ZOOM: 4 px clear of the part, a
  // 1.4 px stroke, 3/2 px dashes. Set once in drawing units, the ring grew
  // with every wheel step until it boxed half the ferrule. `s` is screen px
  // per drawing unit, the stage's CSS zoom included (getScreenCTM has it).
  function screenScale() {
    const ctm = state.svg?.getScreenCTM();
    return ctm ? (Math.hypot(ctm.a, ctm.b) || 1) : null;
  }
  function sizeFarRing(r, s) {
    padRing(r, 4 / s);
    r.style.strokeWidth = String(1.4 / s);
    r.style.strokeDasharray = `${3 / s} ${2 / s}`;
  }
  function padFarRings() {
    if (!farHalos.length) return;
    const s = screenScale();
    if (s) for (const r of farHalos) sizeFarRing(r, s);
  }
  function clearHalos() {
    if (halo) { halo.remove(); halo = null; }
    for (const r of farHalos) r.remove();
    farHalos = [];
  }
  // open every fold a row sits in, so the row can be seen
  function openRow(row) {
    for (let p = row.parentElement; p && p !== el.tree; p = p.parentElement)
      if (p.classList?.contains('kids') && p.classList.contains('hid')) {
        p.classList.remove('hid');
        const tw = p.previousElementSibling?.querySelector('.tw');
        if (tw?.textContent) tw.textContent = '▾';
      }
  }
  // THE SELECTED ROW AND ITS FIBRE'S FAR ROWS, marked on whatever tree is
  // drawn now. Every rebuild draws fresh rows that know nothing of either,
  // which is how a 2D to 3D switch used to lose both highlights.
  function markRows({open = false} = {}) {
    const far = state.far || [];
    for (const r of el.tree.querySelectorAll('.node')) {
      const sel = state.sel != null && r.dataset.path === state.sel;
      const lit = far.includes(r.dataset.path);
      r.classList.toggle('sel', sel);
      r.classList.toggle('linked', lit);
      if (open && (sel || lit)) openRow(r);
    }
  }

  function select(path, fromTree) {
    state.sel = path;
    reveal(path);
    for (const r of el.tree.querySelectorAll('.node')) r.classList.toggle('sel', r.dataset.path === path);
    const q = `[data-path="${CSS.escape(path)}"]`;
    const qo = `[data-of="${CSS.escape(path)}"]`;
    // the part where it is drawn as a part; failing that, as a projection - a
    // cassette's rear MTP is drawn nowhere else, and is still something to point at
    const target = path == null ? null
      : (state.svg?.querySelector(q)
         || Object.values(state.faces || {}).map(f => f.querySelector(q)).find(Boolean)
         || state.svg?.querySelector(qo)
         || Object.values(state.faces || {}).map(f => f.querySelector(qo)).find(Boolean)
         || null);
    // THE SAME PART ON ANOTHER FACE: a projection carries `data-of` naming
    // the seated part, so selecting the part marks its projections too, and
    // clicking a projection selects the part it is of (see the hit test).
    for (const d of faceDocs()) {
      for (const e of d.querySelectorAll('[data-portrayal-selected]')) e.removeAttribute('data-portrayal-selected');
      if (path != null) for (const e of d.querySelectorAll(qo)) e.setAttribute('data-portrayal-selected', '');
    }
    // THE OTHER END OF A FIBRE is marked on every face, and its row lit. A
    // splitter's common end has several (optical.js farPath returns an array
    // for it), so `far` is always a list - empty when the path is no fibre.
    const entry = path && moduleEntry(moduleOf(path));
    const fib = entry && fibreOf(path, entry, compByRef);
    const far = fib ? [].concat(farPath(fib.module, entry, fib.endpoint) || []).filter(Boolean) : [];
    const qf = far.map(p => `[data-path="${CSS.escape(p)}"],[data-of="${CSS.escape(p)}"]`).join(',');
    for (const d of faceDocs()) {
      for (const e of d.querySelectorAll('[data-portrayal-linked]')) e.removeAttribute('data-portrayal-linked');
      if (qf) for (const e of d.querySelectorAll(qf)) e.setAttribute('data-portrayal-linked', '');
    }
    state.far = far;
    // lit and unfolded, but not scrolled to: the selected row keeps the scroll
    for (const r of el.tree.querySelectorAll('.node'))
      if (r.classList.toggle('linked', far.includes(r.dataset.path))) openRow(r);
    clearHalos();
    // getScreenCTM is null while the SVG is hidden, which is exactly what a page
    // showing a 3D stage instead has done to it. Selection still stands; only
    // the halo waits until the drawing is on screen again.
    // A region that records no extent gets NO HALO, because its rect is 0x0 and
    // the halo would be a degenerate box the user cannot see - selecting such a
    // region appeared to do nothing at all. Everything else about selection still
    // happens: the row highlights, the tree scrolls, the inspector explains why
    // there is nothing to point at.
    const noExtent = target?.dataset.extent === 'none';
    // the halo is drawn in the mounted SVG, so only for a target that is in it
    const ctm = state.svg?.getScreenCTM();
    if (target && !noExtent && state.svg.contains(target) && ctm)
      halo = ringAround(target, 'halo pulse', 0.6);
    // THE FAR END, where the mounted drawing has it: the part itself, else a
    // projection of it. Padded by 4 screen px (sizeFarRing), so a fibre dot a
    // fraction of a millimetre across still gets a ring the eye can find.
    if (ctm) {
      for (const p of far) {
        const t = state.svg.querySelector(`[data-path="${CSS.escape(p)}"]`)
               || state.svg.querySelector(`[data-of="${CSS.escape(p)}"]`);
        // A far end hidden inside a pulled-out part (display:none, see the
        // CSS rule) has no screen box to ring - skip it rather than let
        // ringAround hand back nothing to push.
        if (t && t.dataset.extent !== 'none' && !t.closest('[data-portrayal-pulled]')) {
          const ring = ringAround(t, 'halo linked', 0);
          if (ring) farHalos.push(ring);
        }
      }
      padFarRings();
    }
    if (!fromTree) {
      const row = [...el.tree.querySelectorAll('.node')].find(r => r.dataset.path === path);
      if (row) {
        openRow(row);
        row.scrollIntoView({block: 'center'});
      }
    }
    inspect(path, target);
    emit('select', path, target, fromTree);
  }

  // ---------------------------------------------------------------- inspector

  function inspect(path, e) {
    const box = el.inspect;
    const cls = e?.dataset.class || '';
    // a page may claim the inspector for a path of its own - the About panel is
    // the Explorer doing exactly that with the chassis row
    if (emit('inspect', {path, el: e, box, cls}).some(Boolean)) return;
    if (!e) { box.innerHTML = ''; return; }
    const ref = e.dataset.ref || e.querySelector('[data-ref]')?.dataset.ref;
    const bay = bayFor(path);

    let html = `<h2>${cls || 'node'}</h2><div class="row"><span>path</span><code>${path}</code></div>`;
    // WHAT THE CHOSEN NOS CALLS IT (#712). A listing names the device's own
    // ports, so only a port at the top of the drawing is looked up - a port on
    // a seated module has a path of its own and no listing rule reaches it.
    // Where the listing does not name the port, say so and why, never guess.
    const nos = cls === 'port' && !path.includes('/')
      ? nosNameFor(state.listing && LISTINGS[state.listing], path) : null;
    if (nos?.name) {
      html += `<div class="row"><span>${esc(nos.vendor)} name</span><code>${esc(nos.name)}</code></div>`;
      if (nos.note) html += `<div class="row"><span>breakout</span>${esc(nos.note.replace(/^Breakout: /, ''))}</div>`;
    } else if (nos) {
      html += `<div class="row" style="color:var(--dim, #8d939a)">${esc(nos.vendor)} name not stated`
            + (nos.gap ? ` &mdash; see the listing's <code>${esc(nos.gap)}</code> gap` : '') + `</div>`;
    }
    for (const to of state.far || [])
      html += `<div class="row"><span>fibre to</span><a href="#" data-go="${esc(to)}"><code>${esc(to)}</code></a></div>`;
    if (ref) html += `<div class="row"><span>component</span><code>${ref.split(':')[0]}</code></div>`;

    // Why nothing lit up. A region is allowed to name a part of the device that
    // the manifest has no box for - "front air intake" is a real thing to say
    // and there is no rectangle for it - and saying so is better than a silent
    // no-op that reads as a broken viewer.
    if (e.dataset.extent === 'none')
      html += `<div class="row" style="color:var(--warn)">no extent recorded &mdash; `
            + `this region names a part of the device but the manifest gives it `
            + `no box and no members to derive one from, so there is nothing to `
            + `highlight</div>`;
    else if (e.dataset.extent === 'derived')
      html += `<div class="row"><span>extent</span>derived from members</div>`;
    if (e.dataset.members)
      html += `<div class="row"><span>members</span><code>${e.dataset.members}</code></div>`;

    const cage = cageFor(path);
    if (bay) {
      const cur = (state.cfgBays?.[bay.id]) ?? bay.default ?? '';
      const opts = ['<option value="">— open —</option>']
        .concat(bay.accepts.map(a => `<option value="${a}"${a === cur ? ' selected' : ''}>${a}</option>`));
      html += `<div class="row"><span>occupant</span><select id="occ">${opts.join('')}</select></div>`;
      if (!bay.accepts.length)
        html += `<div class="row" style="color:var(--warn)">no component modelled for this slot</div>`;
    }
    // THE OPTIC IN A CAGE, offered exactly as a module in a bay is. The current
    // value is `cfgOccupants`, which is reset from THIS configuration's
    // `configs[].occupants` - never `cage.occupant`, which is only the DEFAULT
    // configuration's answer and would show another configuration's optic.
    //
    // A SLOT THAT SHIPS SOMETHING (B3) holds its `default` until the reader
    // or the configuration says otherwise, so that is its current value when
    // the state has no entry; the option it ships is marked "(ships with)"
    // (swap.js `slotOptions`). A connector slot says so in its label.
    if (cage) {
      const cur = Object.prototype.hasOwnProperty.call(state.cfgOccupants || {}, cage.id)
        ? state.cfgOccupants[cage.id] ?? '' : cage.default ?? '';
      const accepts = cage.accepts || [];
      const opts = slotOptions(cage, cur).map(o =>
        `<option value="${esc(o.value)}"${o.selected ? ' selected' : ''}>${esc(o.label)}</option>`);
      const label = cage.kind === 'connector' ? 'connector' : 'optic';
      html += `<div class="row"><span>${label}</span><select id="optic" data-cage="${esc(cage.id)}">${opts.join('')}</select></div>`;
      if (cage.key && cage.key !== cage.id)
        html += `<div class="row"><span>key</span><code>${esc(cage.key)}</code></div>`;
      if (!accepts.length)
        html += `<div class="row" style="color:var(--warn)">no generic modelled for this cage's family yet</div>`;
      // WHY A CHOSEN OPTIC IS NOT THERE, said where the choice was made. A
      // refusal (swap.js `refusalReason`) leaves the cage empty; a failed load
      // leaves it holding what it held, which the select above now shows.
      const no = state.refused?.[cage.id];
      const why = {
        'mirror': 'this cage is mirrored, and the build refuses to seat an '
                + 'optic into a mirrored cage',
        'group-states': "this cage's group carries lamp states, which the build "
                      + 'applies to a seated optic and the kit does not yet',
      };
      if (no)
        html += `<div class="row" style="color:var(--warn)">${esc(no)} was not seated &mdash; `
              + `${why[refusalReason(cage)] || 'the kit does not seat into this cage'}, `
              + `so it is left empty</div>`;
      const lost = state.failed?.[cage.id];
      if (lost)
        html += `<div class="row" style="color:var(--warn)">${esc(lost)} was not seated &mdash; `
              + `its drawing did not load, so the cage keeps `
              + `${cur ? esc(cur) : 'nothing'}</div>`;
    }
    // WHAT IS CHAINED ON IT (#611). A plug in this slot that takes a boot is
    // a slot at its own path (swap.js chainedSlots), offered here beside the
    // slot it sits in - a click on the plug still names the bore, and the
    // boot is chosen without having to find it first. Its current value is
    // the state's, else what the build seated, as the slot's own is.
    const chain = cage ? cagesOnFace().find(c => c.chained && c.id === `${cage.id}-occupant`) : null;
    if (chain) {
      const cur = Object.prototype.hasOwnProperty.call(state.cfgOccupants || {}, chain.id)
        ? state.cfgOccupants[chain.id] ?? '' : occupantRef(state.svg, chain) ?? chain.default ?? '';
      const opts = slotOptions(chain, cur).map(o =>
        `<option value="${esc(o.value)}"${o.selected ? ' selected' : ''}>${esc(o.label)}</option>`);
      html += `<div class="row"><span>on it</span><select id="chain" data-cage="${esc(chain.id)}">${opts.join('')}</select></div>`;
    }
    if (ref) {
      const c = compByRef(ref.split(':')[0].split('@')[0] + '@' + ref.split('@')[1].split(':')[0]);
      if (c) html += `<div class="row"><button id="open">Open module ↗</button></div>`;
    }
    box.innerHTML = html;

    const occ = box.querySelector('#occ');
    if (occ) occ.onchange = () => swapBay(path, occ.value);
    const optic = box.querySelector('#optic');
    if (optic) optic.onchange = () => swapCage(optic.dataset.cage, optic.value);
    const onIt = box.querySelector('#chain');
    if (onIt) onIt.onchange = () => swapCage(onIt.dataset.cage, onIt.value);
    const open = box.querySelector('#open');
    if (open) open.onclick = () => openModule(ref.split(':')[0]);
    for (const a of box.querySelectorAll('[data-go]'))
      a.addEventListener('click', ev => { ev.preventDefault(); goTo(ev.currentTarget.dataset.go); });
  }

  // FOLLOW A FIBRE to its far end: select it, switching view when that end is
  // drawn only on another face and the tree is not merged (a merged tree
  // already lists every face). The faces not on screen are fetched first if
  // they are not held yet, or a rear end would never be found from the front.
  async function goTo(to) {
    const q = `[data-path="${CSS.escape(to)}"],[data-of="${CSS.escape(to)}"]`;
    const find = () => state.svg?.querySelector(q) ? state.view
      : Object.entries(state.faces || {}).find(([, d]) => d.querySelector(q))?.[0];
    let onView = find();
    if (!onView && !state.module) { await loadFaces().catch(() => {}); onView = find(); }
    if (onView && onView !== state.view && !state.merge) {
      state.view = onView; el.view.value = onView;
      await loadStage();
    }
    select(to);
  }

  // Swapping is done in the DOM, not by rebuilding: fetch the component's compiled
  // skin and drop it into the bay at the bay's own origin.
  //
  // THE SURGERY LIVES IN swap.js, not here, because viewer3d.js needs the identical
  // operation on the fetched face text before it extracts relief from it - the 3D
  // scene is built entirely out of that text, so a swap that only touched this DOM
  // was invisible in 3D on every device. Two copies of `rename` and `bayTransform`
  // would each have been right the day they were written. So a bay goes through
  // `applyOverrides` and a cage through `applyOccupantOverrides` with a
  // one-entry map - the very functions viewer3d applies the whole map with.
  //
  // The component's skin, as those functions ask for it: {comp, text}, or null
  // for a ref that names nothing (a hand-edited `swap=` can say anything).
  //
  // NO `cache: 'no-store'`, for the reason dist.js gives about the JSON and
  // relief.js now gives about the face drawings: the flag kept a rebuilt dist
  // from going stale in development and cost every visitor a re-download of
  // every drawing on every page load, forever. Hard-reload is the development
  // tool for that; a permanent header is not.
  //
  // These fetches are still NOT memoised - they do not go through relief.js's
  // SVG_CACHE - so seating the same module twice in one page still asks twice.
  // Routing them through svgSource would fix that and would also subject them to
  // the runtime override map, which is a behaviour change rather than a caching
  // one, so it is left alone here.
  async function loadSkin(ref) {
    let c = null;
    try { c = compByRef(ref); } catch (e) { return null; }   // not ns/name@major
    if (!c) return null;
    const skin = c.skins?.includes('default') ? 'default' : c.skins?.[0];
    const r = await fetch(distAt(`components/${c.ns}--${c.name}--${c.major}--${skin}.svg`));
    return r.ok ? {comp: c, text: await r.text()} : null;
  }

  // A CARD REPLACED OR EMPTIED TAKES ITS OPTICS WITH IT (#484 R5): every entry
  // keyed under the bay - a card cage's optic, a nested bay's module - leaves
  // the state, so it leaves `swap=` and the 3D override map with it, which are
  // both read from the state. The rule is swap.js's `pruneCarrier`. The card
  // that goes in is a fresh seat of its component with nothing in its cages,
  // and when it is the BUILD's own card no swap names it at all, so the optics
  // the configuration put in it are recorded as emptied, and the modules it
  // put in the card's own bays as the defaults a fresh seat holds there
  // (swap.js's `freshBaysUnder`) - or 3D, handed nothing, would still show them.
  function dropUnder(key, ref) {
    const cfg = (state.meta?.configs || []).find(c => c.name === state.cfg);
    const cb = builtBays(cfg);
    const builtRef = Object.prototype.hasOwnProperty.call(cb, key) ? cb[key] || null
      : bayFor(key)?.default ?? null;
    const again = ref && ref === builtRef;
    const rebuilt = again ? builtOccOf(cfg) : {};
    const fresh = again ? freshBaysUnder(cfg, key, ref, compByRef) : {};
    // what a fresh seat of `ref` ships in each slot under it (B3, P5): its
    // default, read with `ref` in the bay and the state's answer elsewhere
    const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
    const R = slotResolver({bays: allOf(state.meta?.bays), cages: allOf(state.meta?.cages),
      compByRef, placementRef,
      bayRef: (p, bay) => p === key ? ref : own(state.cfgBays, p) ? state.cfgBays[p]
        : own(fresh, p) ? fresh[p] : bay.default ?? null});
    const ships = k => R.entryAt(k)?.default ?? null;
    Object.assign(state, pruneCarrier(state, key, rebuilt, fresh, ships));
    // and a swap still loading under it is no longer anyone's to make: its
    // claim retired, it neither touches the drawing nor writes the state
    claim.retireUnder(key);
  }

  // AN OPTIC REPLACED OR EMPTIED TAKES ITS PLUGS WITH IT, as a card takes its
  // optics (dropUnder): every key on what the slot held -
  // `nt-a/module/qsfp-2-occupant/tx` - leaves the state (swap.js's
  // underCarrier reads `<slot>-occupant/` as it reads `<bay>/module/`). The
  // optic that goes in is a fresh seat of its skin, so when it is the
  // BUILD's own optic, what the configuration plugged into it is recorded as
  // what a fresh seat ships there - or 3D, handed nothing, would still show
  // the build's plugs.
  function dropOnSlot(key, ref, slot) {
    const cfg = (state.meta?.configs || []).find(c => c.name === state.cfg);
    const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
    const built = builtOccOf(cfg);
    const R = slotResolver({bays: allOf(state.meta?.bays), cages: allOf(state.meta?.cages),
      compByRef, placementRef,
      bayRef: (p, bay) => own(state.cfgBays, p) ? state.cfgBays[p] : bay.default ?? null,
      occRef: (p, s) => p === key ? ref : own(state.cfgOccupants, p) ? state.cfgOccupants[p]
        : own(built, p) ? built[p] : s.default ?? null});
    const builtRef = own(built, key) ? built[key] || null
      : (slot || R.entryAt(key))?.default ?? null;
    const rebuilt = ref && ref === builtRef ? built : {};
    const ships = k => R.entryAt(k)?.default ?? null;
    Object.assign(state, pruneCarrier(state, key, rebuilt, {}, ships));
    claim.retireUnder(key);
  }

  // ONE SWAP INTO THE FACE ON SCREEN, bay or cage - the single place both
  // swapBay/swapCage and a reload go through. Returns what it touched, or null
  // when `key` names nothing on this face (or `ref` is not something it
  // accepts). The state is written HERE, so the drawing, the inspector's
  // select, the URL and the 3D scene all read one answer.
  //
  // ONE CLAIM PER KEY (swap.js `seatClaims`), taken before the await and
  // checked after it - by the apply, before it touches the drawing, and here,
  // before the state is written. Two swaps of one cage in flight (a select
  // driven by the arrow keys; a view change re-seating while a swap loads)
  // used to leave both optics on the face and the state naming whichever
  // finished last. Now the later request owns the key and the earlier returns
  // null having changed nothing.
  //
  // A KEY CAN STILL BE CLAIMED ON A FACE THAT NO LONGER EXISTS: the claim
  // book is per-key, not per-face, so a config or view change that never
  // touches `key` leaves its claim untouched and `live()` alone keeps
  // answering true. `svg` is captured here too - the face this call started
  // on - and `svg === state.svg` after the await is another freshness test:
  // not just "am I still the newest claim on this key" but "is the face I am
  // about to write into still on screen". loadStage always mounts a fresh
  // element, so any reload (same view, another view, opening a module)
  // changes the identity and fails this the same way.
  //
  // THE SVG CHECK ALONE MISSES ONE WINDOW: `syncCfgBays` (a configuration
  // change) resets `cfgBays`/`cfgOccupants`/`touched` to the NEW
  // configuration's values SYNCHRONOUSLY, and only the `loadStage()` after it
  // reassigns `state.svg` - and that happens later, after its own `await
  // fetch`. A `seat()` started on the OLD configuration whose skin load
  // resolves inside that window sees `svg === state.svg` still true (the old
  // face is still on screen) and would write its ref into the NEW
  // configuration's freshly-reset objects. `cfgGen`, bumped first thing
  // inside `syncCfgBays`, closes exactly that window: it changes at the
  // instant the objects a write would land in are swapped, not when the face
  // eventually catches up. Kept alongside the svg check rather than in place
  // of it - `cfgGen` only moves on a configuration change, so it does not
  // catch a plain view change or opening a module, both of which replace
  // `state.svg` (and so must retire an in-flight write) without going through
  // `syncCfgBays` at all.
  const claim = seatClaims();
  async function seat(key, ref) {
    if (!state.svg || state.module) return null;
    ref = ref || null;
    const cage = cagesOnFace().find(c => c.id === key);
    const bay = cage ? null : bayFor(key);
    const target = cage || bay;
    if (!target || (ref && !(target.accepts || []).includes(ref))) return null;
    const svg = state.svg;
    const gen = state.cfgGen;
    const live = claim(key);
    const onFace = () => live() && svg === state.svg && gen === state.cfgGen;
    if (bay) {
      await applyOverrides(svg, [bay], {[key]: ref}, loadSkin, onFace);
      if (!onFace()) return null;
      const was = Object.prototype.hasOwnProperty.call(state.cfgBays, key)
        ? state.cfgBays[key] : bay.default ?? null;
      if ((was || null) !== ref) dropUnder(key, ref);
      state.cfgBays[key] = ref;
    } else {
      const {refused, failed} = await applyOccupantOverrides(svg, [cage], {[key]: ref}, loadSkin, onFace);
      if (!onFace()) return null;
      const held = Object.prototype.hasOwnProperty.call(state.cfgOccupants, key)
        ? state.cfgOccupants[key] : cage.default ?? null;
      delete state.refused[key];
      delete state.failed[key];
      // A REFUSED CAGE IS LEFT EMPTY (applyOccupantOverrides removed what was
      // there and seated nothing), so the state says empty too: the select, the
      // URL and the 3D scene agree with the drawing, and the inspector says why
      // rather than leaving a silent empty cage.
      if (refused.includes(key)) { state.refused[key] = ref; ref = null; }
      // A FAILED LOAD CHANGED NOTHING - the cage kept its optic - so the state
      // records what the drawing still holds, not what was asked for, and the
      // inspector says the chosen one did not load.
      else if (failed.includes(key)) {
        const was = Object.prototype.hasOwnProperty.call(state.cfgOccupants, key)
          ? state.cfgOccupants[key] : cage.default ?? null;
        state.failed[key] = ref;
        // what the drawing still holds; on a back the projection keeps no
        // ref to read it by (swap.js isOccupantOf), and it is what the state
        // said the slot held before this swap
        ref = occupantRef(svg, cage)
          ?? (cage.projection && occupantsOf(svg, cage).length ? was : null);
        console.warn(`[portrayal] ${key}: ${state.failed[key]} did not load; `
                     + `the cage keeps ${ref || 'nothing'}`);
      }
      // the occupant that left took whatever was plugged into it
      if (!failed.includes(key) && (held || null) !== ref) dropOnSlot(key, ref, cage);
      state.cfgOccupants[key] = ref;
    }
    state.touched.add(key);
    return cage ? 'cage' : 'bay';
  }

  async function swapBay(bayId, ref) {
    if (!(await seat(bayId, ref))) return;
    seatDetached({[bayId]: stateRef(bayId)}).then(refreshMerged, warnFaces);
    redrawTree();
    select(bayId, true);
    emit('change');
  }

  // The optic in a cage, as swapBay is the module in a bay: take out what the
  // cage holds and seat `ref` (or nothing, for '' / null).
  async function swapCage(cageId, ref) {
    if (!cagesOnFace().some(c => c.id === cageId)) return;
    if (!(await seat(cageId, ref))) return;
    seatDetached({[cageId]: stateRef(cageId)}).then(refreshMerged, warnFaces);
    redrawTree();
    select(cageId, true);
    emit('change');
  }

  // A FRESH FACE IS THE BUILD, and the swaps are not in it. Loading a face -
  // another view, or the same one again - fetches the compiled drawing, which
  // knows only the configuration, so every swap made since the configuration
  // loaded is seated again. Shallowest first: a nested bay exists only once
  // the carrier above it is seated. Keys this face does not have are skipped
  // here and kept, because the face that has them may be the next one shown.
  const depth = k => k.split('/module/').length;
  const byDepth = keys => [...keys].sort((a, b) => depth(a) - depth(b) || (a < b ? -1 : 1));
  // What the state holds for a key it has touched. A cage's answer is in
  // cfgOccupants and a bay's in cfgBays - every write puts a key in exactly
  // one - which also sorts a card's cage from a nested bay, whose keys look
  // alike.
  const stateRef = key => Object.prototype.hasOwnProperty.call(state.cfgOccupants, key)
    ? state.cfgOccupants[key] : state.cfgBays[key];
  async function reseat() {
    // THE FACE AND CONFIGURATION THIS RESEAT STARTED ON. `seat()`'s own
    // checks catch a change while ONE key's skin is loading, but not this:
    // each iteration's ref comes from `state.cfgOccupants`/`cfgBays`, read
    // fresh and synchronously right before the call, no await in between. If
    // a configuration change lands between iterations, `syncCfgBays` has
    // already reset those to the NEW configuration's values - and bumped
    // `cfgGen` - possibly before `state.svg` has caught up (the same window
    // `seat()`'s comment describes), so `svg` alone cannot be trusted to
    // catch it here either. Either one moving means this loop would go ahead
    // and read the NEW configuration's answer for a key from the OLD touched
    // set: undefined for a key it never touched (seat(key, null) - a
    // spurious empty of a cage the new build may have filled), or, worse,
    // another key's own value by coincidence. So the loop itself, not just
    // the call inside it, has to notice its face or configuration moved on
    // and stop - the remaining keys are for whatever reseat the new
    // config's own loadStage already ran.
    const svg = state.svg, gen = state.cfgGen;
    // A SWAPPED BAY SEEN FROM BEHIND. This face may have no bays and still
    // show one: a rear hole names the front bay whose module's back it holds
    // (render.py's `rear:`). `seat` looks for the bay on this face and so never
    // reaches it; the swapped bays are re-seated through the hole instead.
    // FIRST, before the keys (B3 Task 10b): a back's own slots - its MTP
    // bulkheads, `bay-1/module/mtp1` - are keys like any other, and they
    // must be seated into the back the state holds, not into the build's
    // back that this replaces.
    if (svg?.querySelector('[data-rear-of]')) {
      const rear = {};
      for (const key of state.touched)
        if (Object.prototype.hasOwnProperty.call(state.cfgBays, key)) rear[key] = state.cfgBays[key];
      if (Object.keys(rear).length) await applyRearOverrides(svg, rear, loadSkin, compByRef);
    }
    for (const key of byDepth(state.touched)) {
      if (svg !== state.svg || gen !== state.cfgGen) return;
      // a key a card swap pruned while this loop ran is no longer the state's
      if (!state.touched.has(key)) continue;
      await seat(key, stateRef(key));
    }
  }

  // THE SWAPS A RELOAD CARRIES (the explorer's `swap=`), taken into the state
  // and seated into the face on screen. What is taken is decided by swap.js's
  // `acceptSwaps`, BEFORE anything is written: whatever the state holds goes
  // back into `swap=` and to the 3D scene, whose applyOverrides checks no
  // accepts, so an entry the 2D face would refuse must not get as far as the
  // state. An entry is taken only when it names a bay or cage of this device
  // that exists - in any view, since the one on screen is not the only one;
  // a nested bay through what its carrier holds - and its ref is one that bay
  // or cage accepts. A link written for another device, or edited by hand,
  // cannot seat anything the inspector could never have offered.
  async function applySwaps(map) {
    const all = allOf;
    const bays = all(state.meta?.bays);
    const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
    // what this configuration BUILT at a path - the configuration's own map,
    // through builtBays (a nested key is the manifest's, not the drawing's),
    // not the state, which a swap has already moved; undefined = no answer
    const cfg = (state.meta?.configs || []).find(c => c.name === state.cfg);
    const cb = builtBays(cfg);
    const built = p => own(cb, p) ? cb[p] || null
      : bays.find(b => b.id === p)?.default ?? undefined;
    // and in each slot it keys: undefined for a slot it leaves at its default
    const bo = builtOccOf(cfg);
    const builtOcc = p => own(bo, p) ? bo[p] : undefined;
    const gate = () => acceptSwaps(map, {bays, cages: all(state.meta?.cages), built, builtOcc,
                                         compByRef, placementRef});
    let verdict = gate();
    // A SLOT ON A DEVICE PLACEMENT is found through the placement's ref, which
    // only a face that draws it can give (placementRef). The face on screen
    // is the one the link names; a key on another face - a bore swapped on
    // the front, the link written from the rear - is known once the other
    // faces are held, so they are fetched and the gate asked again.
    if (verdict.ignored.length && !state.module
        && (state.meta?.views || []).some(v => !state.faces?.[v])) {
      await loadFaces().catch(() => 0);
      verdict = gate();
    }
    const {accepted, ignored, cages} = verdict;
    // `cages` says which accepted keys are cages - a card's among them, whose
    // key looks like a nested bay's. Shallowest first (acceptSwaps' order), so
    // a card the link swaps drops what the build had under it (dropUnder)
    // BEFORE the link's own optic for that card is written.
    // A slot the link fills drops what the build plugged into it, the same
    // way (dropOnSlot) and for the same reason: reseat() seats a fresh optic.
    const cageKeys = new Set(cages);
    for (const [key, ref] of Object.entries(accepted)) {
      if (cageKeys.has(key)) {
        dropOnSlot(key, ref);
        state.cfgOccupants[key] = ref;
      } else {
        dropUnder(key, ref);
        state.cfgBays[key] = ref;
      }
      state.touched.add(key);
    }
    await reseat();
    // the faces held but not mounted take the same entries - as the state
    // now answers them, so a cage seat() refused is empty there too
    const seated = {};
    for (const key of Object.keys(accepted))
      if (state.touched.has(key)) seated[key] = stateRef(key);
    seatDetached(seated).then(refreshMerged, warnFaces);
    refreshTree();
    emit('change');
    return {ignored};
  }

  function openModule(ref) { state.module = ref; loadStage(); }

  // ---------------------------------------------------------------- loading

  // THE BAYS OF THE FACE ON SCREEN, on this configuration. The index keys
  // `bays` by view name, variant views included (`front-lff-12`), and a
  // configuration that binds a variant says so in its `views`; look the face
  // up through that or a 12-drive front reads the 24-drive bay list. `views`
  // at the top level is faces only, which is what loadFaces walks - a variant
  // has no file of its own to fetch.
  function bayView(view = state.view) {
    const c = (state.meta?.configs || []).find(c => c.name === state.cfg);
    return c?.views?.[view] || view;
  }

  // THE FACES HELD BUT NOT MOUNTED ARE SEATED TOO. loadFaces parses them from
  // the build, which knows only the configuration, and `reseat()` seats only
  // the face on screen - so the merged tree listed a cassette the reader had
  // swapped in on the rear (mounted) and its bay as "open" on the front. Each
  // detached face goes through swap.js's `seatFace`, the pass the 3D scene
  // makes on its own copy of the text: when it is loaded, with the state's
  // whole delta against the build (`swapDelta`, the map index.html hands 3D
  // and writes into `swap=`), and on every later swap, with that one entry.
  //
  // IN PLACE, NOT RE-FETCHED: a held face also carries what the reader did to
  // it - parts pulled, fields painted - and a fresh parse would drop it. The
  // ordering and the record of what each face holds are swap.js's
  // `faceQueue`; the faces it is asked about are the ones held for THIS
  // device and configuration when the job was asked for (`facesFor`).
  const faceParts = view => ({bays: state.meta?.bays?.[bayView(view)] || [],
                              cages: state.meta?.cages?.[bayView(view)] || []});
  function swapDelta() {
    return swapOverrides({
      cfg: (state.meta?.configs || []).find(c => c.name === state.cfg),
      bays: Object.values(state.meta?.bays || {}).flat(),
      cages: Object.values(state.meta?.cages || {}).flat(),
      cfgBays: state.cfgBays, cfgOccupants: state.cfgOccupants, compByRef, placementRef,
    });
  }
  const faceWork = faceQueue({
    loadSkin,
    seat: (face, view, map, skin) => seatFace(face, faceParts(view), map, skin, compByRef),
  });
  const warnFaces = err => console.warn('[portrayal] seating the faces not on screen', err);
  // only when something the tree lists changed, and without losing the
  // reader's place in it
  const refreshMerged = n => { if (n && state.merge && !state.module) redrawTree(); };

  function seatDetached(map) {
    const key = state.facesFor;
    return faceWork.swap(map, {
      live: () => state.facesFor === key,
      held: () => Object.entries(state.faces || {}).filter(([, f]) => f !== state.svg),
    });
  }

  function loadFaces() {
    if (state.module) return Promise.resolve(0);
    const key = `${state.device}.${state.cfg}`;
    if (state.facesFor !== key) { state.faces = {}; state.facesFor = key; }
    return faceWork.load(state.meta?.views || [], {
      live: () => state.facesFor === key && !state.module,
      has: view => !!state.faces[view],
      fetch: async view => {
        const r = await fetch(distAt(faceFile(state.meta, state.cfg, view)));
        if (!r.ok) return null;
        const doc = new DOMParser().parseFromString(await r.text(), 'image/svg+xml');
        return document.importNode(doc.documentElement, true);
      },
      delta: swapDelta,
      // the mounted face may have arrived for this view while it loaded
      store: (view, face) => !state.faces[view] && !!(state.faces[view] = face),
    });
  }

  // THE TREE AGAIN, WITH THE READER STILL IN IT. refreshTree draws every fold
  // as a fresh tree draws it and marks nothing selected - which is right for
  // a new device, and wrong for a redraw nobody asked for: a swap seated into
  // the other faces a moment later folded the tree shut and lost the row the
  // reader had just picked. A fold is known by its chain of labels up to its
  // face's heading, since a group's row has no path and one group name
  // recurs on every face.
  function foldKey(row) {
    const label = r => r.dataset.path || r.querySelector('.nm')?.textContent || '';
    const chain = [label(row)];
    let at = row.parentElement;
    for (; at && at !== el.tree; at = at.parentElement)
      if (at.classList.contains('kids')) chain.unshift(label(at.previousElementSibling));
    let top = row;
    while (top.parentElement && top.parentElement !== el.tree) top = top.parentElement;
    for (let h = top.previousElementSibling; h; h = h.previousElementSibling)
      if (h.classList.contains('face')) { chain.unshift(label(h)); break; }
    return chain.join('\u0000');
  }
  function redrawTree() {
    const folds = () => [...el.tree.querySelectorAll('.node')]
      .filter(r => r.nextElementSibling?.classList.contains('kids'));
    const shut = new Map(folds().map(r => [foldKey(r), r.nextElementSibling.classList.contains('hid')]));
    const top = el.tree.scrollTop;
    refreshTree();
    for (const r of folds()) {
      const k = foldKey(r);
      if (!shut.has(k)) continue;
      r.nextElementSibling.classList.toggle('hid', shut.get(k));
      const tw = r.querySelector('.tw');
      if (tw?.textContent) tw.textContent = shut.get(k) ? '▸' : '▾';
    }
    markRows();
    el.tree.scrollTop = top;
  }
  function refreshTree() {
    // `merge` is the host saying "every face is visible": one section per
    // view, the on-screen one first, each folded the way a single tree is
    if (state.merge && !state.module) {
      const views = [state.view, ...(state.meta?.views || []).filter(v => v !== state.view)];
      el.tree.innerHTML = '';
      for (const view of views) {
        const svg = state.faces?.[view];
        if (!svg) continue;
        renderTree(buildTree(svg), {clear: false, heading: view});
      }
    } else {
      renderTree(buildTree(state.svg));
    }
    // a fresh tree (a 2D/3D switch) opens onto the selection and its far
    // rows; redrawTree then puts the reader's own folds back over this
    markRows({open: true});
    refreshPulled();
  }

  async function loadStage() {
    el.svgHost.innerHTML = '';
    let file;
    if (state.module) {
      const c = compByRef(state.module);
      const skin = c.skins.includes('default') ? 'default' : c.skins[0];
      file = distAt(`components/${c.ns}--${c.name}--${c.major}--${skin}.svg`);
    } else {
      file = distAt(faceFile(state.meta, state.cfg, state.view));
    }
    const txt = await (await fetch(file)).text();
    const doc = new DOMParser().parseFromString(txt, 'image/svg+xml');
    const svg = document.importNode(doc.documentElement, true);
    el.svgHost.appendChild(svg);
    state.svg = svg;
    state.sel = null;
    state.far = [];
    farHalos = [];        // they were drawn in the drawing just replaced
    // THE OTHER FACES ARE STILL THE SAME DEVICE. In 2D one view is on screen
    // and the tree lists it; in 3D every face is on screen at once, so a
    // tree pinned to `state.view` lists a sixth of what the reader is looking
    // at. The remaining faces are fetched on request (loadFaces) and kept
    // parsed but unmounted - buildTree reads structure only, so a detached
    // document is enough - and dropped whenever the device or config changes.
    const key = `${state.device}.${state.cfg}`;
    if (state.facesFor !== key) { state.faces = {}; state.facesFor = key; }
    state.faces[state.view] = svg;
    if (!state.module) await reseat();
    // Clicking the selected thing again clears it, and clicking away from any
    // part clears it too. A selection you cannot revoke is a halo painted over
    // the hardware for the rest of the session - and on the annotate tab, one
    // that ends up in the export you were composing. Esc does the same from
    // anywhere; see below.
    svg.addEventListener('click', ev => {
      if (dragged) return;              // this click is the end of a pan
      // the nearest part - and a click on a projection is a click on the
      // part it projects. A projection drawn INSIDE a part (a cassette's back
      // in its rear cutout) is nearer than that part, so it wins; the old test
      // read the containment backwards and selected the cutout.
      const path = ownerPath(ev.target);
      select(path && path !== state.sel ? path : null, false);
    });
    fit();
    refreshTree();
    // A CONFIG CHANGE MUST NOT UN-MERGE THE TREE. loadStage drops the cached
    // faces when the key changes and re-adds only the mounted one, so a host
    // that merged in 3D would see the tree fall back to a single section
    // until it asked again. Ask on its behalf: the refresh above drew what was
    // available, and this fills in the rest as it arrives.
    if (state.merge && !state.module)
      loadFaces().then(refreshTree).catch(() => {});
    crumbs();
    el.inspect.innerHTML = '';
    el.status.textContent = state.module ? '' :
      `${(state.meta.bays[bayView()] || []).length} bays`;
    emit('load', svg);
  }

  function crumbs() {
    const c = el.crumb;
    if (state.module) {
      c.innerHTML = `<button id="back">← chassis</button> <b>${state.module}</b>`;
      c.querySelector('#back').onclick = () => { state.module = null; loadStage(); };
    } else {
      c.innerHTML = `<b>${esc(state.meta.model)}</b> · ${esc(state.cfg)} · ${esc(state.view)}`;
    }
  }

  // `want` is what a reload asks for - {config, view} off the explorer's own
  // URL - and is honoured only where this device has it; anything else falls
  // back to the device's default configuration and first view.
  async function loadDevice(name, want = {}) {
    // WHOSE BOX THIS IS goes with the box. A caller that names a listing sets
    // it; any other load keeps the current one only if it still lists this
    // device - the tab shell switching boxes must not leave "Arrcus" behind.
    if ('listing' in want) state.listing = want.listing || null;
    else if (state.listing) {
      const d = DEVICES.find(x => x.name === name);
      if (!d || LISTINGS[state.listing]?.hardware !== `${d.ns}/${d.name}`) state.listing = null;
    }
    state.device = name;
    state.module = null;
    state.meta = await j(`${name}.configs.json`);
    const has = (list, v) => v && list.includes(v);
    state.cfg = has(state.meta.configs.map(c => c.name), want.config) ? want.config : state.meta.default;
    state.view = has(state.meta.views, want.view) ? want.view : state.meta.views[0];
    el.cfg.innerHTML = state.meta.configs
      // the kind beside the name, so a reader can tell the bare chassis from a
      // SKU from an illustration without opening device.yaml (#66)
      .map(c => `<option value="${c.name}"${c.name === state.cfg ? ' selected' : ''}>${c.name}${c.kind ? ` · ${c.kind}` : ''}</option>`).join('');
    el.view.innerHTML = state.meta.views
      .map(v => `<option value="${v}"${v === state.view ? ' selected' : ''}>${v}</option>`).join('');
    if (picker && picker.value !== name) picker.value = name;
    syncCfgBays();
    emit('device', name, state.meta);
    await loadStage();
  }
  function syncCfgBays() {
    // BUMPED FIRST, before any of the objects below are replaced, so a
    // seat()/reseat() that captured the old `cfgGen` sees the mismatch no
    // matter how early after this point its continuation runs.
    state.cfgGen++;
    const c = state.meta.configs.find(c => c.name === state.cfg);
    // keyed by the drawing's path, which is what the picker looks a bay up by;
    // the manifest leaves the `/module` steps out - see swap.js's builtBays,
    // the one reading of `configs[].bays`
    state.cfgBays = builtBays(c);
    // the optics THIS configuration seats - `configs[].occupants`, not the
    // cages' own `occupant`, which is the default configuration's answer -
    // read through swap.js's `builtOccupants`, which reduces a mapping value
    // to its ref and drops a chained key that names no cage
    state.cfgOccupants = builtOccOf(c);
    state.touched = new Set();
    state.refused = {};
    state.failed = {};
    state.cfgFields = {};
  }

  el.cfg.onchange = e => { state.cfg = e.target.value; state.module = null; syncCfgBays(); loadStage(); };
  el.view.onchange = e => { state.view = e.target.value; state.module = null; loadStage(); };
  addEventListener('resize', fit);

  const ready = (async () => {
    DEVICES = DEVICES.length ? DEVICES : (await j('devices.json')).devices;
    COMPONENTS = COMPONENTS.length ? COMPONENTS : (await j('components.json')).components;
    // OPTIONAL, for a build from before listings (#677): without the file the
    // picker offers the hardware alone, which is what it always did.
    try { LISTINGS = (await j('listings.json')).listings || {}; } catch { LISTINGS = {}; }
    // the tab shell picks the device and hands it over in the query string, so
    // switching tabs keeps you on the same box. The explorer writes its own
    // configuration, view and swaps there too (index.html), so a reload lands
    // where the reader was: the device, then its configuration and view, then
    // the swaps - in that order, because which bays and cages exist depends on
    // the first two. `swap` is read RAW: it carries its own escaping (see
    // encodeSwaps in swap.js).
    const q = new URLSearchParams(location.search);
    const want = opts.device || q.get('device');
    const start = DEVICES.find(d => d.name === want)
               || DEVICES.find(d => d.name === 'c100g') || DEVICES[0];
    // Which device is the outer shell's state, and inside an iframe this header
    // must not offer a second answer to it. Opened on its own - explore.html
    // straight from the filesystem, or one of the harness pages - there is no
    // outer shell, so the page has to carry the picker itself. Same component
    // either way; only whether it is mounted differs.
    // A LISTING SURVIVES A RELOAD when it lists the device the URL names; one
    // that lists anything else is a stale link and is dropped, not honoured.
    const wantListing = opts.listing || q.get('listing');
    state.listing = start.name === want && LISTINGS[wantListing]?.hardware === `${start.ns}/${start.name}`
      ? wantListing : null;
    if (parent === window) {
      picker = createDevicePicker({mount: el.dev, devices: DEVICES, value: start.name,
                                   listings: LISTINGS, listing: state.listing,
                                   onchange: (name, {listing} = {}) => {
                                     state.listing = listing || null;
                                     // ANOTHER VENDOR'S ENTRY FOR THE BOX ON SCREEN
                                     // changes whose box it is, not what is drawn:
                                     // reloading would reset the configuration, the
                                     // view and every swap (#711 review)
                                     if (name === state.device) {
                                       if (state.sel === 'chassis') select('chassis', false);
                                       emit('change');
                                       return;
                                     }
                                     loadDevice(name, {listing: state.listing});
                                   }});
    } else {
      el.dev.hidden = true;
    }
    // READ BEFORE THE LOAD: loading announces itself, and a page that writes
    // its location on that announcement (index.html) has rewritten `swap=`
    // before the swaps are applied. And only for the device the URL named - a
    // link for a device that is not here says nothing about the fallback.
    const same = start.name === want;
    const swaps = same ? decodeSwaps(rawParam(location.search, 'swap')) : {};
    await loadDevice(start.name, same ? {config: q.get('config'), view: q.get('view')} : {});
    if (Object.keys(swaps).length) {
      const {ignored} = await applySwaps(swaps);
      if (ignored.length) console.warn('[portrayal] swaps naming nothing on', start.name, ignored);
    }
  })();

  // Esc clears the selection from anywhere. A page that binds Esc for its own
  // purposes - annotate disarms a crop with it - handles that first and this
  // never sees it, because that listener runs on the page and stops there only
  // when it has something of its own to cancel.
  addEventListener('keydown', ev => {
    if (ev.key !== 'Escape' || ev.defaultPrevented) return;
    const a = document.activeElement;
    if (a && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName)) return;
    if (state.sel != null) select(null, false);
  });

  // WRITE ON A PART in the 2D drawings: a field is a node the part declares
  // (components.json `fields`) and its skin is wired to - `data-from` for text,
  // `data-fill-from` / `data-stroke-from` for colour - and the value lands on the
  // group as `data-<key>`. `setFields('psu-1/module', {watts: '750W'})`; an empty
  // value hides a text node and puts a colour back to what was drawn. null drops
  // the part from cfgFields and restores its COLOURS as drawn; its text keeps the
  // last value written, here and in 3D alike (nothing stashes drawn text - a gap
  // that predates the colour rule). The rule is fields.js's,
  // shared with the 3D side; the host mirrors the same map into the 3D viewer's
  // setFields.
  function setFields(path, vals) {
    if (!vals) delete state.cfgFields[path];
    else state.cfgFields[path] = {...(state.cfgFields[path] || {}), ...vals};
    for (const d of faceDocs())
      for (const el of d.querySelectorAll(
          `[data-path="${CSS.escape(path)}"],[data-projection][data-of="${CSS.escape(path)}"]`))
        if (vals) paintFields(el, vals);
        else {
          unpaintFields(el);
          // a part seated INSIDE this one keeps its own fields: restoring the
          // outer part's colours reached into it, so its own are put back on
          for (const [inner, iv] of Object.entries(state.cfgFields))
            if (inner.startsWith(path + '/'))
              for (const n of el.querySelectorAll(`[data-path="${CSS.escape(inner)}"]`))
                paintFields(n, iv);
        }
    emit('fields', {path, fields: state.cfgFields[path] || null, all: state.cfgFields});
    emit('change');
  }
  function fieldsOf(ref) { return compByRef(ref)?.fields || {}; }

  return {
    state, el, ready, on, emit, setFields, fieldsOf,
    select, fit, refreshTree, loadFaces, loadDevice, loadStage, openModule, swapBay,
    swapCage, cageFor, applySwaps, swapDelta,
    over, setPulled, pulledPaths,
    compByRef, devices: () => DEVICES, components: () => COMPONENTS,
    device: () => DEVICES.find(d => d.name === state.device),
    // the chosen NOS vendor's listing, whole, or null (#709)
    listing: () => (state.listing && LISTINGS[state.listing]) || null,
    listings: () => LISTINGS,
    hl: () => hlColor,
    stage: () => stageColor,
  };
}
