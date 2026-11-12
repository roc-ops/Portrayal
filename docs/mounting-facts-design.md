# The facts of a mounting: a device key for what differs between two ways of mounting one box

Status: a design, not built. This note proposes the name and shape of one
optional device key, `chassis.mountings`, and what lint, the lock and the
exporters would do with it. No schema, library, kit or lint file changes with
it. It answers the last open item of #550, the third: the facts that differ
between the two mounts of a 7360 ISAM FX shelf. What was decided on 2026-11-11
is the placement: such facts go in a small optional device key that lists the
mountings, each with its own statement (and not on the terminal that takes the
cable, nor on the rack file's item). The key's name and the other choices below
are proposed, and the questions in section 8 are open.

Read with [rack-products-design.md](rack-products-design.md) section 10 (the
vertical mounting item, `roll`), [cable-lay-design.md](cable-lay-design.md)
section 9 (what the lay does not do) and
[format-stability.md](format-stability.md) (what a new optional key costs).

## 1. What is asked, and what is built

#550 asks that Portrayal show a shelf mounted two ways, and names three kinds
of work. The first two are built: the elevation draws a quarter turn (`roll: 90`
clockwise, `270` the other way), and the vertical kit's two parts that take
units are ordinary devices. The FX-8 shelf's own `chassis.ears.rolled` states
the two brackets that hold it turned; the FX-4 shelf states none on this
checkout. The third is "other facts that differ
between the two mounts, worth carrying as attributes of the mounting, not of
the shelf":

- the power lug a mounting takes (the FX-8: 6 AWG horizontal, 8 AWG vertical);
- the side the power cable leaves by;
- whether the open channel of the rack uprights has to face the shelf.

Both design notes name these as not built and as that issue's: rack-products
section 10 ("the lug size and cable exit as facts of the mounting") and
cable-lay section 9 ("the facts that differ with the mounting (lug size, cable
exit)"). Nothing in the library states one today.

## 2. The key

An optional list on `chassis`, beside `mount`, `ears` and `kits`:

```yaml
chassis:
  mountings:
    - id: horizontal            # segment; unique in the list
      roll: [0]                 # the rack-file rolls it covers: 0 (no `roll`), 90, 180, 270
      lug: {awg: 6}             # the power lug the maker names for this mounting
      cable-exit: left          # up | down | left | right, seen from the device's front as mounted
      channel: toward-shelf     # toward-shelf: the uprights' open channel faces the shelf wall
    - id: vertical
      roll: [90, 270]
      lug: {awg: 8}
```

- `id` and `roll` are required; `roll` is a non-empty list with no value in two
  entries of one device. `lug`, `cable-exit` and `channel` are each optional,
  and an entry states at least one of them. A statement a source does not make is
  left out, never written as unknown.
- `lug.awg` is a positive number, the conductor size of the lug. Other
  figures of a lug (hole size, spacing, part number) are given by the held
  guide as the recommended crimp lug of the power cable, not as a fact of a
  mounting; this note proposes leaving
  them out for now (section 8, Question 4), and they could be added to `lug`
  later, as keys of an object.
- `cable-exit` is the side of the box the cable leaves by in that mounting,
  as the front view of the box as mounted shows it. `channel` has one value now.
- A rack item's `roll` (0 where it has none) selects the entry whose list holds
  it. An item that matches no entry has no statement, which is not an error,
  and a device that states no key reads as it does today.
- A statement's source goes in `provenance.mountings`, as every stated figure's
  does; an estimate says so and has a `gaps` entry.

Why `mountings` and not a second `mount`: `chassis.mount` says how the box is
installed in kind (for example `rack`, `wall` or `ceiling`) and has one value; a rolled and an
unrolled shelf are both `rack`. The two names are close, and a reader may
confuse them; section 8 (Question 1) asks whether another name is better.

## 3. How it relates to what exists

- **`chassis.ears.rolled`** states the brackets that hold the box when it is
  rolled, and the elevation draws them. It says nothing of the lug or the
  exit. The two do not overlap: a mounting with `roll: [90, 270]` and a
  device with `ears.rolled` are the same event seen by different readers. No
  check ties them now (section 5 would add one).
- **A DC port's `awg`** (dc-power-design section 5.2) is what the terminal of a
  part takes, from the part's own source. `mountings[].lug` is the lug the
  maker supplies or requires in a mounting, and it can differ from the
  terminal's range (section 8, Question 2).
- **The rack file** needs no change: `roll` is already an optional item key (rack
  file version 4), and a reader that does not know `mountings` still draws the
  turn.
- **Cable lay.** `cable-exit` is the fact a later lay would read to leave a
  rolled shelf's cable on the side the maker shows. Nothing in the lay reads it
  now, and cable-lay section 9 keeps saying so until it does.

## 4. The two devices that state it first

Source for each row: Nokia, 7360 ISAM FX ANSI Hardware Installation Manual
(3HH-12893-AAAA-TCZZA, Issue 29, R6.9). Pages are the PDF's; the manual's
printed page is one less.

| device | mounting | fact | where |
|---|---|---|---|
| `nokia/nfxs-e-bb` (FX-8) | horizontal, 19 in. rack | lug 6 AWG | parts list, section 9.2.2, p165 |
| | vertical, 19 in. rack | lug 8 AWG | the same list, p165 |
| | horizontal, EIA standard 19 in. rack | open channel faces the shelf wall | section 9.2, Caution 1, p160; Figure 80, p161 |
| | horizontal, as drawn | cables are routed through the left side of the rack to the terminal block on the bottom of the shelf | "Power cable routing and connection" under 10.5.3, p202; Figure 105, p203 |
| `nokia/nfxs-f-bb` (FX-4) | both, 19 in. rack | lug 10 AWG (the largest the terminal block takes) | parts list, section 13.2.2, p255; "Power cable type" under 14.5.3, p302 |
| | horizontal, EIA standard 19 in. rack | open channel faces the shelf wall | section 13.2, Caution 1, p250; Figure 140, p251 |
| | horizontal, as drawn | cables are routed through the left side of the rack to the terminal block on the bottom of the shelf | "Power cable routing and connection" under 14.5.3, and Figure 176, p303 |

The FX-8's parts list for a 23 in. rack (section 9.3.2, p181) names one "8 AWG
power lug" and no 6 AWG, for horizontal and vertical mounting alike, so the 6 AWG
horizontal lug is stated for the 19 in. rack only, and the manual's two lists do
not agree for a horizontal mount in a 23 in. rack (section 8, Question 2).

The FX-4's parts list for a 23 in. rack (section 13.3.2, p270) names no power lug.

The routing text names no mounting and says the cables "can then be routed" to the
terminal block; the figures that go with it (105 and 176) draw a horizontal
shelf, so a `left` exit would be a reading of that text and those figures for the
horizontal mounting only, not a statement the manual makes in those words.

What the guide does not say: that the cable leaves upward when the shelf is
vertical (#550 states it; no text of the manual says it, and Figures 82 and
84, which draw the vertical shelf, show no power cable), and that the FX-4's
lug differs by mounting (it does not: one lug, 10 AWG). The FX-8's power cable
section names an 8 AWG cable and an 8 AWG lug without distinguishing the
mountings, while its parts list gives 6 AWG for the horizontal one (section 8,
Question 2). So the manual supports, for the first entries: the FX-8 lug for
each mounting, the channel (and, read from the figures, the exit `left`) for the
horizontal mounting of both shelves, and the FX-4 lug for both; an exit
statement for the vertical mounting has no source (section 8, Question 2).

## 5. What lint would do

New rules, none written yet, all on devices that state the key (the first free
code is L217 at the time of writing):

- error: `id` is a segment and unique; `roll` holds only 0, 90, 180 and 270, no
  value twice across the list; a statement is an object with only the keys above;
  `lug.awg` is positive; `cable-exit` and `channel` are in their lists.
- error: `mountings` is for a `rack` device only, as `ears` and `kits` are (L125).
- warning: a mounting that covers 90 or 270 on a device with no
  `ears.rolled`, and the reverse (the two readers should agree).
- warning, only where the part that carries the terminal states a DC port with
  `awg`: a `lug.awg` thicker than the terminal's range. This is the
  check that would have caught the disagreement in section 8, Question 2.
- an estimate has a `gaps` entry of its own name (the rule every figure falls
  under).

## 6. What the lock and the exports would do

- **The lock.** Under `chassis` a key that is not in `CHASSIS_SURFACE`
  (`devicelock.py`) is hashed into the shape digest, so it counts as geometry and
  moving it is a major. `test_lock_chassis_split.py` holds the schema's chassis
  keys to the two sets, so `mountings` has to be placed in one. As a stated
  figure it would go in the surface set (a patch to state or correct), as
  `weight-kg` and `ears.h` do; whether `cable-exit` stays there is Question 3.
  If the lay ever reads `cable-exit` to place a cable, that value becomes
  geometry and moving it is a major for each device that states it; `ears` and
  `kits` are surface because the generic ear is never in a published face
  (rack-mounting-design.md), and a lay that places cables from `cable-exit`
  would be a different case. The first statement on a device would then be the bump
  the lock computes for a surface key, a patch as `ears.rolled` was; the lock,
  not this note, has the last word.
- **The DCIM exports.** A device that states the key gains one comment
  sentence per mounting, written as `ears_prose` is in `dcim_export.py`, for
  example `Mounted rolled (90 or 270): power lug 8 AWG.`. A device that states
  none moves no file. The exporter reads it from the device; the comment is part
  of an imported description, so changing the sentence later moves every device
  that states the key.
- **The rack file's exports** (the BOM notes and the device row's comment, which
  already say `Mounted rotated 90 degrees clockwise`) could add the matching
  mounting's lug in the same sentence. That is a kit change and a later order.
