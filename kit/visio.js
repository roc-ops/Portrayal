// Portrayal -> Visio, as a .vsdx built in the browser.
//
// The same representation the draw.io and OmniGraffle exports settled on
// (drawio.js, omnigraffle.js): the face as one picture, plus one invisible
// shape over every port and bay, so a cable drawn to a port glues to THAT port.
// Visio's own words for it are a Shape with a Connection section, and a shape's
// Shape Data; PRIOR-ART.md section 6 names both as the mechanism.
//
// What each piece is, and why:
//
// - A shape per port or bay, NAMED BY ITS ADDRESS (`NameU` and `Name` are the
//   drawing's `data-path`: `port-12`, `slot-2/module/p0`). The same address is
//   a row of the shape's Shape Data (`portrayal-path`), with the class and the
//   media, speed, group and module the drawing states. A script reading the
//   file finds a port by name or by data; it never reverses a coordinate. That
//   is the acceptance test of the exporter tab: can a named port still be found?
//
// - One connection point per shape, dead centre, written as a formula
//   (`Width*0.5`, `Height*0.5`) so it stays centred when the shape is resized.
//
// - The face as PNG, drawn here by the browser (omnigraffle.js `rasterize`).
//   Visio takes a bitmap as a Foreign shape; it has no place for an SVG, and
//   re-emitting vector geometry would be the full SVG-to-Visio conversion that
//   PRIOR-ART.md defers. The geometry here is the library's own: nothing is read
//   from a vendor's stencil, which forbids redistribution (spec/VISIO-INTAKE.md).
//
// - The package is a zip of XML parts (the Open Packaging Convention), written
//   with omnigraffle.js's `zipStore`; no second zip writer. Parts are stored,
//   not deflated: a PNG is compressed already.
//
// One page per drawing, the page the size of the face in inches (Visio's unit),
// y up from the page's bottom, where a drawing's y runs down.

import { readDrawing, exportName } from './zones.js';
import { normalise } from './marks.js';
import { zipStore, rasterize } from './omnigraffle.js';

const IN = 25.4;                      // millimetres to an inch
const MIN = 0.5;                      // the smallest shape, in millimetres (as drawio.js, omnigraffle.js)

const NS = 'http://schemas.microsoft.com/office/visio/2011/1/core';
const R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const PKG = 'http://schemas.openxmlformats.org/package/2006/relationships';
const CT = 'http://schemas.openxmlformats.org/package/2006/content-types';
const VREL = 'http://schemas.microsoft.com/visio/2010/relationships';
const HEAD = '<?xml version="1.0" encoding="utf-8" ?>\n';

const esc = s => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const inch = mm => String(+(mm / IN).toFixed(6));

// ── shapes ───────────────────────────────────────────────────────────────
const cell = (n, v, f) => `<Cell N="${n}" V="${esc(v)}"${f ? ` F="${esc(f)}"` : ''}/>`;

/** Shape Data: one row a key, labelled with the key as the drawing spells it. */
function shapeData(info) {
  const rows = Object.entries(info).filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `<Row N="${esc(k.replace(/-/g, '_'))}">${cell('Label', k)}${cell('Type', 0)}` +
      `<Cell N="Value" V="${esc(v)}" U="STR"/></Row>`);
  return rows.length ? `<Section N="Property">${rows.join('')}</Section>` : '';
}

// A rectangle, the way Visio draws one: from the bottom left corner round.
const rect = (w, h) => '<Section N="Geometry" IX="0">' +
  '<Cell N="NoFill" V="1"/><Cell N="NoLine" V="1"/><Cell N="NoShow" V="0"/>' +
  '<Cell N="NoSnap" V="0"/><Cell N="NoQuickDrag" V="0"/>' +
  '<Row T="MoveTo" IX="1"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>' +
  `<Row T="LineTo" IX="2"><Cell N="X" V="${w}" F="Width"/><Cell N="Y" V="0"/></Row>` +
  `<Row T="LineTo" IX="3"><Cell N="X" V="${w}" F="Width"/><Cell N="Y" V="${h}" F="Height"/></Row>` +
  `<Row T="LineTo" IX="4"><Cell N="X" V="0"/><Cell N="Y" V="${h}" F="Height"/></Row>` +
  '<Row T="LineTo" IX="5"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row></Section>';

