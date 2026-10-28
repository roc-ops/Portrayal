# Non-rack devices: a ceiling mount, and a powered device's PoE class and draw

Status: proposed, decided 2026-10-28 to be written before any access point is
modelled. Issue #1296. This note changes nothing: no schema, lint rule, device,
export or test. It sets out two `device.schema.json` questions, recommends an
answer to each, and leaves both for the owner to decide. A later change builds
what is decided, then models the two ReadyLinks access points. Every count was
taken from `main` at commit `a1982880c`.

Read with [din-rail-design.md](din-rail-design.md) (the last mount type that
needed a note), [pdu-model-design.md](pdu-model-design.md) (the last power keys
the schema defined), [format-stability.md](format-stability.md) (what an
additive change is) and issue #1297 (the site file that places these devices in
a room).

## 1. The two questions

The library can say what a switch hands out over PoE. It cannot yet describe
the device at the other end of the cable. Two things are missing before the
first access point can be written down:

1. **How a ceiling device states its mounting.** `chassis.mount` has no value
   for a ceiling (section 2).
2. **How a powered device (PD) states its PoE class and draw,** as numbers a
   tool can sum against a switch's `poe-budget-w` (section 3).

The two access points that wait on this note are, from the maker's sheets:

| Device | Sheet's own title | Mounting | PoE in | PoE out | Draw as printed |
| --- | --- | --- | --- | --- | --- |
| IPC-APWF6-POE-WP | Wi-Fi 6 Wall-Plate Access Point | "replaces the plate over an existing outlet" | "PoE/PoE+ IEEE 802.3af/at" | "LAN1 supports 48V/10W" | "802.3at (PoE+): 25 W", "802.3af (PoE): 15 W" with PoE out disabled, "Idle mode: 8 W" |
| IPC-APWF7-POE-CL | Wi-Fi 7 Ceiling Access Point | "Install ... on the ceiling" | "PoE+/PoE++ IEEE 802.3at/bt" | "LAN1 for PoE power supply (48 V/12.95 W)" | "60W (Excluding PoE output)", "DC power: 60 W" |

So the ceiling question matters for the `-CL` only, and the draw keys have to
cope with a figure printed "excluding PoE output". Neither sheet prints an
802.3 class number.

## 2. Ceiling mounting

### 2.1 Today

`mount` is one of `rack`, `rack-face`, `rack-side`, `din-rail`, `wall` or
`desktop`. Its description says `wall` is "one that screws to a surface", and
that a box that mounts more than one way "names the way it is drawn and
exported, and its provenance says the rest". Ten devices on `main` are `wall`
or `desktop`, among them `readylinks/gl-8xep`.

Four things read the value:

- **Lint L125** (`lint_device_mount`). A mount that is not `rack`, `rack-face`
  or `rack-side` must state no `ru` (error), and no `full-depth`, `overhang`,
  `ears` or `kits` (error). The test is "does it bolt to a rack", not a list of
  the other values, so any new value falls on the not-racked side. The rule's
  catalogue text and its warning name `din-rail`, `wall` and `desktop`.
- **The DCIM exports.** `u_height()` returns 0 and `is_full_depth()` returns
  false for any mount other than `rack`. `comments_for()` adds one sentence from
  `MOUNT_PROSE`, keyed by value, and adds nothing for a value that is not in
  the table. `wall` writes "Wall-mounted; not rack-mounted."
- **The Rack Builder.** `kit/rack/export-data.js` has its own `MOUNTS` table
  for the picker tag and the bill-of-materials notes. An unknown value falls
  back to "not a rack-mount device (ceiling)", which "needs a shelf or bracket".
- **`spec/tests/test_mount_type.py`**, whose `NOT_RACKED` tuple drives the
  export and lint tests over each value.

### 2.2 Option A: a new value, `ceiling`

The `-CL` is written `mount: ceiling`. What changes:

- **Schema.** One enum value, and one sentence in the description:
  "`ceiling` is one that fixes to a ceiling or hangs below it, its front facing
  down."
