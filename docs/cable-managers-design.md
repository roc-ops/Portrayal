# Cable managers: rack-face mounting, sheet bodies, brushes and guides

Status: 2026-10-06. Sections 2 to 4 and the first device of section 7 are implemented;
brushes, pass-throughs, guides and lab placement are design. The first passive rack parts
in the library that hold or pass cables rather than terminate them: the FS horizontal
cable managers.

## 1. What exists, and what is missing

Every device today is a box that occupies rack units between the posts, or is not in a
rack at all.

| what | where it stands |
|---|---|
| `chassis.mount` | `rack` (default), `din-rail`, `wall`, `desktop`. Anything but `rack` states no `ru` and exports `u_height: 0` (L125) |
| the 3D body | a box sized from `chassis`, with each view painted on a side and relief built on it ([DEPTH-AND-3D.md](../spec/DEPTH-AND-3D.md) section 4) |
| panel decoration patterns | `vent`, `holes`, `grille`, `slots`, `slots-h`, `ribs` |
| a lab placement | `{id, ref, ru, label}`. No face, no schema, no checks; `labs_index.py` passes the file through |
| the rack drawing | in the site repository, from `labs.json` |

Four things a cable manager needs are missing:

1. A way to say a part bolts to the rail face at a rack unit and projects **outward**,
   sharing that unit with the equipment behind it.
2. A 3D body that is bent sheet metal and open air, not a solid box.
3. A brush, and a statement that cables can cross a panel through an opening.
4. A statement that a ring or a duct is something cables run through.

## 2. Decisions

1. **The term "zero-U" is not a Portrayal value.** It names what a part does not use, and
   covers vertical power strips, roof-mounted gear and these managers alike. The mount is
   named for where on the rack the part attaches. `rack-face` is added now. `rack-side`
   (beside the posts, running vertically) and `rack-top` are reserved names, not built.
2. **`chassis.mount: rack-face`** means: bolts to rack holes at a rack unit, on the rail
   face, body projecting outward from the mounting plane. The device says nothing about
   front or rear; the same part goes on either, and that is the placement's to say.
3. **A rack-face device states `ru`**, the rack units its ears span. Its `depth` is the
   outward projection. Its own `front` view is its outward side.
4. **The DCIM export writes `u_height: 0` and `is_full_depth: false`** for a rack-face
   device, with a comment line saying it mounts on the rail face at a rack unit and
   occupies none. Neither target schema has a field for the mounting position.
5. **A sheet body.** `chassis.shell: sheet` with a `thickness` in millimetres. The six
   views are drawn as usual, with no housing filled in behind them, and they are
   ELEVATIONS: in 3D nothing is built from the faces. The solid is what the views' parts
   build, section 4. Without it a rack-face part would be a solid block hiding the ports
   it serves.
6. **A `brush` decoration pattern**, with a bristle direction. It paints itself as a solid
   field, so it needs no backing plate, and in 3D it is an opaque slab filling its opening.
7. **A pass-through is declared**, per view, as `passes:` entries with `id`, `at`, `size`,
   `shape` (`rect` or `obround`) and `cover` (`open` or `brush`). It says cables can cross
   this face here to the opposite side. Nothing consumes it in this round.
8. **A guide is declared.** `ring` on a component contract: the aperture and the direction
   cables run through it, inherited by every placement. `duct` on a device view: a channel,
   its run direction, and the finger pitch and gap along its walls. Nothing consumes it in
   this round.
9. **Cable capacity is one stated fact per device**: the count and the vendor's basis for
   it. It is not divided among rings, because the vendor states it per manager and calls it
   theoretical.
10. **A lab placement gains `face`, `on` and `unit`.** `face` is `front` or `rear`. `on`
    names a host placement; `unit` is which rack unit of that host, counted the way the
    rack counts, default 1. A rack-face part always sits on a whole rack unit, also in
    front of a card chassis, because it bolts to the rack and not to the host. Several on
    one tall host are several placements with different `unit` values.
11. **Labs get a schema and build-time checks**, and `labs.json` carries every placement
    with its position resolved to an absolute rack unit, a face and a host id.
12. **Three devices are built with the features**, one per feature, section 7. The rest of
    the line follows as routine modelling.

## 3. The rack-face device

```yaml
chassis:
  width: 483
  height: 44
  depth: 109          # the outward projection
  ru: 1               # the rack units the ears span
  mount: rack-face
  shell: sheet
  thickness: 1.5
```

L125 changes: `rack` and `rack-face` state `ru`; `din-rail`, `wall` and `desktop` state
none. `shell: sheet` requires `thickness`, and `thickness` is stated only with it (L127).

L43 stands down for a rack-face part. That rule says ears are never drawn and the body is
the metal between them; a part that bolts to the rail face is its ears and whatever hangs
off them, so its 483 mm is the part. The ears of the FHD-CMP5DR are drawn, with their
fixing holes, for the same reason: they are the tray's own sheet, not something added.

