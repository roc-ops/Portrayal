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

// ---------------------------------------------------------------- cables
// A rack builder's plan: one page per face, two racks on the front page, a
// switch with a card seated in slot-2, a server whose NIC is on its rear, a
// device with no front drawing, and a patch panel in the next rack.
const sw = {svg, vb, ports: portsOf([
  {id: 'p0', cls: 'port', path: 'p0', x: 0, y: 0, w: 2, h: 2},
  {id: 'slot-2', cls: 'bay', path: 'slot-2', x: 8, y: 0, w: 8, h: 8},
  {id: 'slot-2--module--p0', cls: 'port', path: 'slot-2/module/p0', x: 10, y: 2, w: 2, h: 2},
], {bays: true})};
const srvFront = {svg, vb, ports: [{id: 'p0', cls: 'port', path: 'p0', x: 4, y: 4, w: 2, h: 2}]};
const srvRear = {svg, vb, ports: [{id: 'nic-1--p0', cls: 'port', path: 'nic-1/p0', x: 4, y: 4, w: 2, h: 2}]};
const swM = {name: 'sw', id: 'sw-1', u: 1, ru: 1, faces: {front: sw, rear: face}};
const srvM = {name: 'r740', id: 'srv-1', u: 3, ru: 2, faces: {front: srvFront, rear: srvRear}};
const plan = [
  {label: 'Front', faces: ['front'], racks: [
    {label: 'rack-2', mounted: [swM, srvM,
      {name: 'blank', id: 'blank-1', u: 6, ru: 1, faces: {rear: face}}]},
    {label: 'rack-3', mounted: [{name: 'pp', id: 'pp-1', u: 1, ru: 1, faces: {front: srvFront}}]}]},
  {label: 'Rear', faces: ['rear'], racks: [{label: 'rack-2', mounted: [swM, srvM]}]},
];
const end = (item, path, view) => ({item, path, view});
const cables = [
  {id: 'c1', a: end('sw-1', 'slot-2/module/p0', 'front'), b: end('srv-1', 'p0', 'front'),
   media: 'dac', purpose: 'uplink', label: 'up-1', length: {value: 2, unit: 'm', source: 'entered'}},
  {id: 'c2', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'nic-1/p0', 'rear'), media: 'os2'},
  {id: 'c3', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'p99', 'front')},
  {id: 'c4', a: end('ghost', 'p0', 'front'), b: end('sw-1', 'p0', 'front')},
  {id: 'c5', a: end('blank-1', 'p0', 'front'), b: end('sw-1', 'p0', 'front')},
  {id: 'c 6', a: end('sw-1', 'p0'), b: end('pp-1', 'p0', 'front'), media: 'sm', label: 'a <b>'},
  {id: 'c-6', a: end('srv-1', 'p0', 'front'), b: end('pp-1', 'p0', 'front'), media: 'mystery'},
];
const wiredXml = drawio.rackDiagram(plan, {cables, notes: ['caller note']});
const pageXml = wiredXml.split('<diagram ').slice(1);
const edgeRe = /<object label="([^"]*)"([^>]*) id="([^"]+)"><mxCell style="([^"]*)" edge="1" parent="1" source="([^"]+)" target="([^"]+)"/g;
const edgesOf = x => [...x.matchAll(edgeRe)].map(m => ({
  id: m[3], label: m[1], source: m[5], target: m[6],
  attrs: Object.fromEntries([...m[2].matchAll(/ ([a-z-]+)="([^"]*)"/g)].map(a => [a[1], a[2]])),
  stroke: /strokeColor=([^;]+);/.exec(m[4])?.[1] ?? null,
}));
const cellIds = x => new Set([...x.matchAll(/ id="([^"]+)"/g)].map(m => m[1]));
const valueOf = (x, id) => new RegExp(`<mxCell id="${id}" value="([^"]*)"`).exec(x)?.[1] ?? null;
const commentOf = x => /<!--\n([\s\S]*?)\n-->/.exec(x)?.[1] ?? null;
out.cables = {
  pages: pageXml.map(x => ({
    edges: edgesOf(x),
    // every source and target is a cell on the page the edge is on
    dangling: edgesOf(x).flatMap(e => [e.source, e.target]).filter(c => !cellIds(x).has(c)),
  })),
  far: {front: valueOf(pageXml[0], 'cable-c2-a-far'), rear: valueOf(pageXml[1], 'cable-c2-b-far')},
  farGeom: geom(pageXml[0])['cable-c2-a-far'],
  comment: commentOf(wiredXml),
  commentInside: wiredXml.startsWith('<mxfile host="portrayal"><!--'),
  notes: drawio.rackCables(plan, cables).notes,
  stable: drawio.rackDiagram(plan, {cables, notes: ['caller note']}) === wiredXml,
  none: drawio.rackDiagram(plan, {cables: []}) === drawio.rackDiagram(plan),
  styleFn: edgesOf(drawio.rackDiagram(plan, {cables: cables.slice(0, 1),
    cableStyle: c => `endArrow=none;strokeColor=#${c.purpose === 'uplink' ? 'ABCDEF' : '000000'};`}))
    .map(e => e.stroke),
  styleMap: edgesOf(drawio.rackDiagram(plan, {cables, cableStyle: {sm: '#123456'}}))
    .map(e => [e.id, e.stroke]),
};

// Ids that collide only after numbering or a stub suffix: a third cable named
// what the second was numbered to, and a same-page cable named what another
// cable's stub is called - in both orders.
const clash = [
  {id: 'c 6', a: end('sw-1', 'p0', 'front'), b: end('pp-1', 'p0', 'front')},
  {id: 'c-6', a: end('srv-1', 'p0', 'front'), b: end('pp-1', 'p0', 'front')},
  {id: 'c-6-2', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'p0', 'front')},
  {id: 'x', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'nic-1/p0', 'rear')},
  {id: 'x-a', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'p0', 'front')},
  {id: 'y-b', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'p0', 'front')},
  {id: 'y', a: end('sw-1', 'p0', 'front'), b: end('srv-1', 'nic-1/p0', 'rear')},
];
const clashXml = drawio.rackDiagram(plan, {cables: clash});
const clashIds = [...clashXml.matchAll(/ id="(cable-[^"]+)"/g)].map(m => m[1]);
out.clash = {
  ids: clashIds,
  cables: [...new Set([...clashXml.matchAll(/portrayal-cable="([^"]+)"/g)].map(m => m[1]))],
  notes: drawio.rackCables(plan, clash).notes,
};

// One device, as toDrawio writes it: an end names the drawing by leaving
// `item` out or by its name.
const one = [
  {id: 'k1', a: {path: 'p0'}, b: {item: 'S', path: 'slot-2/module/p0'}, media: 'cu'},
  {id: 'k2', a: {path: 'p0'}, b: {item: 'other', path: 'p0'}},
  {id: 'k3', a: {path: 'p0', view: 'rear'}, b: {path: 'slot-2/module/p0'}},
];
const oneXml = drawio.diagram('S', svg, vb, sw.ports, {cables: one, view: 'front'});
out.oneDevice = {edges: edgesOf(oneXml), comment: commentOf(oneXml)};

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
