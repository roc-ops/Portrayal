# Half-width and quarter-width devices in one rack unit

Status: **proposed, 2026-11-11. Nothing here is built.** A design note only: no code, no
library part, no schema and no export changes with it. Every choice that would be one-way
when built says so, and none is built here.

[#1274](https://github.com/roc-ops/Portrayal/issues/1274) asks that a rack place two (or
four) compact switches or routers side by side in one rack unit, on the tray or shelf they
share. It is the width-wise companion of #970, which put two 0.5 U devices in one unit
(see [rack-file-v4-design.md](rack-file-v4-design.md) section 2). This note settles what the
issue's four "to settle" lines can be settled from what is held, and names what is not.

## 1. The audit

| #1274 asks | state on `main` | evidence |
|---|---|---|
| How a device says it takes a half or a quarter of the width, and which tray or shelf kits it fits | not started | no device or schema key states a width fraction; `chassis.kits` lists kits (rack-mounting-design.md section 4); no compact device is known to list a tray kit, and the count of devices that list any kit was not measured here |
| Whether the tray is a component with bays that devices sit in | not started | `kind: kit` has `motion: shelf` and no place for a held device; the shelf `hosts:` key is designed (rack-products-design.md section 7.1) and no device or schema carries it |
| How the rack view, builder and DCIM export show two devices in one unit | partly, for rack-face parts only | `side: left \| right` on a rack item is read for a part narrower than 450 mm that is `mount: rack-face` (`kit/rack/fit.js` `isNarrow`, `railOf`; `spec/schemas/rack.schema.json` item `side`; lint L142 and L153 for labs) |
| The first case to prove it | not started | no MikroTik 200 mm device and no EdgeRouter is in the library (`library/devices/mikrotik/`, `library/devices/ubiquiti/`) |

The issue says `juniper/ex2300-c-12p` "already models one such unit with its kit". It does
not: the device lists no kit, because the guide names no part number for the EX2300-C
bracket kit (`library/devices/juniper/ex2300-c-12p/device.yaml`, the `rack-ears` gap). The
EX2300-C is 279 mm wide, two posts of a 19 in rack with brackets, not a half-width unit on a
shared tray. It is not a case for this issue.

## 2. What `main` already holds

- **`side` on a rack item** (`left` or `right`): the rail a part narrower than the rack
  opening is on. Fit lets one part stand on each rail at the same unit (`fit.js`
  `NARROW_MM = 450`). It is read only for `mount: rack-face`; a rack device (`mount: rack`)
  with a width under 450 mm was **not measured** here, and the first slice measures it
  before any key is added.
- **Two positions only.** `left` and `right` cannot name four.
- **`heldBy: {item, at, x}`** on an item, for a device on a shelf, drawer or rail of another
  item (rack-products-design.md section 7.2). The kit keeps and refuses it; placing a new one
  is refused until the catalogue describes what can hold a device (`kit/rack/commands.js`,
  `NO_HOSTS`). No library device declares `hosts:`.
- **`ru` in steps of 0.5** for height (rack-file-v4-design.md section 2). Width has no
  equivalent.
- **DCIM.** This note claims nothing about how NetBox or Nautobot store a width position;
  it has not been checked against upstream and the first slice must do so before it relies
  on any.

## 3. The first cases, and what is held

| case | document held | what it says | what is missing |
|---|---|---|---|
| MikroTik RMK-2/10 | `mikrotik/kits/RMK_2_102_230344.pdf` p. 1; `mikrotik/kits/BOFF-RMK-2_10-INSTR_260946.pdf` p. 1 | "allows installing two of the smaller MikroTik form-factor devices within traditional 19-inch racks"; a 200 mm unit; the installation sheet draws one joining bracket between two devices, each on its own standard rack ear, and "2x" beside the bracket drawings for the 10 in use; screws are drawn with no count | no dimensioned drawing, no hole or bay position, no screw count, no load rating |
| MikroTik devices it takes | the RMK_2_102 sheet, p. 1 | CSS610-8G-2S+IN, CRS112-8G-4S-IN, CRS310-1G-5S-4S+IN, CRS112-8P-4S-IN, CRS109-8G-1S-2HnD-IN | none of these five is in `library/devices/mikrotik/` |
| Ubiquiti ER-RMKIT | none; `ubiquiti/COVERAGE.md` records a refused request for its page | its model list comes from the EdgeRouter data sheet p. 5 | no kit page or guide, no dimensions; no EdgeRouter device is modelled |

