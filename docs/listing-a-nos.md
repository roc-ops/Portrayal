# Listing a box under a NOS vendor

A white box is sold twice: once by the company that made it, and again by every
NOS vendor that certifies it. NetBox and Nautobot model that the same way the
buyer's asset register does - one device type per manufacturer that sells it -
so the UfiSpace S9510-28DC appears as `UfiSpace/S9510-28DC`, `Arrcus/S9510-28DC`
and `IP Infusion/S9510-28DC`, all the same metal.

Portrayal models the metal once, under its maker, and gives each NOS vendor a
**listing**: a small file under the vendor's namespace that points at the
device and says only what the vendor changes.

```
library/devices/ufispace/s9510-28dc/device.yaml     the metal
library/devices/arrcus/s9510-28dc/listing.yaml      ArcOS on it
library/devices/ipinfusion/s9510-28dc/listing.yaml  OcNOS on it
```

## Before you start

- **The hardware is modelled.** A listing draws nothing. If the box is missing,
  model it first (`docs/modelling-a-device.md`).
- **The vendor lists it, in a document anyone can read.** Every listing cites
  the compatibility list that puts the box on it: the list, its release, the
  row. A pairing known only from material that cannot be published does not go
  in.
- **The vendor is registered.** `spec/schemas/vendors.yaml` has an entry for the
  namespace with `role: software` (or `both`). Arrcus, IP Infusion, DriveNets and
  SONiC are there.

## The file

```yaml
format: 1
kind: listing
hardware: ufispace/s9510-28dc      # <namespace>/<directory> of the device
version: 1.0.0
source: >-
  <compatibility list, release, row>
nos: ocnos
nos-versions: '>=7.0'
portfolio: {line: ..., family: ...}  # the vendor's catalogue words, not the ODM's
interfaces:
  - {physical: 'port-{n}', name: 'ge{n}', range: '1-24'}
  - {physical: mgmt-eth, name: eth0}
```

The directory is named after the hardware (`arrcus/s9510-28dc`), whatever the
vendor calls the box.

**What the vendor calls the box.** `model` is the vendor's own name when it is
not the hardware's (DriveNets sells a UfiSpace S9700-53DX as the NCP-40C), and
`aliases` holds its other spellings. Both are for search and display.

**When one vendor name covers several boxes.** DriveNets sells one NCP-40C on
a UfiSpace S9700-53DX, an Edgecore COR550 and a Delta AGCXD40S. Set `model: NCP-40C`
and `type-name: '{model} ({sku})'`: each exported type is then named after the
vendor's model and kept distinct by the SKU it would otherwise have had -
`DriveNets/NCP-40C (S9700-53DX)`. `type-name` must contain `{sku}`.

**What a DCIM keys on.** One device type is exported per hardware configuration,
under the NOS vendor. Its model is, in order: `configurations.<cfg>.model`; the
first SKU in `configurations.<cfg>.part-numbers`; else the hardware's own SKU.
The hardware's part number carries over unless the listing gives its own. The
configuration keys are the hardware's - a listing renames or renumbers them,
it cannot add one.

**What the NOS calls each port.** `interfaces` maps the drawing's physical ids
to NOS names. `{n}` runs over `range`, and a name may do arithmetic on it
(`Ethernet{(n-1)*4}` for SONiC's lane numbering). `breakout` gives the modes and
the child naming. A port the NOS does not expose is left out, with a comment
saying so, rather than mapped to a name the box would not answer to.

**How the NOS's component tree joins the drawing.** `entity-map` maps the names
a NOS reports over OpenConfig, ENTITY-MIB or ietf-hardware onto physical ids,
`chassis`, or a `region:`. Read it from a live dump where you can; commit the
dump, sanitised, under the hardware's `dumps/` and list it in `dumps`.

## Where the naming comes from

The NOS vendor's own documentation, per platform, or a live unit. SONiC's names
are per platform: each platform's port configuration in sonic-buildimage states
them, and the listing cites that file. Never derive one NOS's names from
another's.

**When nothing states them, leave `interfaces` out and record a gap.** ArcOS is
the worked case. Its CLI reference says the first port is `swp1`, and the two
boxes we hold live dumps for agree, but its DNX examples start at `swp0`, and
none of them names a platform. So a listing for a box nobody has run is
published without `interfaces`, with a `gaps` entry (`what: arcos-port-names`,
`reason: sources-disagree`) that quotes the disagreement and asks for
`show interface brief` from a unit. The export files the type under the NOS
vendor with the faceplate ids, which is true, rather than `swp` names that are
off by one on half the boxes.

## The gates

- **L56** - the listing sits under a software vendor, `hardware` is a device,
  and every configuration, port and component it names is the hardware's.
- **L124** - under one vendor, no two listings export the same DCIM model, and
  an alias names one listing unless every claimant marks it `shared: true`.
  DriveNets is the case: one NCP name can be certified on two ODMs' boxes, and
  each needs its own DCIM model.
- **The lock.** A listing is versioned like a device (`listing.lock.json`). A
  changed port name, model or part number is major; an added configuration
  override is minor; wording is a patch. Bump, then run
  `devicelock.py --library library --update`.

Then `./build.sh`, and `./publish.sh --no-images` to see the exported types
under `library/exports/*/device-types/<Vendor>/`.
