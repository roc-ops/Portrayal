# What a configuration cannot say — design

*(Started as "config-scoped placements"; a second instance from Cisco widened it.)*

Status: **RESOLVED, 2026-09-16 (roc-ops/Portrayal#193), and kept for the reasoning.** Two thirds of the
shape below are closed and neither took a schema change of the size this note
costed. The dead ends are still worth reading - they are why the answer is where
it is - but do not cost the two options at the top of this note: a fifth route
nobody had tried beat both.

**What actually happened.**

- **Presence** - the C40G's AC inlet panel - is said with **`only-in:`**, which
  scopes a placement or a bay to named configurations and already existed for
  `bays`. The panel carries `only-in: [ac-power]` and the two PEM bays carry
  `only-in: [dc-power, ...]`. An AC chassis has the panel and no PEM openings, a
  DC one the openings and no panel, so they are never both present and the
  overlap route 2 died on never arises. That also answers the "is the model
  DC-shaped?" question at the top: the band holds either, and the view says
  which - the geometry is per configuration and lives where geometry lives.
- **Property** - the 9001-S's licence-disabled ports - is said by
  **`component-attrs` keyed by a placement id**, which is one lookup in
  `instance_group`, not the `placements:` property this note costed. `bay-attrs`
  already took a bay path for the bay half and had no user at all until now.
- **Still open**: a DEVICE attr that changes with the configuration, which is the
  9001-S's 60 Gbps against the 9001's 120. Filed on `cisco/asr-9001` as the
  `config-scoped-device-attrs` gap.

**The lesson worth keeping.** This note costed two schema changes and a
rendering change, and the answer was a field that already existed used on a
thing it had not been used on. Both fixes together are a lookup and two lines of
YAML per device. Reading the whole cost before checking whether an existing
field reaches is how a note like this talks itself into a migration.

---

*Original note, 2026-08-25, unchanged below.* The rendering half of the same
problem (draw order of bay openings against placements) is recorded separately.

## The decision, up front

There are two options and one of them is cheap.

**The cheap one: a targeted rendering change, no schema change at all.** Do not
paint a bay's opening where a placement already covers that area. That single
change rescues the fourth route below — the panel placed unconditionally with
`for: [pem-1, pem-2]`, which already lints clean and is already correct in the DC
configurations. One honest cost: the model would assert the panel exists on a DC
chassis, where it is completely hidden behind the PEMs.

**The thorough one: `placements:` in a configuration, mirroring `bays:`.** One
property in the schema, but it touches `render.py`, the components index, L13,
L14 and L21, all of which assume a placement's `ref` is fixed at declaration.

**And a third possibility that would make both unnecessary** — that the model is
DC-shaped and the renderer is right. The rendering-order note carries it with
equal weight: if the chassis really has ONE opening across
the bottom rear that DC fills with two FRUs and AC covers with one panel, then
two fixed PEM bays is a DC-specific choice baked into the chassis, and there
would be no empty bays to punch holes through the AC panel in the first place.
**A cheap rendering fix that entrenches a DC-shaped model is worse than no fix
at all**, so that question is worth settling first.

The rest of this note is the evidence for all three — and a second
instance, from Cisco, which suggests the gap is one sentence wide:
**a configuration can say what OCCUPIES a bay, but not what is TRUE of
a part.** See "A second instance" below before costing anything.

## The problem, in one device

The Casa C40G ships AC or DC, and the two are different machines at the bottom
of the rear face. The guide draws both: Figures 1-2 and 1-3 for the AC chassis,
1-4 and 1-5 for the DC one.

- **DC**: two power entry modules, side by side, each with a bolted terminal
  cover, four studs in a minus and a plus pair, two release levers and a
  disconnect-power warning. They slide into openings and the guide has
  "Removing the DC power entry modules" and "Replacing the PEMs" procedures.
  So: two bays, `casa/c40g-pem@1`, and the model already does this correctly.
- **AC**: ONE bolted panel across the same band, carrying a rocker ON/OFF
  switch and an IEC C14 inlet for each of the four front-loaded PSUs, with vent
  mesh above and below. It is one panel — checked at 4x, the centre is
  continuous metal with a single captive screw and no seam, no panel edge, no
  gap. There is no remove/replace procedure for it. So: a placement,
  `casa/c40g-ac-inlet-panel@1`, which is built and measured.

The component exists. It cannot be attached to the model, because the format
has no way to say **"this placement is present in this configuration only"**.

The AC rear therefore renders as an empty band today.

## Three routes, and exactly why each fails

### 1. Put it in the configuration

The obvious one. A configuration object accepts exactly `airflow`, `bays`,
`component-attrs`, `default`, `description`, `part-numbers`, `region-context`
and `skins`. There is no `placements`. A configuration can change what sits in
a hole; it cannot change what is bolted to the metal.

### 2. Make it a bay instead

Bays *are* config-scoped, so this looks like the way through. It is not.

The panel occupies the same band as the two PEM bays, so a third bay there
overlaps them and L13 rejects it. L13 has an exemption — a part that declares
`for:` may sit on what it names — and it is the right shape here, because the
panel genuinely does occupy the same opening. But:

```python
# lint.py:753
owned = {p["id"]: set(targets(p.get("for"))) for p in parts_}   # parts_ = placements
```

`owned` is built from `view_parts(view)["placements"]` only. A **placement** can
declare it covers a bay; a **bay cannot declare anything**. So the exemption is
unavailable to precisely the route that needs it.

Worth noting the asymmetry is not obviously wrong — it was written for
indicators sitting on ports — but it means "bay" and "placement" differ in two
ways at once: config-scoping and overlap-declaring, and you cannot have both.

### 3. Mark it `optional:`

`optional: <tag>` exists and is how the rack ears work. It is a **render-time**
flag: `render.py --with <tag>` includes it. `build.sh` emits no `--with`
variants at all, so an optional placement is invisible in every built artefact —
the dist SVGs, the configs JSON, the demo. It hides the panel everywhere rather
than showing it in one configuration.

### A fourth route that half-works, and why it was reverted

Placing the panel unconditionally with `for: [pem-1, pem-2]` lints clean, and is
visually correct in the DC configurations because the PEMs cover it.

In the AC configuration it is worse than nothing. Every bay draws its opening
rect (`#101214`) unconditionally, before its occupant, so an **empty bay is an
opaque black rectangle**. The two empty PEM bays paint straight over the panel
and the result is two black holes with slivers of panel around the edges. That
was tried and reverted. This is the rendering-order half of the same problem,
and either fix would rescue this route.

## What I would add

**`placements:` in a configuration, the same shape `bays:` already has.** A map
from placement id to a ref, or to `null` for "absent here":

```yaml
configurations:
  ac-power:
    placements:
      ac-inlet-panel: casa/c40g-ac-inlet-panel@1
```

with the placement declared on the view carrying no `ref` of its own, exactly as
a bay declares `accepts:` and `default:` and lets configurations choose.

**Cost.** Small in the schema — one property mirroring `bays`. Larger in three
places that assume a placement's `ref` is fixed at declaration: `render.py`'s
placement loop, the components index, and L13, which resolves each placement's
component to size its box and would need to do so per configuration. L14 and L21
also reason about placements and would need the same treatment.

**The cheaper half** is the rendering change described at the top of this note,
and it is worth re-reading before committing to the schema work.

## A second instance, from a different vendor — and the shape they share

The Cisco ASR 9001-S turned up the same wall from the other side, which is what
suggests this is one gap rather than two.

The 9001-S is the same sheet metal as the ASR 9001, sold at half capacity: two
of its four fixed SFP+ ports and one of its two modular bays are **disabled
until a licence is applied**. The cages are physically present and identical.
So it is a configuration, correctly — but the configuration cannot say the one
thing that distinguishes it.

`component-attrs` is the closest mechanism and it misses by one level of
granularity. It is keyed by component NAME, not placement id:

```python
# render.py:239
comp_name = ref.split("/")[-1].split("@")[0]
extra_attrs = (attr_overrides or {}).get(comp_name)
```

So `component-attrs: {sfp-ganged: {...}}` marks **all six** `std/sfp-ganged`
instances on that chassis — both CLUSTER ports and all four SFP+ — when only two
are disabled. Meanwhile a *placement* can carry `attrs:` per instance, but only
at declaration time, so it would be wrong for the full 9001.

**Per instance, or per configuration — you can have either, never both.**

The same edge stops that configuration carrying its own 60 Gbps fabric figure,
because a configuration cannot override device attrs at all.

### The shape

Put the two findings side by side and one sentence covers both:

> A configuration can say what **OCCUPIES** a bay. It cannot say what is
> **TRUE** of a part.

Occupancy is the only axis `configurations:` reaches. Presence of a bolted part,
enablement of a port, a capacity figure that changes with the SKU — all three are
properties rather than occupants, and all three are currently prose in a
`description:` where no tool can read them.

That is worth weighing when costing the schema change at the top of this note. A
`placements:` property fixes one third of it. Extending `component-attrs` to
accept placement ids as well as component names fixes another third and is
probably cheaper — it is a lookup change in `instance_group`, not a new concept.

## Why this is worth deciding rather than shelving

**It recurs.** Any chassis sold AC-or-DC with different rear furniture hits it,
and that is a common way to sell a chassis. The AGR PSU precedent in SKILL.md is
the same problem solved a different way — AC and DC became two components
selected per configuration — which works when the thing is a module in a bay and
does not when it is bolted on.

**It is invisible.** Nothing lints, nothing warns. The AC configuration renders,
looks plausible, and is missing a real part. That is exactly the class the gaps
register exists for, and it cannot even be filed as one: none of the six `reason`
tokens means "the format cannot express this", and inventing a seventh is itself
a schema decision.

## Out of scope

- Doing it here. The payoff is one rear panel; the decision is the point.
- The rendering-order question, recorded separately.
- Whether that band should be one region rather than two fixed PEM bays. The
  chassis arguably has ONE opening there, which DC fills with two FRUs and AC
  covers with one panel. Same question one level up, and not this note's.