The MikroTik sheets and `ubiquiti/COVERAGE.md` are held in the intake corpus, not in this
repository. The RMK-2/10 sheet draws a coupler between two devices that each keep their own
rack ears; it does not draw a tray or shelf. The ER-RMKIT page request was refused, so its
form is not known.

So neither first case can be modelled from what is held: the kit has no position facts, and
no unit it takes is in the library. A device is never modelled for the sake of a note.

## 4. The design

### 4.1 How a device says its fraction (proposal)

**Derive it from the width the device already states, and let the kit say which fractions it
makes.** A 200 mm device already states its width, so no new key is needed to know it is
narrower than 450 mm; the kit's configuration says it holds two of them, side by side, or
four. This holds only if fit treats a `mount: rack` device of that width as narrower, which
section 2 says was not measured (question 3). Option B, a key on the device
(`rack-width: half`), would repeat a number the body already gives and would be a published
key. Recommended: A, if the measurement of question 3 shows fit can read the width.
Nothing is added to the device schema.

### 4.2 The tray (proposal)

**A tray is a `kind: kit` with `motion: shelf`, plus bays in its configuration.** A bay is
`{id, x, width}` in millimetres along the tray from its left, and a device is held in a bay
by the existing `heldBy: {item, at, x}`, with `at` the bay's id. This reuses `heldBy` and the
holder design instead of a new place for a device, and four positions are four bays. The
alternative, a tray as a component placed in a view, would put it in the face of a device it
does not belong to. This form fits a tray or shelf kit; the held RMK-2/10 sheet draws a
coupler between devices on their own ears (section 3), which it does not describe (question
7). Bay sizes are a source fact: a bay with no printed position is a stated
gap, never a divided width.

### 4.3 The rack file (proposal)

`side` stays as it is for rack-face parts. A device in a bay is `heldBy` the tray item, and
the tray item is an ordinary item with its own `ru`. Fit refuses a device wider than its bay,
two in one bay, and a tray whose bays hold more than the kit's load. **One-way when built:**
the bay vocabulary a saved rack names.

The devices this note targets are `mount: rack` boxes of about 200 mm. Under
rack-products-design.md section 7.3 a `mount: rack` device standing on a shelf keeps its own
rack unit and claims it, and lab lint L142 reports two rack devices that share a rack unit.
Two such devices in one tray would therefore each claim the tray's unit and collide. This
proposal does not settle that: either fit and L142 learn that devices in different bays of
one tray share a unit, or each held device is not a `mount: rack` claimant. Which one is
left open (question 8).

### 4.4 Views, builder and export (proposal)

The elevation draws a held device at its bay's `x` inside the tray's unit; the builder offers
a bay, not a free position; the DCIM export treats each held device as a hosted device is
treated today: no position, no face, and a comment line naming its tray and bay
(rack-products-design.md section 7.4). Giving it the tray's position would change that
section and is not proposed. A NetBox or Nautobot width position is not claimed.

## 5. What is one-way when built

| item | why |
|---|---|
| the bay vocabulary on a kit configuration | a published key in the kit schema |
| `at` naming a bay in a saved rack | a saved id |
| any width key on a device | a published key (not recommended) |

## 6. Open questions

1. **Is the tray a kit with bays (4.2)?** Changes the kit schema and the lock of every kit.
2. **Is a derived fraction (4.1) accepted?** Spares a device key.
3. **Which unit measures first:** a `mount: rack` device of 200 mm in fit (section 2).
4. **Which documents:** the RMK-2/10 and ER-RMKIT drawings (section 3) are needed before a
   bay can be stated; a lab measurement of the RMK-2/10 would also do.
5. **DCIM:** what NetBox and Nautobot store for a width position, cited by commit.
6. **The issue's statement about `juniper/ex2300-c-12p`** (section 1) should be corrected.
7. **How is a coupler stated?** The RMK-2/10 as held joins two devices that keep their own
   ears; section 4.2 does not describe it, and a drawing or measurement (question 4) is
   needed before a form is chosen.
8. **Which rule gives two 200 mm devices one unit?** Section 4.3: section 7.3 of the
   rack-products note and lint L142 give each `mount: rack` device its own unit.

## 7. Build order

1. Measure fit on a 200 mm `mount: rack` device (question 3). No change.
2. Hold the kit drawings (question 4); model one MikroTik 200 mm device. The RMK-2/10 as a kit
   waits for question 7.
3. Kit schema bays and `heldBy` placing (one-way, after question 1).
4. Elevation, builder and export.