A sheet part has six views like any other, because a rack drawing and the explorer ask
for them. For the FHD-CMP5DR: `top` carries the tray, the two webs and the five rings;
`rear` the two ears; `front`, `left`, `right` and `bottom` are elevations.

The snap-in D-ring is a component placed five times on the tray. It is an open loop: a
rear leg, a top bar, a hooked end and a front leg that stops short of it, and the gap
between the last two is the slit a cable is laid in through.

## 4. The sheet body in 3D

The viewer builds a box from the chassis and rasterises each view onto a side. For a
sheet body it draws nothing from the six faces. That is what a first reading of "sheet"
gets wrong: a front view shows the ears and the rings end-on, and none of that metal lies
in the front plane, so a face painted onto the envelope stands a picture of the part on
every side of it. The solid is built from three things the library already had:

- **A floor.** The tray is a component placed on the `top` view that is a well, a recess
  as deep as the envelope less the sheet. In a sheet body a well builds its floor and
  nothing round it, seen from both sides; in a box it builds walls and a back as before.
  Whatever the floor's drawing leaves unpainted - a slot, the cut-out between the arms -
  is a hole.
- **Parts standing on the floor.** A part placed `in:` the well rises from its floor. The
  rings are tubes and the web between each ear and the tray is one plate whose top edge
  follows a `profile-y`.
- **Parts standing proud of a face.** The ears are placed on the `rear` view and stand
  the sheet's thickness off it.

Two things had to be put right for that:

- `uhandle` was built from the face plane whatever it stood in. It now rises from the
  floor of the well it is in, as `out`, `cyl` and `bar` did. The rings here ended as
  `cyl` and `bar`, an open loop being more than one handle, so no part uses it yet.
- `in:` sank a part's `out` to the well's floor and left its `profile` measured from the
  face the well is cut in. A profile is a height and now sinks with it.

A well is built no deeper than 2 mm short of the far face. The FHD-CMP5DR's tray clears
that without help: its sheet sits 1.5 mm above the ear's bottom edge, so its floor is 41
mm down in a 44 mm envelope.

This is relief, not CAD, as section 7 of DEPTH-AND-3D.md already says of the whole
pipeline. The tubes are round and their corners square.

The open tray of the brush manager uses the same sheet body. A finger duct with its cover
is a closed box and needs nothing new.

## 5. Brush, pass-throughs and guides

All three compile to attributes on the drawing, which is how every consumer already reads
depth. The DCIM exports ignore them.

```yaml
views:
  rear:
    panel:
      decor:
        - {at: [9, 6], size: [465, 32], pattern: brush, bristle: vertical}
    passes:
      - {id: rear-brush, at: [9, 6], size: [465, 32], shape: rect, cover: brush}
```

A `ring` guide on a component contract:

```yaml
guide: {kind: ring, aperture: {w: 40, h: 70}, run: x}
```

A `duct` guide on a device view:

```yaml
guides:
  - {id: duct, kind: duct, at: [9, 0], size: [465, 44], run: x, finger-pitch: 18.1, finger-gap: 16.4}
```

The figures in these three examples show the form only. The real ones are read from the
sources when each part is modelled.

Three lint rules:

- A pass-through lies inside its face and overlaps no component.
- A pass-through whose cover is `brush` has a brush drawn over it, and a brush drawn where
  a pass-through is declared matches its cover. The picture and the declaration cannot
  drift apart.
- A guide's aperture fits inside the part that declares it.

Every device names a profile, which sets what it must state before it counts as
specified. A cable manager is none of `networking`, `server` or `optical`, so there is a
fourth, `passive`: rack furniture with nothing in it to power or to forward. It owes no
power, performance, platform or environmental section, only its weight.

## 6. Lab placement

```yaml
devices:
  - {id: patch-1, ref: fhd-1ufce, ru: 36}
  - {id: mgr-1,   ref: fhd-cmp5dr, on: patch-1, face: front}            # on a 1U host
  - {id: mgr-2,   ref: fhd-cmp5dr, on: chassis-1, face: front, unit: 3} # third unit of a tall host
  - {id: mgr-3,   ref: fhd-cmp5dr, ru: 30, face: front}                 # no host
  - {id: mgr-4,   ref: cmh-sfd1u, ru: 29}                               # an ordinary 1U manager
```

The checks, at build time:

- every `ref` names a device in the library and every `on` names a placement in the lab;
- `face`, `on` and `unit` appear only on a device whose mount is `rack-face`, and such a
  device has `on` or `ru`, not both;
- `unit` is within the host's height;
- no two `rack` devices overlap, and no two rack-face devices claim one rack unit on one
  face;
- a rack-face device placed by `ru` is reported with the host behind it, if there is one.

They are run over the existing lab before they are made errors, and what they find is
reported.

