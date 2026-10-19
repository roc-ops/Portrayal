# Cable ends: where a cable can land

Status: sections 1 to 6 built in kit 0.30.0, issue #1045. Sections 7 and 8 name
later steps and what the library owes. Builds on
[connectors-power-design.md](connectors-power-design.md) (an inlet is a connector
slot), [connectors-dc-terminal-design.md](connectors-dc-terminal-design.md) (a lug
on a stud), [power-outlets-design.md](power-outlets-design.md) and
[rack-file-v4-design.md](rack-file-v4-design.md).

## 1. What was wrong

A cable landed only on a part of class `port`. No power end in the library is one:
an inlet, an outlet and a DC terminal are class `inlet`, a ground stud is class
`ground`. So no power cord, DC feed or bonding wire could land. The test was written
in three places in the kit and again in a page.

One thing did work, by accident: fit a cord end or a lug (class `port`) into the
slot, then address the cable to `<slot>-occupant`. Nothing is built on that. A plug
is derived from a cable and never stored.

## 2. The rule

**A cable can land on a part of class `port`, or on a connector slot that takes a
cable end.**

- A connector slot is what the build publishes for a part that declares an
  `interface` registered in `connectors.yaml`: an entry of `cages[]` with
  `kind: connector`.
- It takes a cable end when at least one part in its `accepts` is class `port`.
  Class `port` is what every cord end and lug in the library is, and nothing else
  that seats in a slot is: an optic is `transceiver`, a dust cap `cap`, a boot
  `boot`, a touch guard `mechanical`.

So the rule reads two published facts, the slot and the class of what it accepts,
and no class of the receptacle. A new interface needs no kit change and no device
edit: registering it and giving it a cord end is what makes it land.

One function answers it, `cableLandsOn` in `rack/cable-rules.js`, and every reader
in the kit calls it. Counted over the built catalogue of 2026-10-12: every entry
of `cages[]` in `components.json`, and every entry of every panel in each
device's `configs.json`, by the class of the part that presents it:

| slots | presented by | accepts | lands |
|---|---|---|---|
| 7,240 pluggable cages (`kind: cage`) | class `port` | optics | on its optic, as before; the cage is a port and says it holds no optic |
| 3,780 connector slots | class `port` (RJ45, LC, coax, USB, D-sub) | plugs, and caps on fibre | yes, as before |
| 305 connector slots | class `inlet` (C13, C14, C19, C20, Saf-D-Grid, P40, DC barrel, terminal headers, a stud pair) | one cord end or lug | **yes, new** |
| 127 connector slots | class `ground` | one lug | **yes, new** |
| 8 connector slots | class `screw` (the screws of a DC terminal) | one ring lug | **yes, new** |
| 6 connector slots | class `psu` (a placed supply that presents its one inlet) | one cord end | **yes, new**, at the supply |
| 1 connector slot | class `mechanical` (a breaker guard seat) | a touch guard | no |
| every module bay | | modules | no: a bay is not a connector slot |
| a part with no `interface` (a NEMA 5-20R, an Eaton C39, a fixed cord, a terminal drawn as skin art) | | nothing | no, with a sentence (section 5) |

**The address of such an end is the path of the slot**: `psu-1/module/inlet`,
`outlet-rear-3`, `ground`. Never `-occupant`. A cable already saved to an
`-occupant` path keeps working and is not rewritten: it names the same port
(`portPathOf`), so it lands by the slot whether or not anything is fitted there,
and one port still takes one cable.

## 3. The two ends of a cable

A cable is two ends and a cable type. **Each end is checked against what it plugs
into, and the two receptacles are never compared with each other**: a NEMA outlet
feeds a C14 inlet through a cord with a different plug at each end.

- **The plug or lug at an end is derived** from the slot it lands on: the class
  `port` parts in its `accepts`. Exactly one: that one. Several: the end states
  which, in a new optional key `plug` on the end (a component ref); with none
  stated the first is drawn and a sentence says what to set. A stated plug the
  slot does not accept is a warning naming what it does take.
- **"First" is a stated order**, since the order of an accept list as built is
  no promise: the lowest `attrs.rating-a` first, a part that states none after
  those that do, then by ref. A 15 A plug so comes before the 20 A plug of the
  same receptacle, which is the default a NEMA 5-15/20R needs.
