// Portrayal -> draw.io, as a shape library or a rack diagram.
//
// The representation is the one that survived the bake-off: the compiled SVG as
// an image for the picture, plus one invisible, connectable cell per port. That
// is the only shape that is both exact and addressable - an edge drawn to a port
// records source="port-12" rather than a coordinate on the device, which is the
// whole argument for exporting from a model that names things.
//
// The alternatives and why they lost, since the question will come up again:
// a stencil is ~30x smaller and vector, but mxStencil renders no text at all, so
// a faceplate loses every port number and every silkscreen line; and although a
// stencil CAN carry named connection points, draw.io writes exitX/exitY into the
// edge and never the name. One cell per element is addressable but needs path
// conversion to look right and runs to hundreds of cells a device.
//
// Finding the ports is zones.js's; this file only writes cells.

import { readDrawing } from './zones.js';
import { normalise } from './marks.js';

// Standalone entries are drawn at 2 px/mm, which is legible on a blank canvas.
export const SCALE = 2;

// draw.io's own rack wants something else entirely. rackCabinet3 is 180 wide and
// one RU is 14.8, and marginLeft is 9 with the U numbers OFF but 33 with them ON
// - mxRack.js sets it that way itself when you toggle numbering. Using 9 with
// numbering on puts every device 24 units too far left AND 24 too wide, which
// reads as "the rack will not fit its contents".
export const RACK = {
  outer: 180, unit: 14.8, marginL: 33, marginR: 9, marginTop: 21, marginBottom: 22,
};
RACK.width = RACK.outer - RACK.marginL - RACK.marginR;      // 138

const esc = s => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

// ── cells ────────────────────────────────────────────────────────────────
const cell = (id, value, style, x, y, w, h, parent = '1') =>
  `<mxCell id="${esc(id)}" value="${esc(value)}" style="${style}" vertex="1" ` +
  `parent="${esc(parent)}"><mxGeometry x="${x.toFixed(2)}" y="${y.toFixed(2)}" ` +
  `width="${Math.max(w, 0.5).toFixed(2)}" height="${Math.max(h, 0.5).toFixed(2)}" ` +
  `as="geometry"/></mxCell>`;

// A PORT names the drawing path it came from. The cell id is a slug of the
// SVG id, which is namespaced for a port on a seated card
// (slot-2--module--p0); the path (slot-2/module/p0) is what a cable plan,
// Explorer's swaps and a rack plan all speak, so a connector drawn later
// finds its port by this attribute instead of reversing the slug.
const portCell = (id, path, style, x, y, w, h, parent) =>
  `<object label="" portrayal-path="${esc(path)}" id="${esc(id)}"><mxCell style="${style}" ` +
  `vertex="1" parent="${esc(parent)}"><mxGeometry x="${x.toFixed(2)}" y="${y.toFixed(2)}" ` +
  `width="${Math.max(w, 0.5).toFixed(2)}" height="${Math.max(h, 0.5).toFixed(2)}" ` +
  `as="geometry"/></mxCell></object>`;

const model = cells =>
  `<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>${cells.join('')}` +
  `</root></mxGraphModel>`;

// One connection point per port, dead centre. Without this a port gets draw.io's
// DEFAULT perimeter points - the four sides and the corners, never a centre -
// which is right for a box you draw an arrow to and wrong for a socket you plug
// a cable into. The third field is the perimeter flag: 0 means "exactly at this
// fraction", not "project outwards to the outline".
const PORT_POINT = 'points=[[0.5,0.5,0]];';

/** SVG text as a data URI. draw.io omits ";base64" - the semicolon would
 *  terminate the style token it sits in. */
export function svgDataUri(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  }
  return 'data:image/svg+xml,' + btoa(bin);
}

// ── covers ───────────────────────────────────────────────────────────────
// A COVER COMES OFF IN THE DIAGRAM TOO. The R740xd's bezel is drawn by default
// and hides the drives behind it; Explorer takes it off with a pull handle, and
// a diagram needs the same. So a cover is lifted out of the face into its own
// image cell, stacked over a face drawn without it, and tagged with its kind -
// draw.io's View > Tags hides every `bezel` at once, and a single one can
// simply be deleted. ONE TAG, deliberately: draw.io hides a cell only when ALL
// of its tags are hidden, so a second tag (`cover bezel`) meant hiding `bezel`
// alone did nothing.
// The cell stays inside its device's group, so it moves with the device; a
// layer would have left it behind when the device was dragged.
//
// BEZELS ONLY, for now. The drawings have no single marker meaning "this part
// hides those parts": `behaviour: mounts` is on screws and studs too, and
// covers are grouped under `covers`, `filters` or `furniture` by device. Rather
// than guess from group names, this takes a bezel that is itself removable
// until Portrayal names covers explicitly. `data-class="bezel"` alone is not
// enough: the R740xd's riser shrouds and trims carry it on plates deep inside
// parts that do not come off.
export const COVER_SELECTOR = '[data-class="bezel"][data-behaviour="mounts"][data-path]';

