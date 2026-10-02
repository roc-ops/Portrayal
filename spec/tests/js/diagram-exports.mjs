// The draw.io and OmniGraffle writers, run on hand-built zones.
//
// What is tested here is what needs no DOM: where a port's cell lands, which
// zones survive a crop, the file each writer produces. Reading a face back out
// of an SVG (readSvg, readDrawing) needs a real one, and is the browser's to
// check. The output is one JSON line; test_diagram_exports_js.py asserts on it.
const drawio = await import('../../../kit/drawio.js');
const og = await import('../../../kit/omnigraffle.js');
const {within, portsOf} = await import('../../../kit/zones.js');

const out = {};

// An optic's face stands its bail above y=0: a viewBox that does not start at
// the origin. One port at the viewBox's corner, one bay with a port inside it.
const vb = [0, -4.5, 18, 14];
const zones = [
  {id: 'port-1', cls: 'port', path: 'port-1', x: 0, y: -4.5, w: 4, h: 2},
  {id: 'slot-1', cls: 'bay', path: 'slot-1', x: 10, y: 0, w: 8, h: 9.5},
  {id: 'slot-1--module--p0', cls: 'port', path: 'slot-1/module/p0', x: 12, y: 2, w: 2, h: 2},
  {id: 'slot-2', cls: 'bay', path: 'slot-2', x: 4, y: 5, w: 4, h: 4},
];
// No bezel in it, so splitCovers must not reach for a DOMParser.
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb.join(' ')}"/>`;

const geom = xml => {
  const got = {};
  const re = /id="([^"]+)"[^>]*>(?:<mxCell[^>]*>)?<mxGeometry x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g;
  for (const m of xml.matchAll(re)) got[m[1]] = m.slice(2).map(Number);
  const re2 = /<mxCell id="([^"]+)"[^>]*><mxGeometry x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g;
  for (const m of xml.matchAll(re2)) got[m[1]] ??= m.slice(2).map(Number);
  return got;
};

const cells = drawio.deviceCells('d', svg, vb, portsOf(zones, {bays: true}),
                                 0, 0, vb[2] * 2, vb[3] * 2).join('');
out.cells = geom(cells);
out.parents = Object.fromEntries([...cells.matchAll(/id="(d-[^"]+)"><mxCell[^>]*parent="([^"]+)"/g)]
  .map(m => [m[1], m[2]]));
out.order = portsOf(zones, {bays: true}).map(z => z.id);

// What toDrawio reports as connectable, against what deviceCells wrote: slot-1
// holds slot-1/module/p0, so it is a container and takes no line; slot-2 is
// empty and does. connectable() and the cells must agree.
out.connectable = {
  counted: drawio.connectable(portsOf(zones, {bays: true})),
  cells: (cells.match(/connectable=1;/g) || []).length,
  containers: (cells.match(/connectable=0;/g) || []).length,
  zones: portsOf(zones, {bays: true}).length,
};

// A crop over the middle: port-1 is outside it, slot-1 is cut through.
out.within = within(zones, [3, 0, 10, 6]).map(z => [z.id, z.x, z.y, z.w, z.h]);

// A library's JSON sits in an XML text node, and its comment must not close.
const lib = drawio.library([drawio.entry('A <b> & c', svg, vb, [])], 'made -- here');
out.library = {
  head: lib.slice(0, lib.indexOf('<mxlibrary>')),
  rawAngle: /<b>/.test(lib.slice(lib.indexOf('<mxlibrary>') + 11)),
  json: JSON.parse(lib.slice(lib.indexOf('<mxlibrary>') + 11, lib.lastIndexOf('</mxlibrary>'))
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'))[0].title,
};

const dia = drawio.diagram('one "device"', svg, vb, portsOf(zones, {bays: true}));
out.diagram = {
  head: dia.slice(0, dia.indexOf('<root>')),
  paths: [...dia.matchAll(/portrayal-path="([^"]+)"/g)].map(m => m[1]),
  tail: dia.slice(-26),
};

// ---------------------------------------------------------------- rack
// The defaults, and each option a rack builder can set: a group's own faces, a
// mounted device's own id, a rack's own numbering.
const face = {svg, vb, ports: []};
const mounted = (name, id) => ({name, id, u: 1, ru: 1, faces: {front: face, rear: face}});
const pagesOf = x => [...x.matchAll(/<diagram name="([^"]+)"/g)].map(m => m[1]);
const racksOf = x => [...x.matchAll(/<mxCell id="(g\d+r\d+-[a-z]+)"[^>]*style="([^"]*)"/g)]
  .map(m => [m[1], /numDisp=(\w+)/.exec(m[2])[1]]);
const plain = drawio.rackDiagram([{label: 'P', racks: [{label: 'R', mounted: [mounted('A')]}]}]);
const opts = drawio.rackDiagram([
  {label: 'Front', faces: ['front'], racks: [{label: 'R', numDisp: 'descend',
    mounted: [mounted('Same', 'dev-1'), mounted('Same', 'dev-2')]}]},
  {label: 'Rear', faces: ['rear'], racks: [{label: 'R', mounted: [mounted('Same', 'dev-1')]}]},
], {faces: ['front', 'rear']});
out.rack = {
  plain: {pages: pagesOf(plain), racks: racksOf(plain),
          device: /id="(A-g0r0-front)"/.exec(plain)?.[1] ?? null},
  opts: {pages: pagesOf(opts), racks: racksOf(opts),
         devices: [...opts.matchAll(/<mxCell id="([a-z0-9-]+-g\dr\d-[a-z]+)" value="Same"/g)].map(m => m[1])},
};

// ---------------------------------------------------------------- OmniGraffle
out.crc = og.crc32(new TextEncoder().encode('123456789')).toString(16);

const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47]);
const zip = og.buildStencil([{title: 'S', items: [{
  label: 'optic', png, vb, ports: portsOf(zones, {bays: true}), face: 'front', ref: 'x/y@1',
}]}], {generated: new Date(Date.UTC(2026, 9, 2))});

// Stored entries, so the zip can be walked by its local headers.
const dv = new DataView(zip.buffer, zip.byteOffset, zip.byteLength);
const files = {};
for (let at = 0; dv.getUint32(at, true) === 0x04034b50;) {
  const size = dv.getUint32(at + 18, true), n = dv.getUint16(at + 26, true);
  const name = new TextDecoder().decode(zip.subarray(at + 30, at + 30 + n));
  const data = zip.subarray(at + 30 + n, at + 30 + n + size);
  files[name] = {data, crcOk: og.crc32(data) === dv.getUint32(at + 14, true)};
  at += 30 + n + size;
}
const plist = new TextDecoder().decode(files['data.plist'].data);
const bounds = {};
// A dict's keys are written in the order the object has them: Name, Bounds.
for (const m of plist.matchAll(/<key>Name<\/key>\s*<string>([^<]+)<\/string>\s*<key>Bounds<\/key>\s*<string>([^<]+)<\/string>/g))
  bounds[m[1]] = m[2];
out.graffle = {
  files: Object.keys(files),
  crcOk: Object.values(files).every(f => f.crcOk),
  png: [...files['image1.png'].data],
  bounds,
  device: /<key>portrayal-device<\/key>\s*<string>x\/y@1<\/string>/.test(plist),
};

console.log(JSON.stringify(out));
