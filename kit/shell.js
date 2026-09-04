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
import { seatModule } from './swap.js';
import { jdist } from './dist.js';

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
  .node.grp { color:var(--dim); text-transform:uppercase; font-size:0.68rem;
              letter-spacing:0.05em; margin-top:0.25rem; }
  .node.grp .cls { text-transform:none; letter-spacing:0; }
  #hl { display:flex; align-items:center; gap:0.25rem; }
  #hl .sw { width:0.95rem; height:0.95rem; border-radius:3px; cursor:pointer;
            border:1px solid #00000055; }
  #hl .sw.on { outline:2px solid var(--ink); outline-offset:1px; }
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
  @keyframes p { 0%,100%{ stroke-opacity:1 } 50%{ stroke-opacity:0.25 } }
`;

const SHELL_HTML = `
<header>
  <h1></h1>
  <span class="f" id="devpick"></span>
  <label class="f">config <select id="cfg"></select></label>
  <label class="f">view <select id="view"></select></label>
  <span class="f" id="hl" title="Selection colour - pick one that stands out against this chassis"></span>
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
let DEVICES = [], COMPONENTS = [];

export function createShell(opts = {}) {
  let picker = null;
  const DIST = opts.dist || '../dist';
  const body = opts.mount || document.body;
  // shared with the 3D viewer mounted in the same page - see dist.js
  const j = p => jdist(`${DIST}/${p}`);

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

  const state = {device: null, cfg: null, view: null, module: null, sel: null,
                 svg: null, meta: null, cfgBays: {}};

  const handlers = {};
  const on = (name, fn) => { (handlers[name] ||= []).push(fn); };
  const emit = (name, ...a) => (handlers[name] || []).map(fn => fn(...a));

  const compByRef = ref => {
    const [ns, rest] = ref.split('/');
    const [name, major] = rest.split('@');
    return COMPONENTS.find(c => c.ns === ns && c.name === name && c.major === 'v' + major);
  };

  // ---------------------------------------------------------------- stage

  let zoom = 1, panX = 0, panY = 0;
  // set while the pointer is panning, so the click that ends a drag does not
  // also change the selection
  let dragged = false;
  function applyTransform() {
    if (state.svg) state.svg.style.transform = `translate(${panX}px,${panY}px) scale(${zoom})`;
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
                                              px = e.clientX; py = e.clientY; dragged = false;
                                              st.setPointerCapture(e.pointerId); });
    st.addEventListener('pointermove', e => { if (!on) return;
                                              // a few pixels of travel is a tremor, not a drag; without
                                              // this every click on a part reads as a pan and never
                                              // reaches the selection handler
                                              if (Math.abs(e.clientX - px) + Math.abs(e.clientY - py) > 4)
                                                dragged = true;
                                              panX = e.clientX - sx; panY = e.clientY - sy; applyTransform(); });
    st.addEventListener('pointerup', () => { on = false; });
  })();

  // ---------------------------------------------------------------- tree

  // The compiled SVG carries the hierarchy already: every meaningful node has a
  // data-path, '/' separated. Build the tree from that rather than from the
  // contracts, so what you see listed is exactly what is drawn.
  function buildTree(root) {
    const nodes = [...root.querySelectorAll('[data-path]')];
    const byPath = new Map();
    // document order = manifest order, and the manifest is now written in the order
    // the part is made. That is a better group ordering than the alphabet: it put
    // qsfp28 (ports 4-21) ahead of qsfpdd-400g (ports 0-3) purely on spelling.
    nodes.forEach((e, i) => { if (e.__docIdx === undefined) e.__docIdx = i; });
    for (const e of nodes) {
      const path = e.dataset.path;
      if (!byPath.has(path)) byPath.set(path, {path, el: e, kids: []});
    }
    const roots = [];
    for (const n of byPath.values()) {
      const cut = n.path.lastIndexOf('/');
      let parent = cut < 0 ? null : byPath.get(n.path.slice(0, cut));
      // `for:` in the manifest - an LED belongs to its port, a button to its module.
      // Nest under the first target, so an indicator lists under the thing it
      // indicates rather than in a pile of 52 LEDs somewhere else in the tree.
      // A cross-view target is written device-absolute, `/rear/psu-0`, and is not
      // a path in this drawing - a front-view tree cannot nest a rear-view bay,
      // because the rear-view bay is not here. Nest under the first LOCAL target,
      // and leave the row where it naturally falls when there is none. The
      // binding is not dropped: xrefOf() below puts the qualified target on the
      // row as text, so a front-panel PSU lamp reads "led-ps0 → rear/psu-0"
      // rather than sitting silently unexplained among the unbound lamps.
      // A HOLE THAT SOMETHING FILLS IS THAT THING'S APERTURE, NOT A PEER OF IT.
      // Panel cutouts get a namespaced path, `cutout:<id>`, which has no parent
      // component in it, so every one of them landed at the root. On the AGR420
      // that was 74 rows - `cutout:port-0` to `cutout:port-73` - each naming a
      // hole the port listed three rows above already accounts for.
      //
      // The manifest says which is which without being asked: a cutout is
      // declared, then a component is placed in it under THE SAME id. So a
      // cutout whose id is also a path is that node's aperture and nests under
      // it, exactly as a component's own `port-1/aperture/opening` already does.
      // A cutout nothing names is a feature in its own right and stays - which
      // is every cutout on every Cisco chassis, where `shelf-0`, `ft-0` and
      // `esd` are real openings with no module modelled behind them and this row
      // is the only place the tree admits they exist.
      if (!parent && n.path.startsWith('cutout:')) {
        const filled = byPath.get(n.path.slice(7));
        if (filled && filled !== n) parent = filled;
      }
      if (!parent && n.el.dataset.for) {
        const local = n.el.dataset.for.split(' ').filter(t => t[0] !== '/');
        // A PART THAT NAMES SEVERAL OWNERS IS NOT A CHILD OF THE FIRST ONE.
        // The C40G's snap-on filter cover is `for` all four PSU bays, and taking
        // the first target buried a removable full-width panel inside PSU 1 -
        // so the owner looking for it in the list could not find it, and the
        // three other bays it covers said nothing about it.
        //
        // Only for PLACED COMPONENTS, which is what data-ref marks. A shared
        // legend is the opposite case and stays as it was: "0/1" printed between
        // two ports is a mark, it names both, and nesting it under the first of
        // an adjacent pair reads correctly. Lifting those out would have put 74
        // rows back at the top of the AGR420, which is the tree this already fixed.
        const single = local.length === 1 || !n.el.dataset.ref;
        const here = single ? local[0] : null;
        const owner = here && byPath.get(here);
        if (owner && owner !== n) parent = owner;
        // AN INDICATOR WITH ONLY CROSS-VIEW TARGETS STILL BELONGS TO SOMETHING.
        // Leaving it at the root made it a SIBLING of the chassis row, while the
        // lamps beside it on the same faceplate - the ones naming a local target
        // - nested INSIDE that row. One declared group then rendered as two
        // headings in two places, which is what "why are there two LED sections"
        // was seeing: DIAG and Location inside the chassis, Fan and the two PSU
        // lamps outside it, split by nothing more than where the thing each one
        // watches happens to live.
        //
        // The panel is the answer. A lamp pointing at `/rear/psu-1` is screwed to
        // THIS faceplate and reports on something behind it; the target being
        // elsewhere says what it watches, never where it is. So fall back to the
        // chassis - not to the root, which is not a place on the device.
        if (!parent) {
          const body = byPath.get('chassis');
          if (body && body !== n) parent = body;
        }
      }
      (parent ? parent.kids : roots).push(n);
    }
    return roots;
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
    'coax-sma': 'SMA', 'coax-smb': 'SMB', 'micro-usb-b': 'micro-USB B',
    'usb-a': 'USB-A', 'usb-c': 'USB-C', 'sc-apc': 'SC/APC', 'fiber': 'fibre',
    'coax': 'coax', 'ac': 'AC',
  };
  const SPEED = {'1000base-t': '1000BASE-T', '10g-pon': '10G-PON', 'usb3': 'USB 3'};
  const mediaLabel = m => MEDIA[m] || m.toUpperCase();
  const speedLabel = s => SPEED[s] || s.toUpperCase();
  function portLabel(e) {
    const m = e.dataset.media;
    if (!m) return null;
    return e.dataset.speed ? `${mediaLabel(m)} ${speedLabel(e.dataset.speed)}`
                           : mediaLabel(m);
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
    const port = portLabel(e);
    if (port) return `${own} — ${port}`;
    const model = modelOf(e);
    if (model && model !== own) return `${own} — ${model}`;
    const title = e.querySelector(':scope > title');
    return (title && title.textContent.trim()) || own;
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
  const ROLE = {traffic: 0, management: 1, service: 2, indicator: 3,
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
    const off = state.svg ? state.svg.querySelectorAll('[data-portrayal-pulled]') : [];
    const n = off.length;
    el.pulled.hidden = !n;
    el.pulled.textContent = `\u27f2 ${n} removed`;
    el.pulled.title = n === 1 ? 'one part is off - click to put it back'
                              : `${n} parts are off - click to put them all back`;
  }

  function restoreAllPulled() {
    if (!state.svg) return;
    for (const e of [...state.svg.querySelectorAll('[data-portrayal-pulled]')])
      e.removeAttribute('data-portrayal-pulled');
    for (const r of el.tree.querySelectorAll('.node.pulled')) r.classList.remove('pulled');
    refreshPulled();
    emit('pulled', {paths: []});
  }

  function renderTree(roots) {
    const box = el.tree; box.innerHTML = '';
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
            emit('pulled', {paths: [...state.svg.querySelectorAll('[data-portrayal-pulled]')]
                                   .map(e => e.dataset.path).filter(Boolean)});
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

  let halo = null;
  function select(path, fromTree) {
    state.sel = path;
    for (const r of el.tree.querySelectorAll('.node')) r.classList.toggle('sel', r.dataset.path === path);
    const target = path == null ? null
      : state.svg?.querySelector(`[data-path="${CSS.escape(path)}"]`);
    if (halo) { halo.remove(); halo = null; }
    // getScreenCTM is null while the SVG is hidden, which is exactly what a page
    // showing a 3D stage instead has done to it. Selection still stands; only
    // the halo waits until the drawing is on screen again.
    // A region that records no extent gets NO HALO, because its rect is 0x0 and
    // the halo would be a degenerate box the user cannot see - selecting such a
    // region appeared to do nothing at all. Everything else about selection still
    // happens: the row highlights, the tree scrolls, the inspector explains why
    // there is nothing to point at.
    const noExtent = target?.dataset.extent === 'none';
    if (target && !noExtent && state.svg.getScreenCTM()) {
      // getBBox is in the element's OWN coordinate system. The halo is appended to
      // the root, so the box has to be carried through every transform between them
      // or it lands wherever that offset happens to point - which for a bay-mounted
      // port is several slots away.
      const b = target.getBBox();
      const m = state.svg.getScreenCTM().inverse().multiply(target.getScreenCTM());
      const pt = (x, y) => ({x: m.a*x + m.c*y + m.e, y: m.b*x + m.d*y + m.f});
      const cs = [pt(b.x, b.y), pt(b.x + b.width, b.y),
                  pt(b.x, b.y + b.height), pt(b.x + b.width, b.y + b.height)];
      const xs = cs.map(c => c.x), ys = cs.map(c => c.y);
      const x0 = Math.min(...xs), y0 = Math.min(...ys);
      halo = document.createElementNS(NS, 'rect');
      halo.setAttribute('class', 'halo pulse');
      halo.setAttribute('x', x0 - 0.6); halo.setAttribute('y', y0 - 0.6);
      halo.setAttribute('width', Math.max(...xs) - x0 + 1.2);
      halo.setAttribute('height', Math.max(...ys) - y0 + 1.2);
      state.svg.appendChild(halo);
    }
    if (!fromTree) {
      const row = [...el.tree.querySelectorAll('.node')].find(r => r.dataset.path === path);
      if (row) {
        for (let p = row.parentElement; p; p = p.parentElement)
          if (p.classList?.contains('kids')) p.classList.remove('hid');
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
    const bay = (state.meta?.bays?.[state.view] || []).find(b => b.id === path);

    let html = `<h2>${cls || 'node'}</h2><div class="row"><span>path</span><code>${path}</code></div>`;
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

    if (bay) {
      const cur = (state.cfgBays?.[bay.id]) ?? bay.default ?? '';
      const opts = ['<option value="">— open —</option>']
        .concat(bay.accepts.map(a => `<option value="${a}"${a === cur ? ' selected' : ''}>${a}</option>`));
      html += `<div class="row"><span>occupant</span><select id="occ">${opts.join('')}</select></div>`;
      if (!bay.accepts.length)
        html += `<div class="row" style="color:var(--warn)">no component modelled for this slot</div>`;
    }
    if (ref) {
      const c = compByRef(ref.split(':')[0].split('@')[0] + '@' + ref.split('@')[1].split(':')[0]);
      if (c) html += `<div class="row"><button id="open">Open module ↗</button></div>`;
    }
    box.innerHTML = html;

    const occ = box.querySelector('#occ');
    if (occ) occ.onchange = () => swapBay(path, occ.value);
    const open = box.querySelector('#open');
    if (open) open.onclick = () => openModule(ref.split(':')[0]);
  }

  // Swapping is done in the DOM, not by rebuilding: fetch the component's compiled
  // skin and drop it into the bay at the bay's own origin.
  //
  // THE SURGERY LIVES IN swap.js, not here, because viewer3d.js needs the identical
  // operation on the fetched face text before it extracts relief from it - the 3D
  // scene is built entirely out of that text, so a swap that only touched this DOM
  // was invisible in 3D on every device. Two copies of `rename` and `bayTransform`
  // would each have been right the day they were written.
  async function swapBay(bayId, ref) {
    const bay = (state.meta.bays[state.view] || []).find(b => b.id === bayId);
    const g = state.svg.querySelector(`[data-path="${CSS.escape(bayId)}"]`);
    if (!g || !bay) return;
    g.querySelector(`[id="${CSS.escape(bayId)}--module"]`)?.remove();
    state.cfgBays[bayId] = ref || null;
    if (!ref) { refreshTree(); select(bayId, true); emit('change'); return; }
    const c = compByRef(ref);
    const skin = c?.skins?.includes('default') ? 'default' : c?.skins?.[0];
    // NO `cache: 'no-store'`, for the reason dist.js gives about the JSON and
    // relief.js now gives about the face drawings: the flag kept a rebuilt dist
    // from going stale in development and cost every visitor a re-download of
    // every drawing on every page load, forever. Hard-reload is the development
    // tool for that; a permanent header is not.
    //
    // These two fetches are still NOT memoised - they do not go through
    // relief.js's SVG_CACHE - so seating the same module twice in one page still
    // asks twice. Routing them through svgSource would fix that and would also
    // subject them to the runtime override map, which is a behaviour change
    // rather than a caching one, so it is left alone here.
    const file = `${DIST}/components/${c.ns}--${c.name}--${c.major}--${skin}.svg`;
    const txt = await (await fetch(file)).text();
    g.appendChild(seatModule(document, bayId, bay, ref, c, txt));
    refreshTree();
    select(bayId, true);
    emit('change');
  }

  function openModule(ref) { state.module = ref; loadStage(); }

  // ---------------------------------------------------------------- loading

  function refreshTree() { renderTree(buildTree(state.svg)); refreshPulled(); }

  async function loadStage() {
    el.svgHost.innerHTML = '';
    let file;
    if (state.module) {
      const c = compByRef(state.module);
      const skin = c.skins.includes('default') ? 'default' : c.skins[0];
      file = `${DIST}/components/${c.ns}--${c.name}--${c.major}--${skin}.svg`;
    } else {
      file = `${DIST}/${state.device}.${state.cfg}.${state.view}.svg`;
    }
    const txt = await (await fetch(file)).text();
    const doc = new DOMParser().parseFromString(txt, 'image/svg+xml');
    const svg = document.importNode(doc.documentElement, true);
    el.svgHost.appendChild(svg);
    state.svg = svg;
    state.sel = null;
    // Clicking the selected thing again clears it, and clicking away from any
    // part clears it too. A selection you cannot revoke is a halo painted over
    // the hardware for the rest of the session - and on the annotate tab, one
    // that ends up in the export you were composing. Esc does the same from
    // anywhere; see below.
    svg.addEventListener('click', ev => {
      if (dragged) return;              // this click is the end of a pan
      const hit = ev.target.closest('[data-path]');
      const path = hit ? hit.dataset.path : null;
      select(path && path !== state.sel ? path : null, false);
    });
    fit();
    refreshTree();
    crumbs();
    el.inspect.innerHTML = '';
    el.status.textContent = state.module ? '' :
      `${(state.meta.bays[state.view] || []).length} bays`;
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

  async function loadDevice(name) {
    state.device = name;
    state.module = null;
    state.meta = await j(`${name}.configs.json`);
    state.cfg = state.meta.default;
    state.view = state.meta.views[0];
    el.cfg.innerHTML = state.meta.configs
      .map(c => `<option value="${c.name}"${c.name === state.cfg ? ' selected' : ''}>${c.name}</option>`).join('');
    el.view.innerHTML = state.meta.views
      .map(v => `<option value="${v}">${v}</option>`).join('');
    if (picker && picker.value !== name) picker.value = name;
    syncCfgBays();
    emit('device', name, state.meta);
    await loadStage();
  }
  function syncCfgBays() {
    const c = state.meta.configs.find(c => c.name === state.cfg);
    state.cfgBays = {...(c?.bays || {})};
  }

  el.cfg.onchange = e => { state.cfg = e.target.value; state.module = null; syncCfgBays(); loadStage(); };
  el.view.onchange = e => { state.view = e.target.value; state.module = null; loadStage(); };
  addEventListener('resize', fit);

  const ready = (async () => {
    DEVICES = DEVICES.length ? DEVICES : (await j('devices.json')).devices;
    COMPONENTS = COMPONENTS.length ? COMPONENTS : (await j('components.json')).components;
    // the tab shell picks the device and hands it over in the query string, so
    // switching tabs keeps you on the same box
    const want = opts.device || new URLSearchParams(location.search).get('device');
    const start = DEVICES.find(d => d.name === want)
               || DEVICES.find(d => d.name === 'c100g') || DEVICES[0];
    // Which device is the outer shell's state, and inside an iframe this header
    // must not offer a second answer to it. Opened on its own - explore.html
    // straight from the filesystem, or one of the harness pages - there is no
    // outer shell, so the page has to carry the picker itself. Same component
    // either way; only whether it is mounted differs.
    if (parent === window) {
      picker = createDevicePicker({mount: el.dev, devices: DEVICES, value: start.name,
                                   onchange: name => loadDevice(name)});
    } else {
      el.dev.hidden = true;
    }
    await loadDevice(start.name);
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

  return {
    state, el, ready, on, emit,
    select, fit, refreshTree, loadDevice, loadStage, openModule, swapBay,
    compByRef, devices: () => DEVICES, components: () => COMPONENTS,
    device: () => DEVICES.find(d => d.name === state.device),
    hl: () => hlColor,
  };
}