const place = (pinX, pinY, w, h) =>
  cell('PinX', pinX) + cell('PinY', pinY) + cell('Width', w) + cell('Height', h) +
  cell('LocPinX', +(w / 2).toFixed(6), 'Width*0.5') + cell('LocPinY', +(h / 2).toFixed(6), 'Height*0.5');

/** A port or a bay: invisible, connectable, named by its address. `H` is the
 *  page's height in millimetres, because Visio's y runs up from the bottom. */
function zoneShape(id, z, vb, H) {
  const w = Math.max(z.w, MIN), h = Math.max(z.h, MIN);
  const cx = z.x - vb[0] + w / 2, cy = H - (z.y - vb[1] + h / 2);
  const name = exportName(z);
  const info = {'portrayal-path': name, 'portrayal-class': z.cls};
  for (const k of ['group', 'media', 'speed', 'model']) if (z[k]) info[`portrayal-${k}`] = String(z[k]);
  if (z.ref) info['portrayal-ref'] = String(z.ref);
  return `<Shape ID="${id}" NameU="${esc(name)}" Name="${esc(name)}" Type="Shape">` +
    place(inch(cx), inch(cy), inch(w), inch(h)) + shapeData(info) +
    `<Section N="Connection"><Row IX="1">` +
    `${cell('X', +(w / IN / 2).toFixed(6), 'Width*0.5')}${cell('Y', +(h / IN / 2).toFixed(6), 'Height*0.5')}` +
    `${cell('DirX', 0)}${cell('DirY', 0)}${cell('Type', 0)}</Row></Section>` +
    rect(inch(w), inch(h)) + '</Shape>';
}

function pageXml(it, imageRid, generated) {
  const W = it.vb[2], H = it.vb[3];
  const name = `${it.label} face`;
  const info = {'portrayal-device': it.ref, 'portrayal-face': it.face,
                'portrayal-version': it.version ? String(it.version) : undefined,
                'portrayal-generated': generated.toISOString().slice(0, 10)};
  let id = 4;                         // a shape's ID is 4 or more ([MS-VSDX] 2.3.4.2.88)
  const pic = `<Shape ID="${id++}" NameU="${esc(name)}" Name="${esc(name)}" Type="Foreign">` +
    place(inch(W / 2), inch(H / 2), inch(W), inch(H)) +
    // the picture fills the shape ([MS-VSDX] 2.2.6: ImgOffsetX/Y, ImgWidth/Height)
    cell('ImgOffsetX', 0) + cell('ImgOffsetY', 0) +
    cell('ImgWidth', inch(W), 'Width') + cell('ImgHeight', inch(H), 'Height') + shapeData(info) +
    `<ForeignData ForeignType="Bitmap" CompressionType="PNG"><Rel r:id="${imageRid}"/></ForeignData></Shape>`;
  // THE FIRST SHAPE IS PAINTED UNDERNEATH in Visio (the reverse of OmniGraffle):
  // the picture, then the bays, then the ports on top of them.
  const rank = z => (z.cls === 'bay' ? 0 : 1);
  const zones = [...it.ports].sort((a, b) => rank(a) - rank(b));
  const kids = zones.map(z => zoneShape(id++, z, it.vb, H));
  return `${HEAD}<PageContents xmlns="${NS}" xmlns:r="${R}" xml:space="preserve"><Shapes>` +
    `${pic}${kids.join('')}</Shapes></PageContents>`;
}

// ── the package ──────────────────────────────────────────────────────────
const rels = list => `${HEAD}<Relationships xmlns="${PKG}">` +
  list.map(([id, type, target]) => `<Relationship Id="${id}" Type="${type}" Target="${esc(target)}"/>`).join('') +
  '</Relationships>';

const DOCUMENT = `${HEAD}<VisioDocument xmlns="${NS}" xmlns:r="${R}" xml:space="preserve">` +
  '<DocumentSettings TopPage="0" DefaultTextStyle="0" DefaultLineStyle="0" DefaultFillStyle="0"/>' +
  '<Colors/><FaceNames/><StyleSheets><StyleSheet ID="0" NameU="No Style" Name="No Style">' +
  '<Cell N="EnableLineProps" V="1"/><Cell N="EnableFillProps" V="1"/><Cell N="EnableTextProps" V="1"/>' +
  '</StyleSheet></StyleSheets></VisioDocument>';

