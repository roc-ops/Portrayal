// Portrayal -> OmniGraffle, as a stencil, built in the browser.
//
// The same representation the draw.io export settled on (drawio.js): the face
// as one picture, plus one invisible shape over every port and bay, so a line
// drawn to a port attaches to THAT port rather than to a point on a picture.
// Worked out on a one-device prototype and tested in OmniGraffle 7 before it
// was generalised.
//
// What each piece is, and why:
//
// - A shape per port, named after it, carrying its media and speed as
//   key/value data (`UserInfo`). OmniGraffle's own magnets would store only an
//   INDEX on a line, never a name - the same trap as draw.io's exitX/exitY. The
//   shape keeps the address, shows in the sidebar by name, and its data
//   survives dragging the device out of the stencil. One magnet per port, dead
//   centre, so a cable lands in the middle of the socket.
//
// - The face as PNG, rendered here by the browser. OmniGraffle embeds images as
//   files; a browser cannot write PDF, and PNG at 8 px/mm tested sharp.
//
// - The image registry. OmniGraffle resolves `ImageID: n` to the nth name in
//   the document's `ImageList`; a file merely being in the zip is not enough.
//   One empty `ImageLinkBack` per image and `ImageCounter` the next free id, as
//   a known-working stencil has them (davidfsmith/AWS-OmniGraffle-Stencils).
//
// - The single-file zipped format, which OmniGraffle 7.16 and later open and
//   which it offers to upgrade older package stencils to. It is also the only
//   form a browser can hand over as one download.
//
// A FACE THAT DRAWS BLANK is almost certainly a document open READ ONLY:
// OmniGraffle will not paint images there, though it still shows them in the
// sidebar thumbnails. That cost three rounds of the prototype.

import { readDrawing } from './zones.js';
import { normalise } from './marks.js';

const PT = 72 / 25.4;             // points per millimetre - faces are true size
const GAP = 36;                   // points between stencil items
const ROW = 1300;                 // points a row of small items may run to
// Past this many pixels Safari's canvas returns nothing at all. A face is
// drawn at the density asked for unless it would exceed it, and then at the
// highest density that fits - reported, not silent.
const CANVAS_AREA = 16e6;

const TINT = {port: [0, 0.627, 1, 0.22], bay: [0.961, 0.651, 0.137, 0.16]};

// ── property list ────────────────────────────────────────────────────────
// XML, which OmniGraffle reads inside the zip as it does a binary one. A value
// wrapped by real() is written as <real> even when it is whole; everything else
// that is a whole number is an <integer>.
const REAL = Symbol('real');
const real = v => ({[REAL]: v});
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function node(v, ind) {
  const pad = '\t'.repeat(ind);
  if (v === true) return `${pad}<true/>`;
  if (v === false) return `${pad}<false/>`;
  if (v && typeof v === 'object' && REAL in v) return `${pad}<real>${+v[REAL]}</real>`;
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) throw new Error(`plist: not a finite number: ${v}`);
    return Number.isInteger(v) ? `${pad}<integer>${v}</integer>` : `${pad}<real>${v}</real>`;
  }
  if (typeof v === 'string') return `${pad}<string>${esc(v)}</string>`;
  if (Array.isArray(v)) {
    return v.length ? `${pad}<array>\n${v.map(x => node(x, ind + 1)).join('\n')}\n${pad}</array>`
                    : `${pad}<array/>`;
  }
  if (v && typeof v === 'object') {
    const keys = Object.keys(v).filter(k => v[k] !== undefined && v[k] !== null);
    return keys.length
      ? `${pad}<dict>\n${keys.map(k => `${pad}\t<key>${esc(k)}</key>\n${node(v[k], ind + 1)}`)
          .join('\n')}\n${pad}</dict>`
      : `${pad}<dict/>`;
  }
  throw new Error(`plist: cannot write ${typeof v}`);
}

export function plist(v) {
  return '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ' +
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n' +
    `<plist version="1.0">\n${node(v, 0)}\n</plist>\n`;
}

// ── zip ──────────────────────────────────────────────────────────────────
// Stored, not deflated: the PNGs are compressed already, and a stored entry is
// the one every zip reader agrees on. UTF-8 names (bit 11), no zip64 - a
// stencil past 4 GB is not a stencil anyone should be opening.
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
export function crc32(b) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

