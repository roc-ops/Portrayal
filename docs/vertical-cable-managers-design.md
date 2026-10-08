# Vertical cable managers: rack-side mounting

Status: agreed 2026-10-07, not yet built. Follows docs/cable-managers-design.md, which
reserved `rack-side` for this. Scope: the FS-made vertical managers; the four
resold APC parts wait for their vendor's drawings.

## 1. What the parts are, and how they mount

| part | what | H x W x D (mm) | mounts |
|---|---|---|---|
| CMV-SFD45U5W | single-sided ABS finger duct, hinged cover | 2108 x 125 x 165 | beside or between racks |
| CMV-DFD45U5W | dual-sided ABS finger duct, covers both faces | 2108 x 125 x 310 | beside or between racks |
| CMV-SFDS45U5W | single-sided steel finger duct | 2000 x 141.52 x 152.6 | beside or between racks |
| CMV-DFDS45U5W | dual-sided steel finger duct | 2000 x 141.52 x 307.66 | beside or between racks |
| CMV-SFD42U9W | single-sided finger duct with cover | 1866.9 x 88.9 x 152.6 | beside or between racks |
| CMV-5U3W | 5U finger bracket, stackable | 222 tall | on the rail, through the equipment's ear holes |
| VRTCMB | the L-bracket the 45U parts hang on | - | hardware, not drawn as a device |

The full-height parts take no rack unit. L-brackets bolt to the side of the rack's
upright and the duct stands beside the rack, outside the rails, or between two racks
where one duct serves both. Their heights are rack heights: 2000 is 45 x 44.45 and
1866.9 is 42U. FS's compatibility matrix accepts them on open-frame racks only (the
APC AR201 45U two-post; the 42U part also on the AR203A 44U four-post), never in an
enclosure. The 5U bracket is different: it screws to the front of a rail through the
same holes as the equipment's ears and stands forward of the rail, at the rail's side
of the opening, not across it.

## 2. What exists

- `chassis.mount` is `rack`, `rack-face`, `din-rail`, `wall` or `desktop`. `rack-side`
  and `rack-top` are reserved names.
- A face is sized from the chassis, so a part 125 wide and 2000 tall has a portrait
  front. Portrait faces already exist (the DIN-rail switches) and nothing in the
  renderer or the 3D viewer assumes width at least height.
- A lab is one rack: no row, no position beside or between racks.
- The site's Rack Builder keeps a reserved, unused `zeroU` record for side-mounted gear
  (`at` an attachment point, `offsetMm`), with fit rules and no drawing, and routes
  vertical cable runs on lanes 40 mm outside each post.
- The library models no rack, cabinet or frame; the site defines the frame itself.

## 3. Decisions to take

1. **`chassis.mount: rack-side`** is a part that attaches to the side of a rack's
   upright and runs vertically beside it, outside the rails. It states `ru`, the rack
   units of height it spans, and exports `u_height: 0` and `is_full_depth: false`
   with a comment line, as `rack-face` does. It says nothing about left or right, or
   which rack: that is the placement's.
2. **The device is drawn as it stands.** Front `w` is its width across the rack's
   face direction, `h` its height; `depth` is front to back. A dual-sided duct's rear
   face is a second working face, as on the horizontal dual ducts.
3. **Hollow, like every manager.** A full-height duct is built as the horizontal
   ducts are: a `shell: sheet` body, a base well, two rows of fingers standing in it,
   a pullable `mounts` cover over each working face, and a `duct` guide with
   `run: y` (vertical), its pitch and gap read from the drawings. Cables sit in the
   channel and show when the cover is off. The 22.5U and 21U sections are drawn as
   one length with the joint as a seam.
4. **The 5U bracket is `rack-face`,** placed at a rack unit like the horizontal
   lacer panel, with one new placement key, `side: left | right`, saying which rail
   it is on. It does not lie across its host: L142's per-face claim becomes per face
   and side for a part narrower than the opening.
5. **Lab placement** for a `rack-side` part: `side: left | right` and `ru` (its bottom
   unit, default 1), on a face of `front` for a single-sided duct. A lab is still one
   rack; a duct between two racks is the same duct named on the adjoining side of
   each, and waits for a lab with more than one rack (section 6).
6. **The site draws them in its `zeroU` record,** which was reserved for side-mounted
   gear: `at: left | right` on a two-post frame, `offsetMm` from the rack's bottom.
   The elevation widens by the duct's width beside the post, the 3D scene stands the
   duct's model against the upright, and the left and right route lanes run through
   its channel. That is site work and lands after this.
7. **Two devices first,** CMV-SFD45U5W (ABS, with the install guide) and CMV-5U3W
   (the rail bracket), then the steel pair, the dual ABS duct and the 42U part as
   routine modelling.

## 4. Lint

- L125 learns `rack-side`: states `ru` (warning), and `full-depth`, `overhang` and
  `ears` stay rack-only.
- A `rack-side` part's front is taller than it is wide (warning): a duct drawn on its
  side is the likeliest authoring error.
- Lab checks: `side` only on `rack-side` and on a `rack-face` part narrower than the
  opening; two `rack-side` parts on one side overlap in height only if they are
  stacked sections (error).

## 5. What is estimated, and what is not expressible

- The gap between the duct and the upright is drawn but never dimensioned; the
  bracket's own sheet gives its size, so the stand-off is taken from it and marked.
- The APC AR201 the parts pair with is not in the library; the site's frame stands
  in for it.
- A duct shared between two racks is one part in two places until a lab or a rack
  file holds more than one rack.

## 6. Out of scope

- Rows of racks, and routing between racks.
- The in-cabinet zero-U channel (APC AR8442, AR7721) and cabinet side panels.
- The four APC parts, until their drawings are staged.
- `rack-top`.

## 7. Order of work

1. `rack-side`, its lint, lab placement and CMV-SFD45U5W, in one change.
2. `side` on `rack-face` placements, L142's per-side claim, and CMV-5U3W.
3. The remaining four FS ducts.
4. The site: `zeroU` drawn in the elevation and in 3D, and the lanes through the duct.
