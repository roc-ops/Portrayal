// kit/rack/view/ear-holes.js
// THE RAIL HOLES AN EAR IS FIXED AT. One answer for the 2D elevation
// (elevation.js) and the 3D rack (rack3d.js), so a body, its ears and its
// screws agree in both.
//
// WHERE A BODY IS, and the span its item fills, are the kit's (rack/fit.js
// itemBox: `lo` and `hi` in mm above the bottom of the rails, the body centred
// between them, always). The site kept its own answer until rack file version
// 4 (body-span.js: a body under one unit in the lower part of its unit, since
// a position was a whole unit); a position is a whole unit or a half now, the
// kit says which half, and that module is gone.
//
// THE HOLES are the kit's too (rack/rails.js holesIn(lo, hi): every rail hole
// an ear between two heights can use). A unit has three, at 6.35, 22.22 and
// 38.10 mm. An ear that covers a whole unit is drawn with a screw in its first
// and last, the middle one left empty, as it always was: two screws a unit an
// ear, the four a unit a device the BOM counts. A half unit holds one hole
// (its lower half the unit's first, its upper half the last; the middle hole
// is on the line between the halves, where the kit gives it to neither), so a
// half-unit panel has one screw an ear, and two such panels in one unit use
// that unit's two outer holes between them.
import {RU, HOLE_DY, holesIn} from '../rails.js';

/** The heights, in mm above the bottom of the rails, of the holes an ear over
 *  the span [lo, hi] is screwed at. */
export function earHoles(lo, hi) {
  const all = holesIn(lo, hi);
  const unit = y => Math.floor(y / RU + 1e-9);
  const at = (y, k) => Math.abs(y - unit(y) * RU - HOLE_DY[k]) < 0.01;
  const has = (y, k) => all.some(o => unit(o) === unit(y) && at(o, k));
  return all.filter(y => !at(y, 1) || !(has(y, 0) && has(y, 2)));
}