export function zipStore(files, when = new Date()) {
  const enc = new TextEncoder();
  const time = (when.getHours() << 11) | (when.getMinutes() << 5) | (when.getSeconds() >> 1);
  const date = ((Math.max(1980, when.getFullYear()) - 1980) << 9) |
               ((when.getMonth() + 1) << 5) | when.getDate();
  const local = [], central = [];
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name), data = f.data, crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
    lh.setUint16(8, 0, true); lh.setUint16(10, time, true); lh.setUint16(12, date, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
    lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
    local.push(new Uint8Array(lh.buffer), name, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true);
    ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true); ch.setUint16(12, time, true);
    ch.setUint16(14, date, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true);
    ch.setUint32(24, data.length, true); ch.setUint16(28, name.length, true);
    ch.setUint32(42, offset, true);
    central.push(new Uint8Array(ch.buffer), name);
    offset += 30 + name.length + data.length;
  }
  const cdSize = central.reduce((a, b) => a + b.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true);
  end.setUint16(10, files.length, true); end.setUint32(12, cdSize, true);
  end.setUint32(16, offset, true);
  const parts = [...local, ...central, new Uint8Array(end.buffer)];
  const out = new Uint8Array(parts.reduce((a, b) => a + b.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

// ── the face, as a picture ───────────────────────────────────────────────
/** The compiled face as PNG bytes, at `pxmm` pixels per millimetre or the
 *  most that fits a browser canvas. Resolves {png, px: [w, h], density}. */
export async function rasterize(svgText, vb, pxmm = 8) {
  const w = vb[2], h = vb[3];
  const density = w * h * pxmm * pxmm > CANVAS_AREA ? Math.sqrt(CANVAS_AREA / (w * h)) : pxmm;
  const W = Math.max(1, Math.round(w * density)), H = Math.max(1, Math.round(h * density));
  const url = URL.createObjectURL(new Blob([svgText], {type: 'image/svg+xml'}));
  try {
    const img = new Image();
    await new Promise((ok, fail) => {
      img.onload = ok;
      img.onerror = () => fail(new Error('the face would not render'));
      img.src = url;
    });
    const cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    cv.getContext('2d').drawImage(img, 0, 0, W, H);
    const blob = await new Promise(r => cv.toBlob(r, 'image/png'));
    if (!blob) throw new Error(`the browser refused a ${W}x${H} image`);
    return {png: new Uint8Array(await blob.arrayBuffer()), px: [W, H], density};
  } finally {
    URL.revokeObjectURL(url);
  }
}

// ── the document ─────────────────────────────────────────────────────────
const num = v => (Math.round(v * 1e4) / 1e4).toString();
const rect = (x, y, w, h) => `{{${num(x)}, ${num(y)}}, {${num(w)}, ${num(h)}}}`;
const noDraw = () => ({fill: {Draws: 'NO'}, stroke: {Draws: 'NO'}, shadow: {Draws: 'NO'}});
const color = ([r, g, b, a]) => ({r: real(r), g: real(g), b: real(b), a: real(a), space: 'srgb'});

function zoneShape(id, z, ox, oy, vb, item, tinted) {
  const style = tinted
    ? {fill: {Color: color(TINT[z.cls])},
       stroke: {Color: color(TINT[z.cls]), Width: real(0.5)}, shadow: {Draws: 'NO'}}
    : noDraw();
  const info = {'portrayal-device': item.ref, 'portrayal-face': item.face,
                'portrayal-path': z.path || z.id, 'portrayal-class': z.cls};
  for (const k of ['group', 'media', 'speed', 'model']) if (z[k]) info[`portrayal-${k}`] = String(z[k]);
  return {
    Class: 'ShapedGraphic', ID: id, Shape: 'Rectangle', Name: z.path || z.id,
    Bounds: rect(ox + (z.x - vb[0]) * PT, oy + (z.y - vb[1]) * PT,
                 Math.max(z.w, 0.5) * PT, Math.max(z.h, 0.5) * PT),
    Magnets: ['{0, 0}'],
    Style: style,
    UserInfo: info,
  };
}

function sheet(title, uniqueId, graphics, w, h) {
  return {
    ActiveLayerIndex: 0, AutoAdjust: 6, AutosizingMargin: 1,
    BackgroundGraphic: {Bounds: rect(0, 0, w, h), Class: 'GraffleShapes.CanvasBackgroundGraphic',
                        ID: 0, Style: {shadow: {Draws: 'NO'}, stroke: {Draws: 'NO'}}},
    BaseZoom: 0, CanvasDimensionsOrigin: '{0, 0}', CanvasOrigin: '{0, 0}',
    CanvasSize: `{${num(w)}, ${num(h)}}`, CanvasSizingMode: 1,
    ColumnAlign: 0, ColumnSpacing: real(36), DisplayScale: '1.0 pt = 1.0 px',
    GraphicsList: graphics,
    GridInfo: {ShowsGrid: 'YES', SnapsToGrid: 'YES'},
    KeepToScale: false,
    Layers: [{Lock: false, Name: 'Layer 1', Print: true, View: true}],
    Orientation: 2, PrintOnePage: false, RowAlign: 0, RowSpacing: real(36),
    SheetTitle: title, UniqueID: uniqueId, VPages: 1,
  };
}

/**
 * The stencil, as the bytes of a zipped single-file `.gstencil`.
 *
 *   sheets  [{title, items: [{label, png, vb, ports, face, ref, version}]}]
 *           One sheet per group in OmniGraffle's stencil sidebar; each item is
 *           one draggable device face or card, true size, ports in front.
 */
export function buildStencil(sheets, {tinted = false, generated = new Date()} = {}) {
  const enc = new TextEncoder();
  const images = [], out = [];
  let id = 1;
  sheets.forEach((sh, si) => {
    const graphics = [];
    const widest = Math.max(...sh.items.map(it => it.vb[2] * PT), 0);
    const limit = Math.max(ROW, widest);
    let x = 0, y = 0, rowH = 0, right = 0;
    for (const it of sh.items) {
      const w = it.vb[2] * PT, h = it.vb[3] * PT;
      if (x > 0 && x + w > limit) { x = 0; y += rowH + GAP; rowH = 0; }
      images.push({name: `image${images.length + 1}.png`, data: it.png});
      const imageId = images.length;
      // FRONT OF THE Z-ORDER FIRST: OmniGraffle paints the first graphic on
      // top, the reverse of SVG. Ports, then bays, then the picture behind.
      const kids = [];
      for (const cls of ['port', 'bay']) {
        for (const z of it.ports) if (z.cls === cls) kids.push(zoneShape(id++, z, x, y, it.vb, it, tinted));
      }
      kids.push({
        Class: 'ShapedGraphic', ID: id++, ImageID: imageId, Name: `${it.label} face`,
        Bounds: rect(x, y, w, h), ManualSizeImage: 'NO', StretchImage: true,
        Magnets: [], Style: noDraw(),
      });
      graphics.push({
        Class: 'Group', ID: id++, Name: it.label, Graphics: kids, Style: noDraw(),
        UserInfo: {'portrayal-device': it.ref, 'portrayal-face': it.face,
                   'portrayal-version': it.version ? String(it.version) : undefined,
                   'portrayal-generated': generated.toISOString().slice(0, 10)},
      });
      x += w + GAP; rowH = Math.max(rowH, h); right = Math.max(right, x - GAP);
    }
    out.push(sheet(sh.title, si + 1, graphics, right + GAP, y + rowH + GAP));
  });
  const doc = {
    ApplicationVersion: ['com.omnigroup.OmniGraffle7.MacAppStore', '192.21'],
    FileType: 'zipped',
    GraphDocumentVersion: 16,
    GuidesLocked: 'NO', GuidesVisible: 'YES',
    ImageCounter: images.length + 1,
    ImageLinkBack: images.map(() => ({})),
    ImageList: images.map(i => i.name),
    LinksVisible: 'NO', MagnetsVisible: 'NO', MasterSheets: [],
    ModificationDate: generated.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' +0000'),
    Modifier: 'portrayal.dev',
    MovementHandleVisible: 'NO', NotesVisible: 'NO', OriginVisible: 'NO',
    PageBreaks: 'NO', ReadOnly: 'NO',
    Sheets: out,
    SmartAlignmentGuidesActive: 'NO', SmartDistanceGuidesActive: 'NO',
    UseEntirePage: false, useNotesKey: true,
  };
  return zipStore([{name: 'data.plist', data: enc.encode(plist(doc))}, ...images], generated);
}

/**
 * A live drawing, as it stands, as a one-item OmniGraffle stencil.
 *
 * `doc` is a marks document, as for drawio.toDrawio: what is highlighted, lit,
 * labelled or cropped is in the picture, and ports outside a crop are left out.
 * The picture is PNG, so a blinking lamp is held at its lit phase - the one
 * marks.toSvg freezes every lamp at.
 *
 * @returns {Promise<{bytes, name, ports, density}>}  the .gstencil's bytes, a
 *   name for it, how many magnetised shapes it carries, and the px/mm the face
 *   was drawn at (less than asked when the face would not fit a canvas at that
 *   density). Every port and every bay is a shape with a magnet - a bay holding
 *   a card included, unlike draw.io's container - so `ports` counts them all,
 *   and differs from toDrawio's on a chassis with cards seated.
 */
export async function toGraffle(svgRoot, doc = {}, {pxmm = 8, name, tinted = false,
                                                    generated = new Date()} = {}) {
  const d = normalise(doc);
  const {text, vb, ports} = readDrawing(svgRoot, d);
  const title = name || [d.device, d.config, d.view].filter(Boolean).join(' ') || 'drawing';
  const r = await rasterize(text, vb, pxmm);
  const bytes = buildStencil([{title, items: [{
    label: title, png: r.png, vb, ports, face: d.view || undefined, ref: d.device || undefined,
  }]}], {tinted, generated});
  return {bytes, name: title, ports: ports.length, density: r.density};
}
