# Fibre positions you can point at

Status: proposed 2026-09-23.

## The problem

A passive fibre part already declares its fibres. `optical.positions` says how
many a connector carries, and a cassette's `optical.paths` wires them:
`{from: lc01.1, to: 'rear:mtp2.2'}`. The DCIM export and `components.json` both
carry that model. The explorer does not use it, and the drawing gives no fibre an
address of its own:

- An LC bore is addressable only when it happens to be a composed part. The
  24-fibre FHD adapter composes two, named `tx` and `rx`. The 36-fibre adapter
  composes none, because a bore's ferrule stood out through the closed shutter
  in 3D, so its ports have no sub-rows at all.
- An MPO bulkhead is one node. Its opening, its housing and the twelve fibre
  holes are plain drawing, so selecting `mtp1` selects the flange and both
  screws, and no fibre can be selected.
- Nothing shows where a fibre goes. Picking front port 1 says nothing about
  rear `mtp2` fibre 2.

The rear tree also names its rows after the panel holes (`cutout:back-1`),
not the slots they belong to.

## The rule

**A fibre endpoint `X.n` is drawn at path `X/n`.** Every connector part
(`class: port`) with `optical.positions: N` exposes N addressable nodes with
the ids `1` to `N`, in position order. So `lc01.1` is `…/lc01/1`, and
`rear:mtp2.2` is `…/mtp2/2` on the rear face. The explorer, the lint and any
consumer can turn one form into the other without a table.

A node is either:

- **a composed part** where the position is a real bore with its own geometry
  (LC and SC duplex adapters: the bore is the position), or
- **a contracted element** (`elements:`, class `fibre`) marking where the fibre
  is, with no geometry of its own. Used for MPO ferrule holes, shuttered
  bores, simplex sleeves, MDC and splice positions. An element builds nothing
  in 3D, which is what the shuttered adapter needs.

`class: fibre` joins the closed class vocabulary as a passive class.

## Decisions taken (2026-09-23)

1. **Positions are numbered, not `tx`/`rx`, on passive adapters.** A cassette
   port has no direction until something is plugged into it. `tx`/`rx` stays
   where the direction is real: transceivers (`generic/sfp-lc`, `qsfp-lc`,
   `qsfp-dd-lc`, `common/qsfp-transceiver`), and Smartoptics PPM modules, which
   are `class: filter` and out of this rule's scope anyway.
2. **The MPO opening is its own node,** `opening` (class `port`), separate from
   the flange and screws. The fibres are siblings of it: `mtp1 › opening,
   1…12, screw-left, screw-right`. Keeping them flat under the adapter, rather
   than under `opening`, keeps the `X.n → X/n` rule exact.
3. **Type A and Type AF need nothing new.** The two polarities already differ
   only in their `optical.paths` (AF swaps each pair), and that is what reaches
   DCIM. Numbered positions make the difference visible in the explorer.

## MPO fibre numbering

The expected convention is TIA-604-5 (FOCIS 5): with the key up, fibre 1 is at
the left of the row, and on a 24-fibre ferrule the second row carries 13-24.
The skins already draw the fibres left to right at the ferrule's 0.25 pitch
with the key slot on the top edge, so fibre `n` would be the n-th circle.
**This is to be confirmed against the standard, or a vendor drawing that cites
it, before any fibre element is placed.** It also has to be settled which way
the adapter is being looked at, since the rear face shows the side the trunk
plugs into. Each part's provenance records the source.

## Library changes

| part | today | change | version |
|---|---|---|---|
| common/lc-duplex-adapter | composes `tx`, `rx` | ids `1`, `2` | major |
| common/lc-duplex-v-adapter | composes `tx`, `rx` | ids `1`, `2` | major |
| common/sc-duplex-adapter | composes `tx`, `rx` | ids `1`, `2` | major |
| common/lc-duplex-shuttered-adapter | nothing | elements `1`, `2` on the shutters | minor |
| common/mpo-flange-adapter, mpo24-flange-adapter | screws only | `opening` + fibre elements | minor |
| common/mpo-adapter | composes `bore` (std/mpo) | fibre elements `1`-`12` | minor |
| common/st-, fc-, lsh-simplex-adapter | nothing | element `1` | minor |
| common/mdc-adapter | nothing | elements `1`-`4` | minor |
| common/fibre-splice | nothing | elements `1`-`12` | minor |

**The rename is the cost.** 42 contracts and devices use the three renamed
adapters. Changing a composed id changes the paths every consumer draws, so
each consumer takes a major, and each device that accepts one is re-pinned
and re-locked. The bumps are done by script and checked by the existing
version and lock gates.

**A new lint rule** (next free L-number): a `class: port` part with
`optical.positions: N` must expose addressable nodes `1`-`N`, no more and
none missing. A census test lists every part it covers, so a new adapter
joins by design.

**Front and rear ids must not collide** on one cassette. `rear:mtp1` and a
front `mtp1` would draw the same path on two faces as two different
connectors. The lint rule refuses it; no part in the library does it today
(checked when the rule lands).

## Explorer changes (kit)

- **Fibre rows** read `1 → rear mtp2 · 2`, from `optical.paths` in
  `components.json`, looked up through the module's ref (the front's
  `data-ref`, or `data-rear-ref` on the rear; see below).
- **MTP rows** read `mtp2 — front 1-12`: the front fibres wired to that
  connector, numbered as the vendor prints them. The build writes each fibre
  end's far end and front number into `components.json` (`optical.ends`, from
  `optical_ports.front_label`), so the kit reads the numbering and never
  re-derives it.
- **Selecting a fibre marks its other end** on every loaded face
  (`data-portrayal-linked`), highlights that row, and the inspector gives the
  far end as a link. In 3D both faces are on screen at once; in 2D the link
  switches the view.
- **The rear rows are slots.** render.py stamps the rear cutout with the bay's
  `data-group`, `data-rel-pos` and the occupant as `data-rear-ref`, and
  `applyRearOverrides` updates it on a swap. The tree labels it
  `bay-1 — FHD-2MTP12LCDOS2AF (rear)` under the same SLOTS heading as the
  front. The path stays `cutout:back-1`: a label costs nothing, and a renamed
  path would cost the device a major.
- **Rows never show a raw id.** A `<title>` that is an internal id
  (`fhd-2mtp12-lc-af-rear--mtp1--screw-left`) falls back to the path's last
  segment (`screw-left`).

The rules live in kit modules node can run (`swap.js`, or a new `optical.js`),
tested the way `test_projected_rows_js.py` tests the tree rules.

## Out of scope

- DCIM export content. It already numbers fibres from `optical.positions` and
  is unaffected by the rename.
- Directional parts: transceivers and Smartoptics PPM modules keep `tx`/`rx`.
- Applying swaps to faces that are not on screen. That is a separate change
  already in progress, and this work merges after it.

## Delivery

Two pull requests, each merged only after the swap-on-other-faces change:

1. **Library**: position nodes, the rename and its majors, `class: fibre`, the
   lint rule and census, rebuilt dist and locks.
2. **Kit**: rear slot rows, readable labels, fibre-path marking and the
   inspector link.