- **L125.** No logic changes: `ceiling` is not a rack mount, so `ru`,
  `full-depth`, `overhang`, `ears` and `kits` are refused as for `wall`. The
  catalogue text and the warning's list of mounts gain the word. `NOT_RACKED`
  gains it, so the existing tests cover it.
- **Exports.** `u_height: 0` and `is_full_depth: false` come out with no code
  change. `MOUNT_PROSE` gains "Ceiling-mounted; not rack-mounted." Without that
  entry the comment would say nothing about mounting. The parametrized comment
  test catches the omission once `NOT_RACKED` has the value. No export on
  `main` changes, because no device uses the value yet.
- **Rack Builder.** `MOUNTS` gains a row: tag "ceiling mount", "a
  ceiling-mount device", which needs "a shelf or bracket" like `wall`.
- **Schema republish.** The device schema is served at its `$id` under
  `/schemas/v1/`. A new enum value is additive: every file valid today stays
  valid, so `format` does not move. The served copy has to be republished in
  the same release as the first device that says `ceiling`. A reader that
  validates against the old copy would otherwise refuse that device.
- **The site file (#1297).** The site note places a non-rack device "with its
  mount and height". With `ceiling`, the mount tells the site tool which
  surface the device goes on, the ceiling of a space rather than a wall, and
  that its height is measured down from that ceiling. A coverage or cable-run
  calculation can start from it without reading prose.

### 2.3 Option B: `wall`, with a provenance note

The `-CL` is written `mount: wall`, and its provenance says it fixes to a
ceiling. What changes:

- **Schema, L125, the Rack Builder:** nothing.
- **Schema republish:** none.
- **Exports:** the numbers are the same (`u_height: 0`, `is_full_depth:
  false`). The comment says "Wall-mounted; not rack-mounted." A NetBox or
  Nautobot user who opens the record reads that a ceiling access point is
  wall-mounted, which is false, and no field contradicts it.
- **The site file (#1297):** the mount points the tool at a wall. A site author
  has to override it on every placement of the device, or the site file needs
  its own surface key that disagrees with the device. Either way the fact moves
  out of the library into each site, once per placement.

### 2.4 Side by side

| | A: `ceiling` | B: `wall` + note |
| --- | --- | --- |
| `device.schema.json` | one enum value, one sentence | none |
| L125 | catalogue and warning text only | none |
| `u_height` / `is_full_depth` | 0 / false, no code change | 0 / false |
| DCIM comment | "Ceiling-mounted; not rack-mounted." (new `MOUNT_PROSE` row) | "Wall-mounted; not rack-mounted.", which is wrong |
| Rack Builder | one `MOUNTS` row | none |
| Schema republish | yes, additive; same release as the first `ceiling` device | none |
| Site file (#1297) | mount names the surface | each placement overrides the device |
| One-way | the value `ceiling` | none |

### 2.5 Recommendation: option A

Add `ceiling`. The cost is one enum value and three one-line tables (lint
text, `MOUNT_PROSE`, `MOUNTS`), and nothing on `main` re-exports. Option B
costs nothing now. It writes a false sentence into every DCIM record of a
ceiling device, and it moves a fact the device knows into every site that
places it. The mount description already says provenance carries the *other*
ways a box mounts, not the one it is drawn and exported by. A ceiling access
point is drawn and exported as a ceiling device.

## 3. A powered device's PoE class and draw

### 3.1 Today

- **The switch side.** `attrs.power.poe-budget-w` is stated by 49 devices
  (31 Juniper, 9 ReadyLinks, 5 Aurcore, 2 MikroTik, `celestica/es1000`,
  `ufispace/s6301-56stp`), with `poe-budget-scope` on 9 of them. It is not a
  schema-defined key. 37 of the 49 values are numbers; 12 are strings, ten of
  them prose such as "405 W available for PoE (Tables 3 and 14)". A tool
  cannot sum against those 12 today. 37 devices also state a free
  `poe-standard`. On 36 of them it is what the switch gives ("IEEE
  802.3af/at" on the EX2300-24P). On `mikrotik/crs309-1g-8s-plus-in` it is
  the input ("IEEE 802.3af/at, and passive PoE (in)"). One key used for both
  directions cannot be summed against a budget. A device that is both, such
  as the GL-8xEP, needs the two facts under separate names, which is why the
  keys below are prefixed `poe-pd-`. Re-filing the CRS309's input is for the
  build task.
- **The port side.** A port group's `attrs.poe` is free prose in 61 devices
  (`802.3at`, `802.3bt 90 W`, `none`, `passive PD (in)`, `802.3af PD`). No
  rule or exporter reads it.
- **The powered side.** No device states, as a number, what it draws at its PD
  port or which 802.3 class it needs. `nokia/xs-010xr-p` carries a `poe-class`
  gap ("the PD class the port negotiates"). `readylinks/gl-8xep` is a PD as
  well as a switch: its PD input is prose (`power-input: 44-56 V DC 1.86 A
  (PoE-PD)`, `power-supply: ... PoE++ up to 90 W input`).
- **"Excluding PoE output" already has a key.** `power-self-max-w`, the box's
  own draw without what it hands on, is stated by the GL-8xEP and eight other
  ReadyLinks switches ("20W (Excluding PoE output)" on the GL-8xEP), and
  `comparable.py` claims it as peak power with the qualifier `self`.
- **`attrs.power` admits extra keys** of type string, number or boolean. It
  also defines some keys with types and enums (`power-envelope`, and the rack
  PDU keys `input-voltage-v`, `input-current-a`, `capacity-kw`).

### 3.2 The proposed keys

All under `attrs.power`, all optional, all describing the device's PD input.

| Key | Type | Meaning |
| --- | --- | --- |
| `poe-pd-standard` | enum: `802.3af`, `802.3at`, `802.3bt` | The highest 802.3 standard the maker names for the PD input: what the device needs to run as specified. |
| `poe-pd-standard-min` | same enum | The lowest standard the maker names, stated only where it differs. Below `poe-pd-standard` the device runs reduced. |
| `poe-pd-class` | integer, 0 to 8 | The 802.3 class the PD input requests, stated only where a source prints it. Never derived from the standard or the draw. |
| `poe-pd-max-w` | number, greater than 0 | The most the device takes in at its PD input, **including anything it hands on** over PoE out or USB. This is the number a tool sums against a switch's budget. |

The enum values are written as the makers print them, without "IEEE". Both
ReadyLinks sheets print the standard and not the class, so neither access point
states `poe-pd-class`. Class 8 is the highest the library's port prose names
("Type 4 Class 8"). The 0 to 8 range is to verify against IEEE 802.3 before
the schema is written.

A key per PD input is enough for every device in view: each has one PoE-in
port. A device with two PD inputs would need these keys on the port instead.
That is not designed here; section 3.7 lists it as open.

### 3.3 Where they live: free keys or schema-defined

**Option 1: free keys** under `attrs.power`, as `poe-budget-w` is. No schema
change. Lint checks the types, the enum and the range. Nothing stops a value
like `802.3at PoE+` or `25 W` except that rule, and a validator that reads only
the schema accepts it.

**Option 2: schema-defined keys** in `attrs.power.properties`, with the types,
enum and range in the schema. Lint checks only what relates two keys. The
schema republish is additive: optional keys, every file valid today stays
valid, `format` does not move.

**Recommendation: option 2.** The point of these keys is that a tool reads
them as numbers and enums. The schema is what every consumer validates
against; a lint rule only runs in this repository. The rack PDU keys
(`input-voltage-v`, `capacity-kw`) set the precedent. `poe-budget-w` shows
what a free key becomes: 12 of 49 values are strings. A schema-defined
`poe-pd-max-w` that accepted only numbers from the start would not drift that
way. Typing `poe-budget-w` itself is not proposed: it would start refusing 12
files that are valid today, which `format-stability.md` counts as breaking.

### 3.4 A draw printed "excluding PoE output"

A powered device that also gives PoE takes in more than it uses. A PSE port
has to supply both. One key keeps one meaning: `poe-pd-max-w` is always the
whole intake, so a tool sums it without reading a scope. The maker's figures
are kept as printed, under the keys that already mean them:

- the figure "excluding PoE output" goes in `power-self-max-w`, as on the
  GL-8xEP;
- what the device hands on goes in `poe-budget-w`, with `poe-budget-scope`
  naming the port, as on any switch;
- `poe-pd-max-w` is the sum of the two, and the provenance shows the
  arithmetic, as `power-output-scope: pass-through-ceiling` already does.

Where the maker prints a figure that includes what is handed on, or does not
say, that figure is `poe-pd-max-w` directly, and the provenance quotes it.

**Considered and not recommended:** a `poe-pd-max-scope` enum
(`whole-intake`, `excluding-poe-output`) beside a `poe-pd-max-w` copied as
printed. It needs no arithmetic in the device file. It moves the sum into every
tool, and a tool that forgets the scope reads a number 13 W short as the
truth. Lint L28 already refuses `power-max-w` on a component for the same
reason: so that a sum cannot resolve to a plausible wrong number.

### 3.5 How lint checks them

With option 2 the schema checks each key alone. One new device rule, numbered
when it is built, checks the keys against each other:

1. `poe-pd-standard-min` is stated only with `poe-pd-standard`, and is lower
   than it (error).
2. `poe-pd-class` is stated only with `poe-pd-standard` (error). Whether a
   class fits a standard is checked against a table taken from IEEE 802.3 when
   the rule is built, not from memory. Until that table is held, this half is
   not built.
3. `poe-pd-max-w` is stated only with `poe-pd-standard` (warning): a draw with
   no standard cannot be checked against a port.
4. With `power-self-max-w` and `poe-budget-w` both stated as numbers,
   `poe-pd-max-w` is at least their sum (warning). This catches a figure
   "excluding PoE output" written straight into `poe-pd-max-w`.
5. A device that states `poe-budget-w` and `poe-pd-standard` but no
   `poe-pd-max-w` is warned. It gives PoE and takes PoE, so its own draw is
   not its intake.

Elsewhere:

- **L28** refuses whole-box power spellings on a component contract. The four
  new keys join its list, because a PD input is the device's.
- **`comparable.py`** gains a fact for `poe-pd-max-w` and one for
  `poe-pd-standard`, so L68's census claims them and a side-by-side lines them
  up.

The check #1296 asks for, "an 802.3bt device on an 802.3at port is reported",
compares `poe-pd-standard` and `poe-pd-standard-min` with the standard of the
switch port the cable lands on. It belongs to the site file (#1297), which
holds the cable. It also needs the switch port's standard as data, which is
prose today (section 3.7).

### 3.6 The exports

Neither DCIM device type has a field for a device's PD draw or class. The
keys go into the comment, as a rack PDU's class does: "PoE powered device:
802.3at (runs on 802.3af), at most 25 W at the PD input." NetBox's interface
template has `poe_mode` and `poe_type` (read in
[breakout-design.md](breakout-design.md)); Nautobot's has neither. Writing
them on the PD port's interface needs the PD port identified as a placement.
That is not done here: the GL-8xEP's PD port is a registered gap.

### 3.7 What this leaves open

- **The switch port's standard as data.** A port group's `attrs.poe` is prose.
  A structured port key is a separate design: it touches 61 devices and
  the PSE side of every PoE switch.
- **`poe-budget-w` as a number everywhere.** 12 of 49 values are strings. A
  lint warning can ask for the number and move the prose to
  `poe-budget-scope`, device by device, before anything sums against them.
- **A device with two PD inputs** would need these keys per port.

### 3.8 Recommendation

Four schema-defined keys under `attrs.power`: `poe-pd-standard`,
`poe-pd-standard-min`, `poe-pd-class` and `poe-pd-max-w`. `poe-pd-max-w`
always means the whole intake. A figure printed excluding PoE output stays in
`power-self-max-w`, and the sum is written out with its arithmetic. One new
lint rule relates them; the class-to-standard half waits for a held copy of
IEEE 802.3.

## 4. The two access points under the recommendations

An example only; the build task models them from their sheets and may find
more. Only the keys this note is about are shown.

**IPC-APWF6-POE-WP**

```yaml
chassis:
  mount: wall                 # "replaces the plate over an existing outlet"
attrs:
  power:
    poe-pd-standard: 802.3at      # "When powered by 802.3at (PoE+), the AP operates with the optimal performance"
    poe-pd-standard-min: 802.3af  # "802.3af (PoE): 15 W ... PoE out disabled"
    poe-pd-max-w: 25              # "802.3at (PoE+): 25 W ... LAN 1 for PoE supply"
    poe-budget-w: 10
    poe-budget-scope: LAN 1, 48 V
```

The sheet lists "LAN 1 for PoE supply" among the conditions of the 25 W
figure and does not say it excludes PoE output, so 25 W is taken as the whole
intake and written directly. No class is printed. The 802.3af mode (15 W,
PoE out off) and idle (8 W) go in the provenance.

**IPC-APWF7-POE-CL**

```yaml
chassis:
  mount: ceiling              # "Install the IPC-APWF7-POE-CL on the ceiling"
attrs:
  power:
    poe-pd-standard: 802.3bt      # "PoE+/PoE++ IEEE 802.3at/bt"
    poe-pd-standard-min: 802.3at
    power-self-max-w: 60          # "60W (Excluding PoE output)"
    poe-budget-w: 12.95           # "LAN1 for PoE power supply (48 V/12.95 W)"
    poe-budget-scope: LAN 1, 48 V
    poe-pd-max-w: 72.95           # 60 + 12.95; the arithmetic is in the provenance
```

Three things the build task has to settle from the sheet, and record where
it cannot:

- The 60 W is printed under "DC power". The sheet prints no separate figure
  for PoE input.
- "USB port for external power supply (5 V/5 W)" is listed with the 60 W
  conditions, and only PoE output is said to be excluded. Whether the 5 W is
  inside the 60 W is not stated.
- The sheet does not say what the AP does on 802.3at, only that it accepts it.
  Whether 72.95 W is within what an 802.3bt PD may draw is to verify against
  IEEE 802.3.

## 5. One-way items

Once a device on `main` uses them, these cannot be renamed or removed without
a format change:

- the `mount` value `ceiling` (option A);
- the key names `poe-pd-standard`, `poe-pd-standard-min`, `poe-pd-class` and
  `poe-pd-max-w`;
- the enum spellings `802.3af`, `802.3at` and `802.3bt`;
- the meaning of `poe-pd-max-w` as the whole intake, including what is handed
  on.

## 6. For the owner to decide

1. Ceiling mounting: option A (`ceiling`) or option B (`wall` with a note).
   Recommended: A.
2. The PD keys: the four names in section 3.2, schema-defined (option 2) or
   free (option 1). Recommended: the four names, schema-defined.
3. "Excluding PoE output": `poe-pd-max-w` as the whole intake, with the sum
   written out (recommended), or a scope enum beside the printed figure.

## 7. Sources

- ReadyLinks, *IPC-APWF6-POE-WP Wi-Fi 6 Wall-Plate Access Point*, product
  datasheet, July 2026.
- ReadyLinks, *IPC-APWF7-POE-CL Wi-Fi 7 Ceiling Access Point*, product
  datasheet, July 2026.
- `spec/schemas/device.schema.json` (`mount`, `attrs.power`),
  `spec/tools/portrayal/lint.py` (L125, L28, L68),
  `spec/tools/portrayal/dcim_export.py` (`u_height`, `is_full_depth`,
  `MOUNT_PROSE`, `comments_for`), `kit/rack/export-data.js` (`MOUNTS`),
  `spec/tools/portrayal/comparable.py`.
- `library/devices/readylinks/gl-8xep/device.yaml` and
  `library/devices/juniper/ex2300-24p/device.yaml`.
- Not held: IEEE 802.3. No class table is cited; each place that would rely on
  one says "to verify against IEEE 802.3".