- **The elevation, the 3D scene, the faces and the elements file** do not read
  the key and do not move.

## 7. What kind of change it is

A new optional key on the device manifest: format 1 is unchanged and every file
valid before stays valid (format-stability.md, "What is a breaking change").
It is **one-way** in the sense format-stability.md gives the word for an
additive key: from the first device on `main` that states it, the key's name,
the list's shape, the words of `cable-exit` and `channel`, and `roll` as a list
cannot change without a format change, and the served copy of the device schema
is republished in the same release as that device, or a reader validating
against the older copy refuses the device. Before that first device the key can
still be changed freely, since nothing states it; after it, deleting the
statements does not restore the earlier schema for a reader that has already
copied it. Neither `contract` nor the rack file's `version` rises.

## 8. Order of work, and open questions

1. This note.
2. The schema: the key, its `$defs`, a test that the schema and the lock's two
   sets agree, and the served copy.
3. Lint: the rules of section 5, with the lint table and the baseline.
4. The first device: the FX-8 shelf, then the FX-4 shelf, each stating its
   mountings, with the DCIM sentence and its export files and the version bump
   the lock computes. This is a library change with a lock and a full build.
5. A reader in the lay for `cable-exit`, and the rack file's export sentence.

Questions this note leaves open:

- Question 1. Is `chassis.mountings` the right name and place, given `chassis.mount`?
- Question 2. The vertical mounting's cable exit: no held text states "up", and the
  manual's lug (6 AWG horizontal, in the 19 in. list only) is larger than the
  NGFC-H terminal's stated range (up to 8 AWG, M5 studs), while the 23 in. list
  names one 8 AWG lug: which statement does the library keep?
- Question 3. Surface or geometry for `cable-exit`, now or when the lay reads it?
- Question 4. Does `lug` carry only `awg`, or also the part number the manual gives
  (Burndy YAZ8C-2TC10 for the FX-8, Panduit PV10-10R for the FX-4)?