/**
 * The drawing, as the bytes of a `.vsdx`.
 *
 *   items  [{label, png, vb, ports, face, ref, version}]
 *          One page per item: a device face or a card, true size, its ports and
 *          bays over it. The items are `omnigraffle.buildStencil`'s.
 */
export function buildVsdx(items, {generated = new Date()} = {}) {
  const enc = new TextEncoder();
  const text = s => enc.encode(s);
  const files = [], pages = [], pageRels = [];
  items.forEach((it, i) => {
    const n = i + 1;
    files.push({name: `visio/pages/page${n}.xml`, data: text(pageXml(it, 'rId1', generated))});
    files.push({name: `visio/pages/_rels/page${n}.xml.rels`,
                data: text(rels([['rId1', `${R}/image`, `../media/image${n}.png`]]))});
    files.push({name: `visio/media/image${n}.png`, data: it.png});
    pages.push(`<Page ID="${n}" NameU="${esc(it.label)}" Name="${esc(it.label)}">` +
      `<PageSheet LineStyle="0" FillStyle="0" TextStyle="0">` +
      `${cell('PageWidth', inch(it.vb[2]))}${cell('PageHeight', inch(it.vb[3]))}` +
      `<Cell N="PageScale" V="1" U="IN"/><Cell N="DrawingScale" V="1" U="IN"/>` +
      `${cell('DrawingSizeType', 3)}${cell('DrawingScaleType', 0)}</PageSheet><Rel r:id="rId${n}"/></Page>`);
    pageRels.push([`rId${n}`, `${VREL}/page`, `page${n}.xml`]);
  });
  const title = items.map(it => it.label).join(', ');
  const stamp = generated.toISOString().replace(/\.\d+Z$/, 'Z');
  const types = `${HEAD}<Types xmlns="${CT}">` +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Default Extension="png" ContentType="image/png"/>' +
    '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>' +
    '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>' +
    items.map((_, i) => `<Override PartName="/visio/pages/page${i + 1}.xml" ContentType="application/vnd.ms-visio.page+xml"/>`).join('') +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '</Types>';
  const core = `${HEAD}<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ` +
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
    `<dc:title>${esc(title)}</dc:title><dc:creator>portrayal.dev</dc:creator>` +
    `<dcterms:created xsi:type="dcterms:W3CDTF">${stamp}</dcterms:created></cp:coreProperties>`;
  const head = [
    {name: '[Content_Types].xml', data: text(types)},
    {name: '_rels/.rels', data: text(rels([
      ['rId1', `${VREL}/document`, 'visio/document.xml'],
      ['rId2', 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties', 'docProps/core.xml'],
    ]))},
    {name: 'docProps/core.xml', data: text(core)},
    {name: 'visio/document.xml', data: text(DOCUMENT)},
    {name: 'visio/_rels/document.xml.rels', data: text(rels([['rId1', `${VREL}/pages`, 'pages/pages.xml']]))},
    {name: 'visio/pages/pages.xml',
     data: text(`${HEAD}<Pages xmlns="${NS}" xmlns:r="${R}" xml:space="preserve">${pages.join('')}</Pages>`)},
    {name: 'visio/pages/_rels/pages.xml.rels', data: text(rels(pageRels))},
  ];
  return zipStore([...head, ...files], generated);
}

/**
 * A live drawing, as it stands, as a one-page Visio document.
 *
 * `doc` is a marks document, as for drawio.toDrawio and omnigraffle.toGraffle:
 * what is highlighted, lit, labelled or cropped is in the picture, and ports
 * outside a crop are left out. The picture is PNG, so a blinking lamp is held
 * at its lit phase, the one marks.toSvg freezes every lamp at.
 *
 * @returns {Promise<{bytes, name, ports, density}>}  the .vsdx's bytes, a name
 *   for it, how many shapes carry a connection point - every port and every bay,
 *   as toGraffle counts them - and the px/mm the face was drawn at.
 */
export async function toVisio(svgRoot, doc = {}, {pxmm = 8, name, generated = new Date()} = {}) {
  const d = normalise(doc);
  const {text, vb, ports} = readDrawing(svgRoot, d);
  const title = name || [d.device, d.config, d.view].filter(Boolean).join(' ') || 'drawing';
  const r = await rasterize(text, vb, pxmm);
  const bytes = buildVsdx([{
    label: title, png: r.png, vb, ports, face: d.view || undefined, ref: d.device || undefined,
  }], {generated});
  return {bytes, name: title, ports: ports.length, density: r.density};
}
