// The Visio writer, run on hand-built zones.
//
// What is tested here is what needs no DOM: the file buildVsdx writes for zones
// it is handed, and that draw.io's writer finds the same names in the same
// zones. Reading a face out of an SVG (readDrawing) and drawing it to a PNG
// (rasterize) need a browser and are the browser's to check. The output is one
// JSON line; test_visio_export_js.py parses the file it carries.
const drawio = await import('../../../kit/drawio.js');
const visio = await import('../../../kit/visio.js');
const {portsOf} = await import('../../../kit/zones.js');

// A face whose viewBox does not start at the origin (an optic stands its bail
// above y=0), a card seated in a bay, an empty bay, and a port whose address
// holds every character an XML attribute must escape.
const vb = [0, -4.5, 18, 14];
const zones = [
  {id: 'port-1', cls: 'port', path: 'port-1', x: 0, y: -4.5, w: 4, h: 2,
   group: 'uplink', media: 'sfp+', speed: '10G'},
  {id: 'slot-1', cls: 'bay', path: 'slot-1', x: 10, y: 0, w: 8, h: 9.5, model: 'x/card@1'},
  {id: 'slot-1--module--p0', cls: 'port', path: 'slot-1/module/p0', x: 12, y: 2, w: 2, h: 2},
  {id: 'slot-2', cls: 'bay', path: 'slot-2', x: 4, y: 5, w: 4, h: 4},
  {id: 'odd', cls: 'port', path: 'a&b <c> "d"', x: 6, y: -4, w: 2, h: 2},
];
const ports = portsOf(zones, {bays: true});
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb.join(' ')}"/>`;
const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const when = new Date(Date.UTC(2026, 9, 2, 12, 0, 0));
const item = {label: 'S9510 front', png, vb, ports, face: 'front', ref: 'ufispace/s9510@1', version: '1.2.0'};

const bytes = visio.buildVsdx([item, {...item, label: 'second', face: 'rear'}], {generated: when});
const again = visio.buildVsdx([item, {...item, label: 'second', face: 'rear'}], {generated: when});

const b64 = u8 => Buffer.from(u8).toString('base64');

// The names draw.io writes for the same zones, from the cells it writes.
const cells = drawio.deviceCells('d', svg, vb, ports, 0, 0, vb[2] * 2, vb[3] * 2).join('');
const unesc = s => s.replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const drawioNames = [...cells.matchAll(/portrayal-path="([^"]+)"/g)].map(m => unesc(m[1]));

console.log(JSON.stringify({
  vsdx: b64(bytes),
  stable: b64(bytes) === b64(again),
  drawioNames,
  zoneNames: ports.map(z => z.path),
  exports: Object.keys(visio).sort(),
}));
