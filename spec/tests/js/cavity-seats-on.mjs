// A lifted cavity has to punch the surface it was lifted onto, or it is a well
// at the right depth behind an unbroken plate. smartoptics/dcp-404 is the case
// that found it: a faceplate 44 proud with four QSFP cages lifted onto it, all
// four invisible because a cage is a pure cavity with no `out` of its own.
//
// relief.js reads `location` at module scope and falls through to fetch, so both
// are stubbed the way relief-scope.mjs does it - the real module is exercised
// rather than its text asserted on.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg id="FETCHED"/>' });

const m = await import('../../../kit/relief.js');
const seats = m.cavitySeatsOn;

// the DCP-404 as built: a 205 x 44 plate standing 44 proud, cages lifted onto it
const plate = { x: 0, y: 0, w: 205, h: 44, out: 44 };
const cage = { x: 38.42, y: 29.3, w: 18.35, h: 8.5, lift: 44 };

const out = {
  // the case that was broken
  seatedCage: seats(cage, plate),

  // an unlifted cavity is the FACE's business - the face punch already handles
  // it, and punching the plate as well would hole the plate for nothing
  unlifted: seats({ ...cage, lift: 0 }, plate),

  // a cavity lifted to a DIFFERENT height is on some other surface, not this one
  wrongHeight: seats({ ...cage, lift: 20 }, plate),

  // ... including one lifted higher than this surface stands
  above: seats({ ...cage, lift: 60 }, plate),

  // a cavity outside the surface's footprint never belonged to it
  outsideRight: seats({ ...cage, x: 300 }, plate),
  outsideBelow: seats({ ...cage, y: 100 }, plate),

  // straddling the edge is not "within" - punching would cut past the surface
  straddles: seats({ ...cage, x: 200 }, plate),

  // flush at the edges IS within, to the tolerance
  flushCorner: seats({ x: 0, y: 0, w: 205, h: 44, lift: 44 }, plate),

  // a surface that does not stand proud has nothing to be lifted onto
  flatSurface: seats(cage, { ...plate, out: 0 }),

  // THE DEGENERATE PAIR: an unlifted cavity on a surface that stands 0 proud.
  // Both depths match at zero and the footprint is within, so every clause
  // except the lift guard says yes - and the answer is still no, because an
  // unlifted cavity is punched out of the FACE and punching a flat surface as
  // well would hole it twice. Without this case the guard is untested: every
  // other row here is already rejected by the height match.
  zeroOnZero: seats({ ...cage, lift: 0 }, { ...plate, out: 0 }),
};

console.log(JSON.stringify(out));
