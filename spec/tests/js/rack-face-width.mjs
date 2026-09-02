// A face is drawn at ITS OWN size, not at the size of the plane it sits on.
//
// The R740xd's front is the 482.6 mm RACK FACE - Dell builds the mounting
// flanges into the faceplate and puts the VGA, the power button and the health
// lamp in them - over a 434 mm body. relief.js took its width from the chassis,
// so it rasterised a 482.6 mm drawing into a 434 mm canvas (10% narrow) and
// converted every feature's x against the wrong centre:
//
//     LX = x + w/2 - fw/2
//
// with fw = 434 that puts a port at x 470 at +253, against a box edge at +217 -
// 36 mm off the end, in mid-air. That is the floating USB and VGA.
//
// This exercises the arithmetic without a browser: the same expression, at both
// widths, for the r740xd's real right-hand ports and for a face whose drawing
// already matches its plane (which is every other face in the library, and must
// not move).
import assert from 'node:assert';

const VIEWBOX = /viewBox\s*=\s*"\s*[-\d.eE+]+\s+[-\d.eE+]+\s+([\d.eE+-]+)\s+([\d.eE+-]+)/;

// the rule relief.js now applies
function drawnSize(svgText, planeW, planeH) {
  const m = VIEWBOX.exec(svgText);
  if (m) {
    const w = parseFloat(m[1]), h = parseFloat(m[2]);
    if (w > 0 && h > 0) return [w, h];
  }
  return [planeW, planeH];
}

const LX = (x, w, fw) => x + w / 2 - fw / 2;

const CHASSIS_W = 434.0;
const RACK_FACE = '<svg width="482.6mm" height="86.8mm" viewBox="0 0 482.6 86.8">';
const PLAIN_REAR = '<svg width="434.0mm" height="86.8mm" viewBox="0 0 434 86.8">';

// --- the rack face reports its own width -----------------------------------
const [fw, fh] = drawnSize(RACK_FACE, CHASSIS_W, 86.8);
assert.strictEqual(fw, 482.6, 'the drawing states 482.6 and must be believed');
assert.strictEqual(fh, 86.8);

// --- a face that already matches its plane must not move --------------------
const [rw, rh] = drawnSize(PLAIN_REAR, CHASSIS_W, 86.8);
assert.strictEqual(rw, CHASSIS_W, 'an ordinary face keeps its plane width');
assert.strictEqual(rh, 86.8);

// --- and one with no viewBox at all falls back ------------------------------
const [nw] = drawnSize('<svg width="434mm">', CHASSIS_W, 86.8);
assert.strictEqual(nw, CHASSIS_W, 'no viewBox -> the plane, as before');

// --- the ports that were floating -------------------------------------------
// vga sits at x 469.435 w 11.40; usb-1 at 460.40 w 4.5 (device.yaml, rear of
// the front panel's cutout list). Half the BODY is 217; half the FACE is 241.3.
const PORTS = [
  {id: 'vga', x: 469.435, w: 11.40},
  {id: 'usb-1', x: 460.40, w: 4.5},
  {id: 'power-btn', x: 458.80, w: 8.34},
];
const bodyEdge = CHASSIS_W / 2;          // +217.0
const faceEdge = fw / 2;                 // +241.3

for (const p of PORTS) {
  const wrong = LX(p.x, p.w, CHASSIS_W);
  const right = LX(p.x, p.w, fw);
  assert.ok(wrong > bodyEdge,
    `${p.id}: the old maths must land OUTSIDE the body box to reproduce the bug`);
  assert.ok(right <= faceEdge,
    `${p.id}: the new maths must land on the face, at ${right}`);
  assert.ok(right < wrong,
    `${p.id}: the fix moves it inboard, not outboard`);
}

// the ear ports are outboard of the BODY even when placed correctly - which is
// the whole point: they are in the flange, and the flange needs a plate under it
const vgaRight = LX(469.435, 11.40, fw);
assert.ok(vgaRight > bodyEdge,
  'the VGA is genuinely outside the 434 body - that is why a plate is needed');

console.log(JSON.stringify({
  drawn: [fw, fh],
  bodyEdge,
  faceEdge,
  vga: {wrong: LX(469.435, 11.40, CHASSIS_W), right: vgaRight},
  ordinaryFaceUnchanged: rw === CHASSIS_W,
}));