- **A DC feed is one cable, and it lands on a screw.** Where a terminal is a
  slot itself (a stud pair that takes one two-hole lug), the feed lands on the
  terminal and its studs are part of it. Where only its screws are slots
  (`common/dc-terminal-24@1`: `lug-1`, `lug-2`, `lug-3`), the feed lands on
  the first free screw in natural order, `<terminal>/lug-1`: free ports group
  the screws under their terminal (`of`) and mark that one (`first`). Every
  screw of a terminal is the same power port to a DCIM, so the row to come
  does not depend on which was taken. An end that names the terminal and no
  screw does not land, and is not moved: its reason names the screws with no
  cable and the path of the first of them, or says every screw has one. The library can end the choice by making the terminal the
  slot (section 8).
- A derived plug is drawn and is never a swap, never a bill-of-materials line and
  never an export row: both ends belong to the cord.
- The slots a cable landed on before this (LC, duplex LC, RJ45) keep their plug
  table and their answers. A port of class `port` with any other connector still
  derives none, as before.

**What an end is** comes from the part that presents the slot, not from its class
alone:

| the part | family | which way | AC or DC |
|---|---|---|---|
| class `ground` | `ground` | none | none |
| states `attrs.outlet` | `power` | hands power on | not stated today |
| states `attrs.input` or `attrs.media` of `ac` or `dc...` | `power` | takes power | as stated |
| class `inlet`, `psu` or `power` otherwise | `power` | not known | not known |
| anything else that takes a cable end | not known | | |

A free end is named for a person from the same facts: "C13 outlet", "C20 inlet",
"terminal-stud ground".

## 4. Media

Two words are added to the saved `media`, and no more:

- **`power`**: a conductor that carries power. An AC cord and a DC feed share it.
  What differs between them (gauge, conductors, colour, connectors) is the cable
  **type**, as Cat 6A U/UTP and F/UTP are types of `cat6a`. A DC feed is ONE
  cable of two conductors, landing on one terminal at each end and exported as one
  row; AC against DC is read from the ends.
- **`ground`**: a bonding conductor. It is its own word because it is not power in
  any consumer: no DCIM has a ground termination, its colour is green, and a
  ground lug on a power stud must be told apart from a feed.

Defaults where the cable names no type, each replaced by a type when one is named:

| | `power` | `ground` |
|---|---|---|
| diameter | 7.1 mm, the `power-c13` cord | 6.3 mm, a 6 AWG building wire; **estimated**, no source held |
| bend radius | 42.6 mm, six diameters, from the table, where it is marked unverified; the mark is carried | none known; the unset figure |
| plug reach | 77.0 mm, a C13 on its stub | the unset figure |
| inside the port | 17.0 mm, a C13 nose in its inlet | 0 |
| short tolerance | the copper rule; **estimated**, no maker tolerance held | the same |
| colour | `#1c1c1c`, the black every cord end is drawn in | `#3f9b4b`, green; **estimated** |
| stock lengths | the one list every media shares | the same |

`cable.add` is offered `power` when the first end that states a family is power,
and `ground` likewise, by the rule that already picks fibre and copper.

## 5. What is said, and what is refused

Nothing here is refused. A mismatch has always been a warning, because a file that
holds one must still load and a person may know better; that stays.

| the cable | said |
|---|---|
| a data cable into a power or ground end | a warning: the media does not suit the end |
| a power cord into a data port | a warning, the same |
| a power end to a ground end | a warning: the ends differ |
| an AC end to a DC end, where both state it | a warning |
| outlet to outlet, or inlet to inlet, where both state it | a warning: a cord runs from an outlet to an inlet |
| a stated plug the slot does not take | a warning naming what it takes |
| an end on a power part with no interface | **loose**: "outlet-9 is NEMA-5-20R, which takes no plug or lug the library knows" |
| an end on a slot of a side, top or bottom view | **loose**: the slot is there and an end can only be given on the front or rear |

Direction is known for DC the way it is for AC, from `attrs.outlet` and
`attrs.input`; a breaker output states neither today, so nothing is said there. A
ground wire has no direction.

## 6. Free ports, and what a page hands the kit