/** The face split into a drawing without its covers, and each cover alone on
 *  the same canvas (so it lands exactly where it was). Outermost covers only. */
export function splitCovers(svgText) {
  // No bezel, nothing to split - and no parse. A face is parsed once for the
  // base and once more per cover, which is three copies of a large chassis to
  // find nothing on most of them, and it lets a face with no cover be written
  // where there is no DOMParser at all.
  if (!/data-class=["']bezel["']/.test(svgText)) return {base: svgText, covers: []};
  const parse = () => new DOMParser().parseFromString(svgText, 'image/svg+xml').documentElement;
  const outermost = root => [...root.querySelectorAll(COVER_SELECTOR)]
    .filter(el => !el.parentElement.closest(COVER_SELECTOR));
  const found = outermost(parse());
  if (!found.length) return {base: svgText, covers: []};
  const ser = root => new XMLSerializer().serializeToString(root);

  const baseRoot = parse();
  for (const el of outermost(baseRoot)) el.remove();

  const covers = found.map(({dataset}) => {
    const root = parse();
    const keep = outermost(root).find(el => el.dataset.path === dataset.path);
    const onPath = new Set();
    for (let n = keep; n && n !== root; n = n.parentElement) onPath.add(n);
    (function prune(el) {
      for (const kid of [...el.children]) {
        if (kid === keep) continue;
        if (onPath.has(kid)) prune(kid);
        else if (kid.localName !== 'style' && kid.localName !== 'defs') kid.remove();
      }
    })(root);
    return {path: dataset.path, cls: dataset.class, text: ser(root)};
  });
  return {base: ser(baseRoot), covers};
}

// A port is ON a bay's card when its path runs through the bay: slot-2/module/p0
// is slot-2's. deviceCells nests such a port in its bay and makes the bay a
// container that takes no line; connectable() counts by the same rule.
const onBay = (p, b) => p.cls === 'port' && String(p.path || p.id).startsWith(`${b.id}/`);

/**
 * How many cells deviceCells writes that a line can be drawn to: every port,
 * and every bay that holds no port of its own (an empty slot). A bay with a
 * card's ports in it is a container, `connectable=0`, so it is not one - and
 * counting it overstated a modular chassis by its seated cards.
 */
export function connectable(ports) {
  const bays = ports.filter(p => p.cls === 'bay');
  return ports.filter(p => p.cls === 'port').length
    + bays.filter(b => !ports.some(p => onBay(p, b))).length;
}

/**
 * One device: the compiled face as an image, with a connectable cell per port.
 *
 * The root is a GROUP rather than the image itself. Resizing an image vertex
 * does not rescale its children, so ports slid off the faceplate the moment a
 * rack resized it; group children scale with the group. `visible` tints the
 * ports so they can be seen while judging - shipped exports leave them
 * invisible, which is the point of putting them over an exact picture.
 */
export function deviceCells(id, svgText, vb, ports, x, y, w, h, {visible = false, covers = true} = {}) {
  const sx = w / vb[2], sy = h / vb[3];
  // FROM THE VIEWBOX'S CORNER, not from 0,0. A device face starts at the
  // origin, so the two were the same thing until the faces that do not: an
  // optic's face stands its bail above y=0 (`0 -4.5 18.35 14.6`), and a cropped
  // export is a viewBox over the middle of a faceplate. Measured from 0,0, the
  // ports of either land off the picture by the viewBox's offset.
  const X = v => (v - vb[0]) * sx, Y = v => (v - vb[1]) * sy;
  const tint = c => visible
    ? (c === 'bay' ? 'fillColor=#F5A623;opacity=16;strokeColor=#F5A623;'
                   : 'fillColor=#00A0FF;opacity=22;strokeColor=#00A0FF;')
    : 'fillColor=none;strokeColor=none;';
  const out = [cell(id, '', 'group;html=1;', x, y, w, h)];
  const split = covers ? splitCovers(svgText) : {base: svgText, covers: []};
  out.push(cell(`${id}-face`, '',
    `shape=image;imageAspect=0;editableCssRules=.*;image=${svgDataUri(split.base)};`,
    0, 0, w, h, id));
  // Over the face, under the ports: a hidden bezel must not take the drive
  // bays' connection points with it, and a shown one must not bury them.
  for (const c of split.covers) {
    out.push(`<object label="" tags="${esc(c.cls)}" portrayal-cover="${esc(c.path)}" ` +
      `id="${esc(`${id}-cover-${slug(c.path)}`)}"><mxCell style="shape=image;imageAspect=0;` +
      `editableCssRules=.*;connectable=0;image=${svgDataUri(c.text)};" vertex="1" ` +
      `parent="${esc(id)}"><mxGeometry x="0" y="0" width="${w.toFixed(2)}" ` +
      `height="${h.toFixed(2)}" as="geometry"/></mxCell></object>`);
  }

  // A MODULAR CHASSIS GROUPS ITS PORTS UNDER THE CARD THEY ARE ON. The cells
  // are still at their real positions over the image - this is the footprint,
  // not the miniature - but a bay is now a container holding its own card's
  // ports, which gives the bay an identity a cable can be checked against.
  //
  // NOT COLLAPSIBLE. It was, so that folding a card took its forty connection
  // points with it - but draw.io marks every collapsible container with a "-"
  // toggle, which sat on each card like a stray icon, and folding hid only
  // invisible cells while the card's picture stayed exactly as drawn.
  const bays = ports.filter(p => p.cls === 'bay');
  const owned = new Set();
  for (const b of bays) {
    const mine = ports.filter(p => onBay(p, b));
    if (!mine.length) continue;
    mine.forEach(p => owned.add(p));
    const bx = X(b.x), by = Y(b.y);
    const bw = Math.max(b.w * sx, 1.5), bh = Math.max(b.h * sy, 1.5);
    out.push(
      `<object label="" portrayal-bay="${esc(b.id)}"` +
      (b.model ? ` portrayal-module="${esc(b.model)}"` : '') +
      ` id="${esc(`${id}-${b.id}`)}"><mxCell style="${tint('bay')}html=1;` +
      `container=1;collapsible=0;connectable=0;" vertex="1" ` +
      `parent="${esc(id)}"><mxGeometry x="${bx}" y="${by}" width="${bw}" ` +
      `height="${bh}" as="geometry"/></mxCell></object>`);
    for (const p of mine) {
      out.push(portCell(`${id}-${p.id}`, p.path || p.id,
        `${tint(p.cls)}html=1;connectable=1;${PORT_POINT}`,
        X(p.x) - bx, Y(p.y) - by,
        Math.max(p.w * sx, 1.5), Math.max(p.h * sy, 1.5), `${id}-${b.id}`));
    }
  }
  for (const p of ports) {
    if (owned.has(p) || p.cls === 'bay') continue;
    out.push(portCell(`${id}-${p.id}`, p.path || p.id, `${tint(p.cls)}html=1;connectable=1;${PORT_POINT}`,
      X(p.x), Y(p.y), Math.max(p.w * sx, 1.5), Math.max(p.h * sy, 1.5), id));
  }
  // A bay with no ports of its own is still worth being a cell - it is an empty
  // slot - so it keeps the behaviour it had before this change.
  for (const b of bays) {
    if (ports.some(p => onBay(p, b))) continue;
    out.push(cell(`${id}-${b.id}`, '', `${tint('bay')}html=1;connectable=1;${PORT_POINT}`,
      X(b.x), Y(b.y), Math.max(b.w * sx, 1.5), Math.max(b.h * sy, 1.5), id));
  }
  return out;
}

/** A library entry for one device, at whatever scale the caller wants. */
export function entry(name, svgText, vb, ports, opts = {}) {
  const {ru = null, visible = false} = opts;
  const w = ru ? RACK.width : vb[2] * SCALE;
  const h = ru ? RACK.unit * ru : vb[3] * SCALE;
  const id = slug(name);
  return {
    w: Math.round(w), h: Math.round(h),
    title: ru ? `${name} (${ru}RU, rack)` : name,
    tags: `portrayal ${name} ${ru ? 'rack' : 'standalone'} port`,
    xml: model(deviceCells(id, svgText, vb, ports, 0, 0, w, h, {visible})),
  };
}

const slug = s => String(s).replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-|-$/g, '');

/**
 * <mxlibrary> wrapping a JSON array.
 *
 * The JSON sits in an XML TEXT NODE, so its angle brackets must be escaped or
 * the file is not well-formed XML and draw.io rejects it before it ever reaches
 * the JSON - reporting a JSON error about its own error page, which is a
 * memorably unhelpful way to find out.
 */
export function library(entries, provenance = null) {
  const payload = JSON.stringify(entries)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // WHAT THIS IS A LIBRARY OF, as an XML comment. draw.io ignores it, the file
  // keeps it, and a person who opens the .xml can see which drawings their
  // shapes came from. A device's version moves when its drawing does, and a
  // major bump means a slot moved or an id was renamed - so a shape placed from
  // an old library can disagree with the current drawing about where a port is.
  // The comment is the only place to say so: an mxlibrary has no metadata slot,
  // and putting it in a shape's title would put it in the shape picker.
  const head = provenance ? `<!--\n${String(provenance)
    .replace(/--+/g, '-')}\n-->\n` : '';
  return `${head}<mxlibrary>${payload}</mxlibrary>`;
}

// Room for the U gutter between cabinets, and more between racks than between
// the two sides of one rack - so a front/rear pair reads as a pair.
const FACE_GAP = 90, RACK_GAP = 190;
const pairWidthOf = fs => fs.length * RACK.outer + (fs.length - 1) * FACE_GAP;

// CONTENT STARTS AT THE ORIGIN. Whatever draw.io decides to scroll to when it
// opens a file - and it is not the page's top-left, which was tried - the one
// place it will not be looking is off past the end of an empty canvas. So the
// first rack is at x=0 and the page is drawn tight around what is on it,
// leaving only the headroom the cabinet's own label needs above it.
const TOP = 30;

// ── cables ───────────────────────────────────────────────────────────────
// WHAT THE PORT CELLS WERE FOR. A cable is an edge whose source and target are
// two port cells, so in draw.io its connectors stay glued to their ports when a
// device is dragged to another U. The shape is a rack plan's:
//   {id, a: {item, path, view}, b: {item, path, view}, media, purpose, label, length}
// where `item` names a mounted device (its `id`, else its `name`), `path` is a
// port's data-path - `slot-2/module/p0` for a port on a seated card - and
// `view` the face it is on.

/** Jacket colours by `media`. A default, not a rule: `cableStyle` takes a map
 *  of the embedder's own (merged over this one) or a function. */
export const CABLE_COLOURS = {
  dac: '#4D4D4D', aoc: '#2F80C0', cu: '#7A5C99', mm: '#16A5A5', sm: '#D4A017',
  om1: '#E07B39', om2: '#E07B39', om3: '#16A5A5', om4: '#16A5A5', om5: '#7DB343',
  os1: '#D4A017', os2: '#D4A017', cat5e: '#7A5C99', cat6: '#7A5C99', cat6a: '#7A5C99',
  default: '#808080',
};

// ORTHOGONAL, AND NO ARROWS. A patch lead has no direction, and draw.io's
// default edge ends in an arrowhead that says it does. NOT html=1, here or on
// a stub's label: an html label renders its text as markup, and a cable label
// or a port path is text a plan typed, not markup.
const CABLE_EDGE = 'edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=none;' +
  'startArrow=none;strokeWidth=2;fontSize=8;labelBackgroundColor=#FFFFFF;';

function cableStyleOf(cable, opt) {
  if (typeof opt === 'function') return String(opt(cable));
  const map = opt ? {...CABLE_COLOURS, ...opt} : CABLE_COLOURS;
  const colour = map[String(cable.media || '').toLowerCase()] || map.default;
  return `${CABLE_EDGE}strokeColor=${colour};`;
}

// A plan writes `length` as {value, unit, source}; a number or a string is
// taken as it is written.
const lengthText = l => (l == null || l === '') ? ''
  : typeof l === 'object' ? [l.value, l.unit].filter(v => v != null && v !== '').join(' ')
  : String(l);

/** Notes as one XML comment. draw.io reads the <diagram>s inside <mxfile> and
 *  ignores the rest, so the file carries what it could not draw for a person
 *  who opens it in an editor. `--` would close the comment. */
const notesComment = notes => notes.length
  ? `<!--\nNotes:\n${notes.map(n => `- ${n}`).join('\n').replace(/-{2,}/g, '-')}\n-->`
  : '';

// EVERY EDGE ID FROM THE CABLE'S OWN ID, so the same plan writes the same file
// and a cable is findable by its name after a round trip. Slugged like a
// device's cell id - and draw.io keeps the first cell of an id and silently
// drops the second, so every id a cable writes comes from ONE set of ids
// already taken. Checking the base slug alone was not enough: "c 6" and "c-6"
// share one, the second is numbered `cable-c-6-2`, and a third cable called
// `c-6-2` then lands on it; a stub's `-a` suffix meets a cable called `x-a` the
// same way. A candidate that is taken is numbered on until it is free, and a
// stub pair's four ids are taken together so they keep one suffix.
function idAllocator() {
  const used = new Set();
  return (base, suffixes) => {
    for (let n = 1; ; n++) {
      const stem = n === 1 ? base : `${base}-${n}`;
      const ids = suffixes.map(s => stem + s);
      if (ids.every(id => !used.has(id))) {
        ids.forEach(id => used.add(id));
        return stem;
      }
    }
  };
}

const endText = e => `${e.item != null ? `${e.item} ` : ''}${e.view ? `${e.view}/` : ''}${e.path ?? '?'}`;

/**
 * The cells a cable list adds to each page, and the cables it could not draw.
 *
 * `locate(end)` answers {at: [{page, cell, y, stubX, far}]} in page order, or
 * {reason}. A cable whose two ends share a page is one edge there. One whose
 * ends are only on different pages - a front-to-rear run, when each face is a
 * page - is a STUB on each: an edge from the port to a small label naming the
 * far end, because a draw.io edge cannot leave its page. A cable with an end
 * that is not drawn at all is NOT half drawn: it goes in the notes with why.
 */
function cableCells(cables, locate, {cableStyle} = {}) {
  const pages = new Map(), notes = [];
  const put = (page, xml) => (pages.get(page) || pages.set(page, []).get(page)).push(xml);
  // Stub labels stack down the gutter beside their cabinet rather than over
  // each other when two ports sit at one height.
  const taken = new Map();
  const slot = (page, x, y) => {
    const key = `${page}:${x}`;
    const ys = taken.get(key) || taken.set(key, []).get(key);
    while (ys.some(t => Math.abs(t - y) < 10)) y += 10;
    ys.push(y);
    return y;
  };
  const take = idAllocator();
  cables.forEach((c, i) => {
    const a = locate(c.a || {}), b = locate(c.b || {});
    if (a.reason || b.reason) {
      const why = [a.reason && `a (${endText(c.a || {})}) ${a.reason}`,
                   b.reason && `b (${endText(c.b || {})}) ${b.reason}`].filter(Boolean);
      notes.push(`Cable ${c.id ?? i + 1} is not drawn: ${why.join('; ')}.`);
      return;
    }
    const base = `cable-${slug(c.id ?? '') || i + 1}`;
    const style = esc(cableStyleOf(c, cableStyle));
    const value = [c.label, lengthText(c.length)].filter(Boolean).join(' · ');
    // THE CABLE STAYS A CABLE after a round trip: draw.io keeps an <object>'s
    // attributes through an edit and a save, as it keeps a port's path.
    const attrs = [['portrayal-cable', c.id], ['portrayal-media', c.media],
                   ['portrayal-purpose', c.purpose], ['portrayal-length', lengthText(c.length)]]
      .filter(([, v]) => v != null && v !== '')
      .map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
    const edge = (eid, extra, src, dst) =>
      `<object label="${esc(value)}"${attrs}${extra} id="${esc(eid)}"><mxCell ` +
      `style="${style}" edge="1" parent="1" source="${esc(src)}" target="${esc(dst)}">` +
      `<mxGeometry relative="1" as="geometry"/></mxCell></object>`;
    const pa = a.at.find(p => b.at.some(q => q.page === p.page));
    if (pa) {
      const pb = b.at.find(q => q.page === pa.page);
      put(pa.page, edge(take(base, ['']), '', pa.cell, pb.cell));
      return;
    }
    const id = take(base, ['-a', '-a-far', '-b', '-b-far']);
    for (const [end, here, there] of [['a', a.at[0], b.at[0]], ['b', b.at[0], a.at[0]]]) {
      const far = `${id}-${end}-far`;
      const y = slot(here.page, here.stubX, here.y - 5);
      put(here.page, cell(far, `→ ${there.far}`,
        'text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;' +
        'fontSize=8;fontColor=#333333;spacingLeft=2;',
        here.stubX, y, 84, 10));
      put(here.page, edge(`${id}-${end}`, ` portrayal-end="${end}"`, here.cell, far));
    }
  });
  return {pages, notes};
}

// THE PORTS A RACK DIAGRAM DRAWS, where it draws them: the same walk, ids and
// arithmetic as rackDiagram's own, so an edge names cells that exist. Keyed by
// item and path; a device drawn on several pages has a place on each.
function rackPorts(groups, faces) {
  const at = new Map(), drawn = new Map(), known = new Set();
  groups.forEach((group, gi) => {
    const gFaces = group.faces || faces;
    let x = 0;
    group.racks.forEach((rack, r) => {
      gFaces.forEach((face, i) => {
        const fx = x + i * (RACK.outer + FACE_GAP);
        for (const m of rack.mounted) {
          const item = m.id ?? m.name;
          known.add(item);
          const f = m.faces[face];
          if (!f) continue;
          (drawn.get(item) || drawn.set(item, new Set()).get(item)).add(face);
          const id = `${slug(item)}-g${gi}r${r}-${face}`;
          const top = TOP + RACK.marginTop + (m.u - 1) * RACK.unit;
          const sy = RACK.unit * (m.ru || 1) / f.vb[3];
          for (const p of f.ports) {
            if (p.cls !== 'port') continue;
            const path = p.path || p.id;
            const key = `${item}\n${path}`;
            (at.get(key) || at.set(key, []).get(key)).push({
              page: gi, face, cell: `${id}-${p.id}`,
              y: top + (p.y + p.h / 2 - f.vb[1]) * sy,
              stubX: fx + RACK.outer + 4,
              far: [rack.label, m.name, `${face}/${path}`].filter(Boolean).join(' · '),
            });
          }
        }
      });
      x += pairWidthOf(gFaces) + RACK_GAP;
    });
  });
  return end => {
    if (!known.has(end.item)) return {reason: 'names no mounted device'};
    const faceOk = p => !end.view || p.face === end.view;
    const found = (at.get(`${end.item}\n${end.path}`) || []).filter(faceOk);
    if (found.length) return {at: found};
    const sides = drawn.get(end.item);
    if (end.view && !(sides && sides.has(end.view)))
      return {reason: 'is on a face no page draws'};
    return {reason: "is not a port in its device's drawing"};
  };
}

/** What a cable list adds to a rack diagram: the cells for each page (by its
 *  index in `groups`) and the notes for the cables it cannot draw. rackDiagram
 *  calls this itself; a caller that wants the notes as a list calls it too. */
export function rackCables(groups, cables = [], {faces = ['front'], cableStyle} = {}) {
  return cableCells(cables, rackPorts(groups, faces), {cableStyle});
}

/**
 * A rack diagram: draw.io's own cabinet, with devices mounted in it.
 *
 * The rails, the U numbering and the snapping are draw.io's - we do not draw a
 * rack, we fill one. `childLayout=rack` snaps a child to whole units, so a
 * device only has to be the right size and at the right U.
 */
/**
 * Rack elevations as a multi-PAGE .drawio: one page per group.
 *
 * `groups` is [{label, racks: [{label, mounted}]}]. Everything on one canvas
 * becomes a wall you navigate rather than a diagram you read, and an .mxfile
 * takes as many <diagram> elements as you give it - each is a tab along the
 * bottom of the editor.
 *
 * A group may carry its own `faces` (a rack builder draws one page per face),
 * a mounted device its own `id` (cell ids are slugged from it instead of the
 * name, which two devices can share), and a rack its own `numDisp` (`descend`
 * prints 1 at the bottom). Without them, the output is exactly what it always
 * was.
 *
 * `cables` adds the patching (see rackCables): an edge between two port cells
 * where both ends are on one page, a labelled stub on each page where they are
 * not, and a note for a cable with an end not drawn. `cableStyle` is a map of
 * media to colour or a function from a cable to an edge style. `notes` are the
 * caller's own, written in the same comment as the cables' - one block, inside
 * <mxfile>, so it survives being handed around as a file.
 */
export function rackDiagram(groups, {faces = ['front'], labels = true,
                                     cables = [], cableStyle, notes = []} = {}) {
  const wired = rackCables(groups, cables, {faces, cableStyle});
  // Each rack carries its own height, because each is grown to its contents.
  const heightOf = units => RACK.marginTop + RACK.marginBottom + units * RACK.unit;
  const style =
    `shape=mxgraph.rackGeneral.rackCabinet3;rackUnitSize=${RACK.unit};` +
    `fillColor2=#f4f4f4;container=1;collapsible=0;childLayout=rack;allowGaps=1;` +
    `marginLeft=${RACK.marginL};marginRight=${RACK.marginR};` +
    `marginTop=${RACK.marginTop};marginBottom=${RACK.marginBottom};` +
    // The label sits ABOVE the cabinet. Centred in it - the default - a name
    // long enough to be useful is wider than 180 units and runs into the rack
    // either side of it.
    `textColor=#666666;numDisp=ascend;html=1;` +
    `verticalLabelPosition=top;verticalAlign=bottom;fontSize=11;fontStyle=1;`;
  const pages = groups.map((group, gi) => {
    const gFaces = group.faces || faces;
    const pairWidth = pairWidthOf(gFaces);
    const cells = [];
    let x = 0;
    group.racks.forEach((rack, r) => {
      const units = rack.units || 12;
      const h = heightOf(units);
      gFaces.forEach((face, i) => {
        const rackId = `g${gi}r${r}-${face}`;
        const fx = x + i * (RACK.outer + FACE_GAP);
        // The PAGE is named for the vendor and family, so the cabinet only
        // has to say which rack and which side.
        cells.push(cell(rackId, rack.label ? `${rack.label} · ${face}` : face,
                        rack.numDisp ? style.replace('numDisp=ascend;', `numDisp=${rack.numDisp};`) : style,
                        fx, TOP, RACK.outer, h));
        for (const m of rack.mounted) {
          const f = m.faces[face];
          const ru = m.ru || 1;
          const id = `${slug(m.id ?? m.name)}-g${gi}r${r}-${face}`;
          // A device with nothing drawn on this side does NOT borrow the other
          // side's picture. An optical shelf that is only a front is a real
          // thing, and putting a faceplate on the back of a rack would be a
          // straightforward lie.
          //
          // It says so rather than leaving a hole, though. A rear cabinet with
          // two devices in it and nothing drawn reads as a broken export; the
          // same cabinet saying "no rear drawing" against each device reads as
          // the library being honest about what it has. The unit span is still
          // right, so the device occupies its real U either way.
          if (!f) {
            const top0 = RACK.marginTop + (m.u - 1) * RACK.unit;
            cells.push(cell(`${id}-none`, `no ${face} drawing`,
              'rounded=0;html=1;dashed=1;dashPattern=4 4;fillColor=#f0f0f0;' +
              'strokeColor=#b0b0b0;fontColor=#8a8a8a;fontSize=9;' +
              'verticalAlign=middle;align=center;movable=0;resizable=0;' +
              'editable=0;connectable=0;',
              RACK.marginL, top0, RACK.width, RACK.unit * ru, rackId));
            if (labels) {
              const ly0 = RACK.marginTop + (m.u - 1 + ru) * RACK.unit;
              cells.push(cell(`${id}-label`, `\u25B2 ${m.name}`,
                'text;html=1;strokeColor=none;fillColor=none;align=left;' +
                'verticalAlign=middle;fontSize=9;fontColor=#333333;spacingLeft=4;' +
                'movable=0;resizable=0;editable=0;connectable=0;',
                RACK.marginL, ly0, RACK.width, RACK.unit, rackId));
            }
            continue;
          }
          // Which end U1 is at follows the container's numbering, not the
          // machine room. `numDisp=ascend` prints 1 at the TOP and counts down,
          // so placing from the bottom the way a real rack is counted puts
          // every device against a number it is not in.
          const top = RACK.marginTop + (m.u - 1) * RACK.unit;
          const dh = RACK.unit * ru;
          const sub = deviceCells(id, f.svg, f.vb, f.ports, RACK.marginL, top,
                                  RACK.width, dh, {visible: false});
          // The group keeps the name as its value - Outline lists it, search
          // finds it, an edge endpoint reports it - but does not PRINT it.
          // Drawn, it lands a couple of units off its own device and collides
          // with the U numbers, and a label against the wrong number is worse
          // than none. The faceplate carries the model in silkscreen anyway.
          sub[0] = cell(id, m.name, 'group;html=1;noLabel=1;',
                        RACK.marginL, top, RACK.width, dh, rackId);
          for (let k = 1; k < sub.length; k++) {
            sub[k] = sub[k].replace(/parent="1"/, `parent="${id}"`);
          }
          cells.push(...sub);
          // NAMED IN THE GUTTER BELOW, NOT ON THE DEVICE. Printed on the device
          // the label lands a couple of units off its own faceplate and collides
          // with the U numbers, and a label against the wrong number is worse
          // than none - which is why these were suppressed. In the unit of air
          // that already sits between devices it belongs to nothing, cannot be
          // mistaken for a U number, and the arrow says which way to read it.
          // Rows of white 1RU boxes are otherwise genuinely hard to tell apart.
          if (labels) {
            const ly = RACK.marginTop + (m.u - 1 + ru) * RACK.unit;
            cells.push(cell(`${id}-label`, `▲ ${m.name}`,
              'text;html=1;strokeColor=none;fillColor=none;align=left;' +
              'verticalAlign=middle;fontSize=9;fontColor=#333333;spacingLeft=4;' +
              'movable=0;resizable=0;editable=0;connectable=0;',
              RACK.marginL, ly, RACK.width, RACK.unit, rackId));
          }
        }
      });
      x += pairWidth + RACK_GAP;
    });
    const tallest = Math.max(...group.racks.map(r => heightOf(r.units || 12)));
    // NO dx/dy. Those are draw.io's stored scroll offset, and hard-coding them
    // opened the file scrolled off its own content - the racks above the
    // viewport with a sliver of cabinet showing, which reads as an empty file
    // until you think to zoom out. Omitted, draw.io fits the page itself.
    // PAGE FRAME OFF. With page="1" draw.io opened the file scrolled past the
    // bottom of its own content - the rack feet at the top of the viewport and
    // everything else above it. Putting the content at the origin and drawing
    // the page tight around it both moved it slightly and neither fixed it, so
    // the page is what it is scrolling to rather than the drawing. With no page
    // it has nothing to scroll to but the graph, and fits that instead.
    //
    // pageWidth/pageHeight are kept: they are what a later File > Page Setup or
    // an export reads, and only `page` decides whether a frame is drawn.
    return `<diagram name="${esc(group.label)}" id="page${gi}">` +
      `<mxGraphModel grid="0" page="0" pageScale="1" ` +
      `pageWidth="${Math.ceil(x - RACK_GAP + 20)}" ` +
      `pageHeight="${Math.ceil(tallest + TOP + 20)}"><root>` +
      `<mxCell id="0"/><mxCell id="1" parent="0"/>${cells.join('')}` +
      `${(wired.pages.get(gi) || []).join('')}</root></mxGraphModel></diagram>`;
  });
  // Front and rear are NOT mirrored. Walking round a rack does reverse
  // left-to-right, but every DCIM elevation - NetBox's and Nautobot's included -
  // shows both sides in the same order, because the point of the pair is to
  // read one device across two views. Mirroring makes that a puzzle.
  return `<mxfile host="portrayal">${notesComment([...notes, ...wired.notes])}` +
    `${pages.join('')}</mxfile>`;
}


/**
 * One device as a .drawio document: the face at SCALE px/mm on a page of its
 * own, its ports connectable, nothing else on the canvas.
 *
 * The form to OPEN, where a library is the form to keep. A person who set a
 * device up the way a project needs it - optics seated, lamps lit, one region
 * cropped - wants to draw on that device now, and a library makes them import a
 * file, find the shape and drag it out first.
 *
 * `cables` are drawn between this device's own ports: an end names it by
 * leaving `item` out or giving `opts.item` (the name, by default), and a `view`
 * other than `opts.view`, where that is given, is a face this file does not
 * draw. An end that is not here is a note, as in a rack.
 */
export function diagram(name, svgText, vb, ports, opts = {}) {
  return diagramOf(name, svgText, vb, ports, opts).text;
}

function diagramOf(name, svgText, vb, ports, opts = {}) {
  const {cables = [], cableStyle, notes = [], item = name, view = null} = opts;
  const e = entry(name, svgText, vb, ports, opts);
  // entry() names the device's cells by this slug, and these are its ports.
  const id = slug(name), here = new Map();
  for (const p of ports) {
    if (p.cls === 'port') here.set(String(p.path || p.id), `${id}-${p.id}`);
  }
  const wired = cableCells(cables, end => {
    if (end.item != null && end.item !== item) return {reason: 'names a device this file does not draw'};
    if (end.view && view && end.view !== view) return {reason: 'is on a face this file does not draw'};
    const c = here.get(String(end.path));
    return c ? {at: [{page: 0, cell: c}]}
      : {reason: "is not a port in this drawing (cropped away, or an unknown path)"};
  }, {cableStyle});
  const all = [...notes, ...wired.notes];
  const text = `<mxfile host="portrayal">${notesComment(all)}` +
    `<diagram name="${esc(name)}" id="page0">` +
    e.xml.replace('<mxGraphModel>', '<mxGraphModel grid="0" page="0">')
      .replace('</root>', `${(wired.pages.get(0) || []).join('')}</root>`) +
    `</diagram></mxfile>`;
  return {text, notes: all};
}

/**
 * A live drawing, as it stands, for draw.io.
 *
 *   form: 'diagram'  a .drawio to open and draw on (the default)
 *         'library'  a one-shape library to keep beside the others
 *
 * `doc` is a marks document - the highlights, labels, lamp states and crop a
 * page has applied - and goes into the picture exactly as marks.toSvg would
 * write it. Ports outside a crop are left out rather than left floating.
 *
 * `cables` (with `cableStyle`) draws a cable list between this drawing's ports,
 * as `diagram` does; a cable with an end outside the drawing is in `notes`.
 *
 * @returns {{text, name, ports, notes}}  the file's text, a name for it, how
 *   many cells a line can be drawn to - every port, and every empty bay, not a
 *   bay holding a card, which is a container of its card's ports
 *   (connectable()) - and what it could not draw
 */
export function toDrawio(svgRoot, doc = {}, {form = 'diagram', name, visible = false,
                                             cables = [], cableStyle, item} = {}) {
  const d = normalise(doc);
  const {text, vb, ports} = readDrawing(svgRoot, d);
  const title = name || [d.device, d.config, d.view].filter(Boolean).join(' ') || 'drawing';
  if (form === 'library') {
    // A LIBRARY HOLDS SHAPES, NOT A DRAWING: there is nowhere in one for an
    // edge to live, so cables handed to it are said to be left out.
    const notes = cables.length
      ? [`${cables.length} cable(s) not written: a library holds shapes, not edges.`] : [];
    return {text: library([entry(title, text, vb, ports, {visible})],
              `Portrayal ${title} - ${d.marks.length} mark(s)${d.crop ? ', cropped' : ''}`),
            name: title, ports: connectable(ports), notes};
  }
  const out = diagramOf(title, text, vb, ports,
    {visible, cables, cableStyle, item: item ?? title, view: d.view || null});
  return {text: out.text, name: title, ports: connectable(ports), notes: out.notes};
}