In the rack drawing a rack-face device is drawn at its rack unit on the outer side of the
rails: forward of the front rails, or behind the rear ones and turned round. In a 2D
elevation it draws over its host on that face. That change is in the site repository and
lands after this one. A site older than the `labs.json` it reads ignores the new keys and
draws the manager as an ordinary device on that rack unit, which is wrong and visible;
the site's contract check is what catches the gap.

## 7. The three devices

| device | vendor part | what it proves |
|---|---|---|
| `fhd-cmp5dr` | FHD-CMP5DR, 0U, 5 snap-in D-rings | `rack-face`, the sheet body, the D-ring component |
| `cmh-4drb1u` | CMH-4DRB1U, 1U, 4 steel D-rings and a brush strip | the brush pattern, pass-throughs, a sheet tray in a rack unit |
| `cmh-sfd1u` | CMH-SFD1U, 1U ABS finger duct with cover | the duct guide; the shape most of the line shares |

## 8. Sources

Vendor documents and renders held in the maintainer's gitignored corpus; the names are
the vendor's.

- **0U/1U Horizontal Cable Manager Datasheet**, updated 2025-05-11. A dimensioned
  three-view of the FHD-CMP5DR: plan 110 deep; front 44 high, 31.5 between ear holes, 465
  between hole centres, 483 overall; a ring profile. Raster, 1142 x 767 px.
- **Horizontal Cable Managers Quick Start Guide V2.0.** The one drawing of how the
  FHD-CMP5DR shares a rack unit: its ear laid over the host enclosure's ear, one fastener
  each side. Not dimensioned. The host drawn is a fibre enclosure.
- **CMH-4DRB1U Horizontal Cable Manager Datasheet**, updated 2025-12-09. Specifications
  and a dimensioned render, not an orthographic drawing.
- **Horizontal Cable Managers with Finger Duct Datasheet.** The ABS finger ducts.
- Product-page renders, 1600 px. Every image of the line is a render, not a photograph.

## 9. What is estimated, and what is not expressible

- **How far the tray of the FHD-CMP5DR stands from its host** is not stated by any
  document. The part's own profile is measured from the ring-profile view.
- **The brush has no dimensions.** Bristle length and window size are measured from
  renders against the 482.6 width.
- **Colour and finish** are the vendor's render material.
- **The vendor's depth is an overall projection**, rings or duct included. It is not a
  body depth, and each device says which it states.
- **Curved sheet metal** is drawn as flat plates: the swept arm of the FHD-CMP5DR is a
  strip of floor, an upright ear and a sloped web.
- **A detachable, rotatable ring** is drawn fitted, in one orientation.

## 10. Out of scope

- Routing cables through rings, ducts and brushes. The declarations in section 5 exist so
  that work has something to read.
- The other thirteen managers of the line that have renders, and the eight that exist
  only as datasheets published in the week of this design.
- `rack-side` and `rack-top`.
- Mounting position in the DCIM exports, which have no field for it.

## 11. Order of work

1. The viewer probe for the sheet body. Done.
2. `rack-face`, the sheet body, the D-ring component and `fhd-cmp5dr`.
3. The brush pattern, pass-throughs and `cmh-4drb1u`.
4. Guides and `cmh-sfd1u`, with the ring guide applied to the D-rings of steps 2 and 3.
5. Lab placement, the lab schema and checks, and the site change.

Each of steps 2 to 5 is its own change, and each pairs one feature with the part that
proves it.

## 12. Testing

- Each new lint rule has a test that passes on a good device and fails on a broken one.
- The export test: a rack-face device writes `u_height: 0` and is not full depth.
- One failing lab fixture per lab check.
- Each device goes through the modelling gates, with a comparison of source drawing
  against render reviewed before the full build.
- In 3D, the composited screenshot of a rack-face manager on a host shows the host's
  ports through the manager. That is what the sheet body is for.

## Decisions taken

Agreed 2026-10-06:

- Scope is library parts plus rack placement. Cable routing is a follow-up once managers
  exist in the library.
- The placement form of section 6, with `on` and `unit` so that managers on a chassis
  move with it, and `ru` for a manager with no host.
- `rack-face`, with `rack-side` and `rack-top` reserved, in place of "zero-U".
- The brush as a pattern plus a declared pass-through.
- Rings and ducts declared as guides; capacity recorded per device.
- Three devices first: FHD-CMP5DR, CMH-4DRB1U, CMH-SFD1U.
- The sheet body. The thin-box fallback was not needed.

Agreed in review of the first device, 2026-10-06:

- A sheet's views are elevations and build nothing in 3D; its solid is floors and relief.
- The ears of a rack-face part are drawn, with their holes: they are the product.
- A ring is an open loop with its slit.
- The web between ear and tray is one sloped plate, not steps.
- The plan is 110 mm deep, the drawing's figure, where the spec table says 109.