`freePorts` lists the ends a cable can land on. An end that lands by its slot
carries `kind` (`power`, `ground` or `other`), `connector` (the words above) and
`plug`; a port of class `port` is listed exactly as before. `kinds` narrows the
list, so a picker for a data cable asks for `data` alone. Over the 257 devices of
the built catalogue, each in its default configuration, the answer for the 6,763
free ports of class `port` is the same text as before, both where a page hands in
what it always did and where it hands in the slot ends and asks for `data`.

The kit answers from the catalogue wherever the catalogue can:

- **A part in a bay** (`psu-1/module/inlet`): the seated part's own components say
  whether a slot is at the path, what presents it and what it is. Where neither
  the configuration nor a swap names the bay, which is how most supplies sit,
  the bay holds what it ships with, provided the configuration has the bay: a
  bay that states `only-in` is published with it (`configs.json`), and one that
  leaves the configuration out is no bay there.
- **A slot of the device itself** (`outlet-rear-3`, `ground`): `configs.json`
  lists the slot, its panel and what it accepts, so the end lands. **Only on the
  panel this configuration shows**: a device lists the slots of every panel it
  has, and a 24-port build shows another front than the 48-port one, named in
  the configuration's `views`. A slot of another build is not on this one, and
  a path with nothing drawn reads "is not on this panel" as it always did. A
  sweep of every configuration holds that at none. `configs.json` does not say
  what part presents the slot. That is the one thing a page adds, through a named
  reader on the context: **`drawnAt(end)`, the ref of the component drawn at the
  end's path on that panel**, or null. With it the end says what it is and an
  outlet that is no slot is named in its reason. **Without it nothing is
  guessed**: the end lands with no family and no direction, so no warning rests
  on a guess, and an outlet that is no slot reads "is not on this panel" as it
  always did.

So a page that still knows class `port` alone gets true answers from this kit for
every end it reads, with one exception it must close before it offers power
cabling: **without `drawnAt` an outlet-to-outlet or inlet-to-inlet cord on a
device's own slots is not warned about**, since neither end says which it is.
A page supplies `drawnAt` first, and shows those two warnings where they
cannot be missed. To offer the ends, it asks the zone reader for them:
`readSvg(text, {ends})` with the paths `cableEndPaths(item, view, ctx)` gives.
Without `ends` the zone reader answers what it always did.

## 7. Later steps, named

The audit of these steps against the code, and the design of the open ones, is in [power-cords-design.md](power-cords-design.md).

1. **A zero-U part as an end** (a vertical PDU): **done in kit 0.38.0.** An end
   names the part's id as its `item` and one of its own connector slots as its
   `path`. No page reads a part beside the rack, so the catalogue answers for
   the end whole: the slot is its outlet, a C13, C19 or C39 by its interface,
   and its place is the slot's `mate`, which the routes measure to. Where no
   part says which way a coupler faces, IEC 60320's numbering does: odd is a
   female connector (an outlet), even a male inlet. A cord set pairs its ends,
   C13 with C14 and C19 with C20, so a slot that takes two plugs (a C39) draws
   the one that pairs with the plug at the cord's other end.
2. **Ends on side, top and bottom views.** An end states `front` or `rear` only,
   so the ground studs on the sides of a panel cannot be reached yet.
3. **A feed end outside the rack**: the far end of a fixed input cord, a branch
   circuit, a battery plant.
4. **A and B feeds**, and a check that a device is on both.
5. **Named cord types with two ends** (`power-c13` is a C13 and a C14): the type
   then states the plug at each end, and a cord whose plug an end does not accept
   is found from the type alone.
6. **Load**: a breaker has a rating field; nothing records what a device draws.
7. **Two wires on two screws**: a DC feed is drawn as one line for now.
8. **The DCIM cables file**: a power cable and a ground wire are left out of it
   today, each with its reason in the notes, never silently. Writing them needs
   the name each end prints (section 8) and a cable type proved against both
   targets.

## 8. What the library must do

Nothing below needs a kit change: each part lands as soon as it publishes a slot
that accepts a class `port` part.

