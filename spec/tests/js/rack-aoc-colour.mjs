// spec/tests/js/rack-aoc-colour.mjs
// AN AOC IS AQUA, AND CAN BE TOLD FROM OM3 AND OM4 (#1028). It is the same
// multimode family as they are (a teal, hue within 15 degrees of theirs) at a
// clearly different lightness, and it differs from every other cable colour
// the explorer and the draw.io writer draw. Every colour here is read off the
// built tables (`COLORS`, `CABLE_COLOURS`), never copied from the source.
//
// The measures, stated:
//   - distance: CIE76 delta E in CIELAB (D65). 20 is the least that reads as
//     two colours on a cable a few pixels wide; OM4 against Cat 6 blue is 64.
//   - contrast: WCAG relative-luminance ratio against a stage, 3:1 as for a
//     graphical object. The explorer's dark stage is #101214, draw.io's page is
//     white.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as G from '../../../kit/rack/cable-geometry.js';
import {CABLE_COLOURS} from '../../../kit/drawio.js';

const MIN_DISTANCE = 20, MIN_CONTRAST = 3, DARK = '#101214', WHITE = '#ffffff';
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const luminance = h => { const [r, g, b] = rgb(h).map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const contrast = (a, b) => { const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const lab = h => {
  const [r, g, b] = rgb(h).map(lin);
  const xyz = [(0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b,
    (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883];
  const [fx, fy, fz] = xyz.map(t => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116));
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
};
const distance = (a, b) => Math.hypot(...lab(a).map((v, i) => v - lab(b)[i]));
const hue = h => { const [, a, b] = lab(h); return (Math.atan2(b, a) * 180 / Math.PI + 360) % 360; };

const entries = (o, prefix = '') => Object.entries(o).flatMap(([k, v]) =>
  (typeof v === 'string' ? [[prefix + k, v]] : entries(v, `${prefix}${k}.`)));
const others = entries(G.COLORS).filter(([k]) => k !== 'aoc');

test('an AOC with no colour stated is a colour of its own, a distance of 20 and more from every other COLORS entry, OM3 and OM4 included', () => {
  const aoc = G.colorOf({media: 'aoc'});
  assert.match(aoc, /^#[0-9a-f]{6}$/);
  assert.equal(aoc, G.COLORS.aoc);
  assert.ok(others.length >= 10);
  for (const [k, v] of others) assert.ok(distance(aoc, v) >= MIN_DISTANCE, `aoc ${aoc} against ${k} ${v}: ${distance(aoc, v).toFixed(1)}`);
});

test('an AOC is of the multimode aqua family: the hue of OM3 and OM4 within 15 degrees', () => {
  const d = Math.abs(hue(G.COLORS.aoc) - hue(G.COLORS.om4));
  assert.ok(Math.min(d, 360 - d) <= 15, `hue ${hue(G.COLORS.aoc).toFixed(0)} against ${hue(G.COLORS.om4).toFixed(0)}`);
  assert.equal(G.COLORS.om3, G.COLORS.om4);
});

test('an AOC reads on the explorer\'s dark stage and on a white page: 3:1 on each', () => {
  for (const stage of [DARK, WHITE]) assert.ok(contrast(G.COLORS.aoc, stage) >= MIN_CONTRAST, `aoc against ${stage}: ${contrast(G.COLORS.aoc, stage).toFixed(2)}`);
});

test('draw.io: the AOC stroke is the explorer\'s, and differs from OM3, OM4 and every other row of CABLE_COLOURS', () => {
  assert.equal(CABLE_COLOURS.aoc, G.colorOf({media: 'aoc'}));
  for (const [k, v] of Object.entries(CABLE_COLOURS)) if (k !== 'aoc') assert.ok(distance(CABLE_COLOURS.aoc, v) >= MIN_DISTANCE, `aoc against ${k} ${v}`);
  assert.notEqual(CABLE_COLOURS.aoc, CABLE_COLOURS.om3);
  assert.notEqual(CABLE_COLOURS.aoc, CABLE_COLOURS.om4);
});

test('every other row of CABLE_COLOURS is as the kit draws that media, as it stood before the AOC moved', () => {
  const OTHER = {dac: '#15171a', cu: '#e8c547', mm: '#e8c547', sm: '#e8c547', om1: '#e8c547', om2: '#e8c547', om3: '#2bb3c8',
    om4: '#2bb3c8', om5: '#9acd32', os1: '#e8c547', os2: '#e8c547', cat5e: '#e8c547', cat6: '#5aa7ff', cat6a: '#5aa7ff', default: '#e8c547'};
  assert.deepEqual({...CABLE_COLOURS, aoc: undefined}, {...OTHER, aoc: undefined});
});
