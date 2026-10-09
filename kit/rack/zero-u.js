// kit/rack/zero-u.js
// ZERO-U PARTS: WHAT STANDS BESIDE THE RACK (#926). Pure, like fit.js.
//
// A zero-U part takes no rack unit. It lives in `rack.zeroU`, never in
// `items` (model.js zeroUOf has the entry's shape), stands at an attachment
// point of the frame (`at`), and is fitted by fit.js fitsZeroU. Which mounts
// are zero-U parts is fit.js ZERO_U_MOUNTS: `rack-side` today, the vertical
// cable managers; a zero-U PDU is placed the same way. The commands that
// place, move and remove one are `zerou.*` in commands.js.
//
// This file holds what the drawings, the routes and the exports ask of one:
// where it is, as words and as x; whether a cable lane runs through it; and
// each placeable entry with what a drawing needs.

import {RU, RAIL_W, OPENING} from './rails.js';
import {isZeroUPart, zeroUUnits, zeroUSpan, zeroUSpanText} from './fit.js';
import {zeroUOf, zeroUBottom} from './model.js';

// The gap between a part and the upright it stands against: no source
// dimensions it (the FS ducts' `bracket-stand-off` gap), so it is drawn against
// the upright's outer face.
export const STANDOFF = 0;

// The side of the rack an attachment point is on, and the face of a four-post
// it is on (null on a two-post, whose one pair of uprights both panes see).
export const sideOfAt = at => (String(at).startsWith('right') ? 'right' : 'left');
export const faceOfAt = at => /-(front|rear)$/.exec(String(at))?.[1] ?? null;

export const zeroUName = (z, chassisOf) => z.label || chassisOf(z.ref)?.model || z.ref;
// "beside the rack at left, U1-U45", or "between racks at ...".
export const whereText = (rack, z, chassisOf) =>
  `${z.between ? 'between racks' : 'beside the rack'} at ${z.at}, ${zeroUSpanText(rack.frame, z, chassisOf)}`;

// Each zero-U part the catalogue knows as one, with what a drawing or an
// export needs: its bottom U (`ru`), the units it runs beside (`u`), and its
// chassis width and drawn height in mm. An entry of another shape, or whose
// part is not a zero-U part, is not listed: an export says it is left out
// (export-data.js rackNotes).
export function zeroUEntries(rack, chassisOf) {
  return zeroUOf(rack).filter(z => isZeroUPart(chassisOf(z.ref))).map(z => {
    const c = chassisOf(z.ref), u = zeroUUnits(c);
    return {id: z.id, ref: z.ref, cfg: z.cfg || c.default || '', label: zeroUName(z, chassisOf), at: z.at,
            between: z.between === true, ru: zeroUBottom(z), u, w: Number(c.w) || 0,
            h: Number(c.h) || u * RU, mount: c.mount};
  });
}

// ── lanes through a part ─────────────────────────────────────────────────
// The cable lane beside an upright runs through a zero-U part standing there
// when the part is a pathway (it declares guides, as a duct does): a lane
// waypoint at a U the part spans is in its channel, at its centre line. A part
// that is no pathway (a PDU) leaves the lane where it was, in the gutter.
export const carriesLane = c => isZeroUPart(c) && Object.values(c?.guides || {}).some(l => Array.isArray(l) && l.length);
export function zeroUOnLane(rack, lane, ru, chassisOf) {
  return zeroUOf(rack).find(z => z.at === lane && carriesLane(chassisOf(z.ref))
    && ru >= zeroUSpan(z, chassisOf)[0] && ru <= zeroUSpan(z, chassisOf)[1]) ?? null;
}
// Its centre line across the rack, in mm from the rack's centre line, right as
// seen from the front: outside the rail, the stand-off and half its width out.
export function zeroUX(z, chassisOf) {
  const w = Number(chassisOf(z.ref)?.w) || 0, s = sideOfAt(z.at) === 'left' ? -1 : 1;
  return s * (OPENING / 2 + RAIL_W + STANDOFF + w / 2);
}

// Does a run of lane waypoints pass through a part? A waypoint on its lane at a
// U it spans, or two in a row on its lane whose run crosses its span.
export function runsThrough(waypoints, z, chassisOf) {
  const [lo, hi] = zeroUSpan(z, chassisOf);
  return waypoints.some((w, k) => {
    if (w.lane !== z.at) return false;
    if (w.ru >= lo && w.ru <= hi) return true;
    const nx = waypoints[k + 1];
    return nx?.lane === z.at && Math.min(w.ru, nx.ru) <= hi && Math.max(w.ru, nx.ru) >= lo;
  });
}