1. **Interfaces to register** in `connectors.yaml`, each with the part that
   presents it and what it accepts:
   - `nema-5-15r` (accepts a 5-15P), `nema-5-20r` (accepts a 5-15P and a 5-20P),
     on `std/nema-5-20r@1` and any 5-15R added;
   - `eaton-c39` (accepts `generic/c14-plug@1` and `generic/c20-plug@1`) on
     `eaton/c39-outlet@1`;
   - a lug seat on `amphenol-ns/output-terminal@1` (the two screws of one
     circuit as ONE slot, so that a feed has one place to land: a two-hole lug
     where the screws are a stud pair, else a new two-wire end part),
     `amphenol-ns/input-feed-studs@1`, `amphenol-ns/input-stud-pair@1` and
     `amphenol-ns/input-feed-busbar@1`, each with the lug it takes.
   Stating `interface` on a part publishes a slot on every device that places it:
   a new export fact and so a minor on each, by the device lock.
2. **`mates` as one interface or a list** in `component.schema.json`, since a
   5-15P seats in a 5-15R and a 5-20R, and a C14 plug in a C13 outlet and a C39.
   Every reader of `mates` must take both shapes: `render.py` (the accept list
   and `_mounts`), `components_index.py`, `components_catalogue.py`, `lint.py`
   (L12 and the family checks) and, in the kit, `rack/zero-u.js`.
3. **Cord ends to add**, class `port`, drawn from the cable side with a `cable`
   point: `generic/nema-5-15p-plug@1` and a slot-seating `generic/nema-5-20p-plug`
   (the part of that name today is class `inlet` and has no `mates`).
4. **Which way each part faces**: `attrs.outlet` on every part that hands power
   on (the P40 and terminal outputs state none) and `attrs.input` on every part
   that takes it. `std/c13-outlet@1` and `std/c19-outlet@1` state `outlet` and no
   `ac`; stating it lets an AC cord on a DC terminal be found.
5. **Cable types** in `cable-types.yaml`, each sourced or marked estimated: a
   North American SJT cord for each NEMA pair; DC feed pairs by gauge (`media:
   power`, two conductors, their colours); ground wires by gauge (`media:
   ground`, green). The kit reads diameter and bend radius from them as it does
   for every type.
6. **Three supplies whose DC terminal is skin art or nothing** must compose a
   part that presents a lug or plug interface, so that it publishes a slot:
   `ufispace/psu-132-dc@1` (its `terminal-block`), `supermicro/psu-pws-601s-1r@1`
   (no terminal element at all) and `nokia/lpwr-f@1` (its `connector-block`).
   `common/dc-terminal-24@1` and `common/terminal-header-508-5f@2` are the shapes
   to follow. About forty other DC supplies are in the same state.
7. **Nested slots of a part fixed to a chassis are not published.** `csr180`
   and `csr200` place `common/dc-terminal-24@1` and `-27@1` on the chassis as
   `psu1-input` and `psu2-input`. The screws are drawn, but `configs.json`
   lists a device's own placements and not the slots of the parts a placed
   part composes, so nothing lands there, while the same screw lands under a
   bay (`tm-8104`). The build must publish them as it does a four-inlet
   panel's, keyed `<placement>/<part>` (`render.py` `cage_entries`), or the
   terminal must present one interface itself.
8. **The power and ground ends still refused**, counted over the same
   catalogue, each needing an `interface` and something of class `port` to
   accept: `amphenol-ns/output-terminal` (176 placements),
   `amphenol-ns/input-stud-pair` (88), `input-feed-studs` (44),
   `input-feed-busbar` (18), `eaton/c39-outlet` (36), `std/nema-5-20r` (16),
   the two chassis DC terminals above, `common/dc-terminal-plug-2`, the
   `telco-systems` and `nokia` DC parts, `commscope/bp-p1` and `bp-p2`,
   `common/orv3-busbar-connector`, the terminals drawn as skin art under bays
   (about 290 elements), and the parts of class `ground` with no slot
   (`common/ground-symbol` 242, `cisco/a9k-ground-pad`, the `casa` studs,
   `common/ground-screw-washer`). `common/esd-jack` is rightly refused: a
   wrist strap is no cable of the rack.
9. **The name each end prints**, published where the kit can read it beside the
   path, for the DCIM cables file: a numbered outlet (`outlet-9` prints `9`,
   `outlet-front-1` prints `Front 1`) and a module power port (`terminal-block`
   prints `{module}/Inlet`). The type files hold these names already; nothing
   publishes the mapping.
