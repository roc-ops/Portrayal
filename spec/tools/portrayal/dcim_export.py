#!/usr/bin/env python3
"""Export a Portrayal device manifest as DCIM device types, for NetBox and Nautobot.

Portrayal is the source of truth for the physical facts; a DCIM is one consumer
of them. This emits the schema shared by netbox-community/devicetype-library and
nautobot/devicetype-library so a device modelled here loads into either without
anyone re-typing port counts by hand.

THREE THINGS THIS DOES THAT THE NAUTOBOT-ONLY EXPORTER DID NOT.

One device type per CONFIGURATION, not per device. A configuration is a real
SKU with its own part number and airflow - 7726-32X-O-AC-F against
7726-32X-O-AC-B - and that is exactly the granularity both libraries model:
their own Edgecore entries are filed as `5912-54X-O-AC-F.yaml`. Collapsing them
lost the part number, forced `airflow` to be dropped whenever two configurations
disagreed, and left no honest way to attach an image, because an AC
front-to-back and a DC back-to-front are not the same picture.

A NOS is optional. The old exporter emitted a file only once it could resolve
switch interfaces for a NOS profile, so a CCAP chassis or an optical shelf -
whose ports are line-card bays, and which run neither ArcOS nor SONiC -
produced nothing at all, despite having console ports, module bays, a weight
and a part number. Not every device takes a NOS; that is a fact about the
device, not a reason to refuse to export it.

A NOS is data. What ArcOS calls a port is stated once, in the device's overlay
(`overlays/arcos.yaml`, `interfaces:`), and the exporter reads it from there -
it does not know any NOS by name. Every device exports under its manufacturer
with ports named by their faceplate id; a device whose overlay declares a NOS
asked for with `--nos` exports a second type with that NOS's names, filed
under the software vendor when the overlay carries an `identity:`. A `--nos`
that no overlay in the build declares is refused.

Nothing is dropped on the floor. What the target schema has no field for goes
into `comments` rather than being lost: the datasheet, the maturity this model
claims, and the attrs that have no home - power envelope, ASIC, CPU. A bay's
`accepts` list goes in its description, because neither library can yet express
it as data (netbox-community/devicetype-library#4497,
nautobot/devicetype-library#24).

  python3 dcim_export.py DEVICE_YAML --out DIR [--nos arcos] [--dist DIR]
"""
import argparse
import re
import pathlib
from pathlib import Path

import yaml

from artifacts import Dist

from manifest import view_parts

# Portrayal media/speed -> DCIM interface type. Every value here is valid in
# both libraries: NetBox's enum is a strict superset of Nautobot's (227 types
# against 115) and there is nothing Nautobot accepts that NetBox does not.
IFACE_TYPE = {
    ("sfp", "25g"): "25gbase-x-sfp28",
    ("sfp", "10g"): "10gbase-x-sfpp",
    ("sfp", "1g"): "1000base-x-sfp",
    ("qsfp", "400g"): "400gbase-x-qsfpdd",
    ("qsfp", "100g"): "100gbase-x-qsfp28",
    ("qsfp", "40g"): "40gbase-x-qsfpp",
    ("rj45", "1g"): "1000base-t",
}
AIRFLOW = {"front-to-back": "front-to-rear", "back-to-front": "rear-to-front"}

# A module's ports are its `parts`. Mapped by component ref, because a cage's
# ref says what the cage IS while the speed it runs at is a property of the card
# - a9k-40ge-b's forty std/sfp-ganged are SFP+, and the attrs say so.
PART_IFACE = {
    "std/sfp-ganged": "10gbase-x-sfpp",
    "common/sfp-plus-cage": "10gbase-x-sfpp",
    "std/sfp": "1000base-x-sfp",
    "std/xfp": "10gbase-x-xfp",
    "std/qsfp-ganged": "40gbase-x-qsfpp",
    "std/qsfp28": "100gbase-x-qsfp28",
    "std/qsfp-dd": "400gbase-x-qsfpdd",
}
# What a cage RUNS AT is a property of the card, not of the cage. So the cage ref
# gives the family and the card's attrs give the speed within it.
#
# Matching by family matters because twelve modules declare more than one: an
# A9K-8HG-FLEX-TR is qsfp-dd AND qsfp28, in std/qsfp-dd and std/qsfp-ganged
# cages respectively, and an SMM 300G is qsfp28 in its QSFP cages and sfp-plus
# in its SFP ones. Applying one declared media to every cage on the card would
# retype half of them.
#
# Two earlier versions of this were wrong in opposite directions. Keeping the
# cage default unless the attr looked "faster" - compared as strings, which is
# not an ordering - meant A9K-40GE-B still exported forty 10G interfaces after
# its contract was corrected to `sfp: 40` (roc-ops/Portrayal#23). Letting the attr win
# outright then retyped every QSFP cage on the mixed cards.
CAGE_FAMILY = {
    "std/sfp-ganged": "sfp",
    "common/sfp-plus-cage": "sfp",
    "std/sfp": "sfp",
    "std/qsfp-ganged": "qsfp",
    "std/qsfp28": "qsfp",
    "std/qsfp-dd": "qsfp-dd",
    "std/xfp": "xfp",
}
# Most specific first: a card declaring both qsfp28 and qsfp is 100G in a QSFP
# cage, because a QSFP28 cage takes a 40G optic too.
FAMILY_ATTRS = {
    "sfp": (("sfp-plus", "10gbase-x-sfpp"), ("sfp", "1000base-x-sfp")),
    "qsfp": (("qsfp28", "100gbase-x-qsfp28"), ("qsfp", "40gbase-x-qsfpp")),
    "qsfp-dd": (("qsfp-dd", "400gbase-x-qsfpdd"),),
    "xfp": (),
}


def cage_type(ref, attrs):
    """The interface type for one cage on one card."""
    for attr, t in FAMILY_ATTRS.get(CAGE_FAMILY.get(ref, ""), ()):
        if attrs.get(attr):
            return t
    return PART_IFACE.get(ref)


PART_CONSOLE = {"std/rj45-ganged": "rj-45", "common/rj45-shielded": "rj-45",
                "std/usb-a": "usb-a"}

# The four-part RJ45 family (sweep_rj45.py / docs/rj45-family-design.md), keyed
# by the FULL ref including @major because a version bump inside this family
# changes what the jack IS, not just its shape: std/rj45@2 and
# std/rj45-ganged@2 are the swept bare jack (console/aux/timing, no lamps);
# common/rj45-eth@1 and common/rj45-ganged-eth@1 are the swept lamped jack
# (Ethernet). Checked in build_module BEFORE the version-less PART_CONSOLE/
# PART_IFACE maps below, on the un-stripped ref, so an unswept std/rj45@1 -
# RE-S-2000, JNP10K-RE1, the MX2000 RCBs, and every other Juniper RE card
# still on the old bare ref - keeps falling through exactly as it always did,
# rather than an id-blind version-less "std/rj45" key exporting its Ethernet
# management jack as a console port (the rj45-common fix round). std/rj45@1
# and std/rj45-ganged@1 old refs are unaffected: the ganged one was already
# in PART_CONSOLE version-less (both its versions read the same either way);
# the plain one still drops out of export, as before this family existed.
FAMILY_PART = {
    "std/rj45@2": ("console", "rj-45"),
    "std/rj45-ganged@2": ("console", "rj-45"),
    "common/rj45-eth@1": ("iface", "1000base-t"),
    "common/rj45-ganged-eth@1": ("iface", "1000base-t"),
}

# ...AND FAMILY_PART IS A FALLBACK, NOT A DECISION. #125 gave std/rj45@2 seven
# jobs - console, aux, serial; ToD, BITS, 1PPS, sync; telemetry - so the ref can
# no longer carry the DCIM type, which is the lesson recorded a few lines below
# and learned twice already (roc-ops/Portrayal#27, #29). Reading the ref alone exported seven
# Juniper timing jacks as CONSOLE PORTS. So the placement's own words are read
# first: an id, role or media naming a timing function makes an `other` interface
# labelled with that function - the treatment PART_RF already gives an SMB timing
# input, which says "a thing this schema has no name for" instead of naming a
# neighbour - and one naming a console keeps the console path. Anchored on
# whitespace or a hyphen so a token cannot fire inside an unrelated word
# ("contact", "topology"), the same anchoring lint.RJ45_BARE uses.
RJ45_TIMING = re.compile(
    r"(^|[\s-])(gm-ptp|1588|bits|tod|pps|sync|ptp|ics|clk)([\s-]|$)", re.I)
RJ45_CONSOLE = re.compile(r"console|aux|serial|(^|[\s-])con([\s-]|$)", re.I)


def rj45_words(part):
    a = part.get("attrs") or {}
    return f"{part.get('id') or ''} {a.get('role') or ''} {a.get('function') or ''} " \
           f"{a.get('media') or ''} {part.get('group') or ''}"


def rj45_timing_label(part):
    """The timing function this RJ45 placement names, upper-cased, or None."""
    m = RJ45_TIMING.search(rj45_words(part))
    return m.group(2).upper() if m else None

# RF and timing connectors. These are INTERFACES, not front ports: a front port
# in both libraries is a patch-panel pass-through and requires a rear_port to
# terminate on, which a connector on a line card does not have. Emitting them as
# front ports made 21 module types invalid before this was noticed.
#
# The connector is not the signal. Casa's 6+12 I/O cards carry DOCSIS on MCX and
# its QAM/US I/O cards carry it on F, so both are `docsis` and the label records
# which connector. The SMB ports on Cisco route processors are gps-10mhz and
# gps-1pps - timing inputs, not network interfaces - so they take `other`, which
# says "a thing this schema has no name for" rather than naming a neighbour.
# An appliance inlet that accepts a C13 cord is a C14 on the equipment side, and
# both DCIMs name it from the inlet.
#
# c20-inlet is here before anything places it. Nothing in the library uses it
# yet, so the entry is unreachable today - but an unmapped inlet does not raise,
# it just drops the power port, and a port that disappears without an error is
# the worst way to find out about a part somebody added.
PART_POWER = {
    "std/c14-inlet": "iec-60320-c14",
    "std/c20-inlet": "iec-60320-c20",
}

# What the PLACEMENT says runs through the connector, when it says.
#
# A housing cannot carry this. Ten identical `common/sfp-plus-cage` can be eight
# 1G and two 10G, and an 8P8C shell is equally an Ethernet port, a console and a
# telemetry link - roc-ops/Portrayal#27 and #29 are the same defect seen twice. The
# library answers both the same way: `attrs` on the placement, which thirty-odd
# parts already carried before either issue was filed.
#
# Keyed (media, speed) and falling back to (media, None), because a medium that
# runs at one rate does not repeat it - rj45-telemetry has no speed to give.
#
# rj45-telemetry is `other` deliberately. It is the Casa switch BDM's link to a
# rectifier shelf: an 8P8C housing carrying a proprietary monitoring protocol,
# which is neither Ethernet nor a console. `other` says "a thing this schema has
# no name for", and that is exactly true; typing it rj-45 console would invite
# somebody to patch it into a terminal server.
PART_MEDIA = {
    ("sfp", "1g"): "1000base-x-sfp",
    ("sfp-plus", "10g"): "10gbase-x-sfpp",
    ("qsfp", "40g"): "40gbase-x-qsfpp",
    ("qsfp28", "100g"): "100gbase-x-qsfp28",
    ("qsfp-dd", "400g"): "400gbase-x-qsfpdd",
    ("rj45-telemetry", None): "other",
}


def placed_type(part):
    """The interface type the placement itself declares, or None."""
    a = part.get("attrs") or {}
    media = a.get("media")
    if not media:
        return None
    speed = a.get("speed")
    return PART_MEDIA.get((media, speed)) or PART_MEDIA.get((media, None))


PART_RF = {
    "std/f-type": ("docsis", "F"),
    "std/mcx": ("docsis", "MCX"),
    "std/smb": ("other", "SMB"),
}

# std/lc-bore is the rx/tx bore of a QSFP transceiver, not a port on a device:
# the transceiver IS the module. A pull tab is furniture.
PART_SKIP = {"common/qsfp-pull-tab", "std/lc-bore"}

# Both libraries take the same device-type document. They differ only in what
# they REQUIRE - NetBox also demands u_height and is_full_depth, which we always
# write - and in the airflow enum, where NetBox allows three values we never
# emit. So one document is written to both trees, and each is validated against
# its own schema so a divergence is caught rather than assumed away.
TARGETS = ("netbox", "nautobot")


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")


def _index_expr(expr, n):
    """`{n}`, `{(n-1)*4}`: arithmetic over the port index, and nothing else.

    The overlay schema's own example for a name pattern is SONiC's
    `Ethernet{(n-1)*4}`, so the braces have to admit an expression - and an
    expression read from a data file is not something to hand to eval() whole.
    Only literals, `n` and the arithmetic operators pass; anything else is the
    overlay's mistake and is refused by name.
    """
    import ast
    tree = ast.parse(expr.strip(), mode="eval")
    ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
          ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if not isinstance(node, ok) or (isinstance(node, ast.Name) and node.id != "n"):
            raise SystemExit(f"overlay interface name {{{expr}}}: only arithmetic over n "
                             f"is allowed in a name pattern")
    return int(eval(compile(tree, "<overlay>", "eval"), {"__builtins__": {}}, {"n": n}))


def _expand(pattern, n):
    """Fill every `{...}` in a name pattern for port n. `{i}` - the breakout
    child index - is not known at the port and is left standing."""
    return re.sub(r"\{([^{}]*)\}",
                  lambda m: m.group(0) if m.group(1).strip() == "i"
                  else str(_index_expr(m.group(1), n)),
                  pattern)


def overlay_names(overlay):
    """physical id -> (NOS interface name, breakout rule or None).

    THE OVERLAY IS THE ONLY SOURCE OF A NOS NAME. This used to be a Python
    function with `if profile == "arcos"` and `if profile == "sonic"` in it,
    while the ArcOS overlay stated the same rule as data with breakout modes the
    Python never read (#63, #56). Two statements of one fact drift, and the code
    won silently. Now the exporter reads `interfaces:` - `physical` with `{n}`
    over `range`, `name` with `{n}` or arithmetic on it - and a NOS with no
    overlay has no names, rather than invented ones.
    """
    out = {}
    for rule in (overlay or {}).get("interfaces") or []:
        phys, name = rule["physical"], rule["name"]
        if "{n}" in phys:
            if not rule.get("range"):
                raise SystemExit(f"overlay interface {phys!r} has {{n}} and no range")
            lo, hi = (int(x) for x in str(rule["range"]).split("-", 1))
            for n in range(lo, hi + 1):
                out[phys.replace("{n}", str(n))] = (_expand(name, n), rule.get("breakout"))
        else:
            out[phys] = (name, rule.get("breakout"))
    return out


def breakout_note(breakout, n):
    """What the overlay says a port can be split into, as prose on the interface.

    A device type lists the ports the metal has. The 4x25G children a breakout
    makes are how a DEVICE is configured, not a fact about the type - so they go
    in the description, modes and the child naming pattern for port n, rather
    than as 96 interfaces the faceplate has not got.
    """
    modes = ", ".join(breakout.get("modes") or [])
    child = breakout.get("child-name")
    parts = [f"Breakout: {modes}" if modes else "Breakout capable"]
    if child:
        parts.append(f"children {_expand(child, n)}")
    return "; ".join(parts)[:200]


def iface_type(p, attrs):
    """DCIM interface type for a port placement, or None when it cannot be
    known. Family from the cage ref, speed from the attrs; an unknown
    combination is skipped rather than guessed."""
    ref = p["ref"]
    fam = ("qsfp" if "qsfp" in ref else
           "rj45" if "rj45" in ref else
           "sfp" if "sfp" in ref else None)
    if fam is None:
        return None
    if fam == "rj45" and attrs.get("role") == "mgmt":
        return "1000base-t"                    # a copper management port is 1G
    speed = attrs.get("speed") or {"qsfp": "100g", "sfp": "25g", "rj45": "1g"}[fam]
    return IFACE_TYPE.get((fam, speed))


def flatten(section, prefix=""):
    """attrs are nested a section deep and sometimes deeper. Read them flat."""
    out = {}
    for k, v in (section or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and not {"value", "unit"} & set(v):
            out.update(flatten(v, f"{key}."))
        else:
            out[key] = v
    return out


def comments_for(dev, cfg_name, cfg):
    """Everything true about the device that the target schema has no field for.

    A DCIM that cannot hold a fact should still be able to show it to whoever
    opens the record, so this is prose rather than nothing.
    """
    lines = []
    if dev.get("description"):
        lines += [dev["description"].strip(), ""]
    if cfg and cfg.get("description"):
        lines += [f"Configuration `{cfg_name}`: {cfg['description'].strip()}", ""]

    ds = dev.get("datasheet") or {}
    if ds.get("url"):
        lines.append(f"Datasheet: {ds.get('title') or ds['url']}")
        if ds.get("title"):
            lines.append(f"  {ds['url']}")
        lines.append("")

    facts = []
    for section, vals in (dev.get("attrs") or {}).items():
        flat = flatten(vals)
        for k, v in flat.items():
            if isinstance(v, (str, int, float)) and str(v).strip():
                facts.append(f"- {section}.{k}: {v}")
    if facts:
        lines.append("Facts carried in the model that this schema has no field for:")
        lines += facts
        lines.append("")

    # WHICH DRAWING THIS RECORD CAME FROM. #48 made a device's version move when
    # its model does, and classifies a moved slot or a renamed id as a MAJOR -
    # which is exactly what invalidates a coordinate or a reference somebody
    # took out of an earlier export. A DCIM record outlives the export that made
    # it, so without this a holder cannot tell a current type from a stale one.
    if dev.get("version"):
        lines.append(f"Drawing version {dev['version']}. A major bump means a "
                     f"slot moved or an id was renamed, so anything cached from "
                     f"an earlier export may no longer line up.")
    if dev.get("maturity"):
        lines.append(f"Model maturity: {dev['maturity']}. Every dimension in the "
                     f"source records where it came from.")
    return "\n".join(lines).strip()


def module_models(dist):
    """Every model the library carries as a MODULE, for telling a FRU part
    number from a chassis one.

    Reads components.json rather than globbing contracts: the index carries
    `kind` and `attrs` for every component, which is all this needs, and it is
    published where a checkout is not."""
    return dist.module_models()


def scoped(items, cfg_name):
    """The items a configuration actually has.

    `only-in: [config, ...]` names the configurations a bay or placement exists
    in; absent means all of them, which is still the answer almost everywhere.
    The renderer filters both lists before anything reads them, and an export
    that does not do the same emits bays the chassis has not got.
    """
    out = []
    for it in items:
        only = it.get("only-in") if isinstance(it, dict) else None
        if only and cfg_name not in only:
            continue
        out.append(it)
    return out


def views_for(dev, cfg_name):
    """The views one configuration actually wears.

    A view carrying `face:` is a VARIANT and belongs only to configurations that
    bind it through `configurations.<name>.views`. Walking every view instead
    put `front-lff-12`'s twelve LFF bays into the 24-bay `base` device type -
    the bays carry no `only-in`, because the binding is what scopes them, so
    `scoped()` had nothing to filter on.

    Same rule as render.resolve_views. A device with no bindings is unaffected.
    """
    views = dev.get("views") or {}
    cfg = ((dev.get("configurations") or {}).get(cfg_name) or {})
    # A BOUND VARIANT REPLACES THE DEFAULT VIEW FOR ITS FACE - it does not join
    # it. Merely adding gave `lff-12` twelve LFF bays AND the twenty-four SFF
    # ones, which is a front this chassis cannot be built with. render.py keys
    # `resolve_views` by FACE for exactly this reason, so the view named after
    # the face drops out when something is bound to it.
    bound = {face: n for face, n in (cfg.get("views") or {}).items()
             if n in views}
    out = [views[n] for n in bound.values()]
    for n, v in views.items():
        if (v or {}).get("face") or n in bound:
            continue
        out.append(v)
    return out


def bay_signature(dev, cfg_name):
    """Which bays this configuration renders, as a comparable key.

    Two configurations are the same device type only if they are the same
    CHASSIS. Before `only-in` that could be assumed - configurations differed
    only in what was seated - but a C40G's `ac-power` genuinely has no pem-1 or
    pem-2, so collapsing it with the DC configurations would give the AC SKU two
    module bays that are not on it.
    """
    ids = []
    for view in views_for(dev, cfg_name):
        for b in scoped(view_parts(view)["bays"], cfg_name):
            ids.append(str(b.get("id") or ""))
    return tuple(sorted(ids))


def build(dev, cfg_name, cfg, overlay, dist=None, frus=None, label=None):
    ch = dev.get("chassis", {})
    cfg = cfg or {}

    # The SKU is the model, which is how both libraries file these: their own
    # Edgecore entries are 5912-54X-O-AC-F rather than one AS5912-54X.
    #
    # A `part-numbers` map does not say which of its keys is the CHASSIS. Taking
    # the alphabetically first exported the S9510-28DC as `FAN-402825-HD`: that
    # device lists only FRUs - a fan and a PSU - and the fan sorts first, so a
    # fan tray became a chassis and the switch vanished from both libraries.
    #
    # No string rule can separate the two. Edgecore's chassis SKU for the
    # AS7726-32X is `7726-32X-O-AC-F` and Celestica's for the ES1010 is
    # `R4048-F91L9-A1`; neither contains the model, and matching on the name
    # would reject both. What IS knowable is the other side: a part number that
    # names a module the library already models is a FRU. Drop those, and if
    # nothing is left fall back to the device's own model - unspecific, but a
    # switch rather than a fan. model/slug is the one field a DCIM import cannot
    # recover from; it is the primary key on both sides.
    pns = cfg.get("part-numbers") or {}
    chassis_pns = [k for k in pns if k not in (frus or ())]
    # PREFER THE CORDLESS SKU, which is the rule render.py:519 already uses to
    # stamp `data-sku` on the faceplate. The two disagreed: render named the
    # variant that ships without a cord - the chassis itself - while this took
    # whichever sorted first, so one drawing and its device type could carry
    # different part numbers for the same thing.
    #
    # Where every SKU in a configuration carries a cord, as on the AS5912-54X
    # whose AC variants are all regional, there is no cordless one to prefer and
    # the first sorted stands. That names the type after a region, which is
    # arbitrary but ORDERABLE - and orderable was the whole complaint.
    cordless = [m for m in chassis_pns
                if ((pns.get(m) or {}) if isinstance(pns.get(m), dict) else {})
                .get("power-cord") in (None, "", "none")]
    sku = (sorted(cordless) or sorted(chassis_pns) or
           [dev["model"].split(" (")[0]])[0]
    part = pns.get(sku)
    if isinstance(part, dict):
        part = part.get("part")

    model = f"{sku} {label}" if label else sku
    out = {
        "manufacturer": dev["manufacturer"],
        "model": model,
        "slug": slugify(f"{dev['manufacturer']}-{model}"),
        "u_height": float(ch.get("ru", 1)),
        "is_full_depth": True,
    }
    if part:
        out["part_number"] = part

    weight = ch.get("weight-kg")
    if weight:
        # Both schemas require a multiple of 0.01. The ASR 9910 is modelled at
        # 64.915 kg and float arithmetic turns 39.69 into 39.690000000000005,
        # so round rather than hand either straight through.
        out["weight"] = round(float(weight), 2)
        out["weight_unit"] = "kg"

    air = AIRFLOW.get(cfg.get("airflow"))
    if air:
        out["airflow"] = air

    if dev.get("description"):
        out["description"] = dev["description"].strip().split(".")[0][:200]

    # Images, if this configuration has been rendered. front_image/rear_image are
    # booleans; the file itself is matched by slug from elevation-images/.
    if dist:
        for face in ("front", "rear"):
            if (Path(dist) / f"{dev['name']}.{cfg_name}.{face}.svg").exists():
                out[f"{face}_image"] = True

    dev_groups = dev.get("groups") or {}

    def attrs_of(p):
        g = dev_groups.get(p.get("group")) or {}
        return {**(g.get("attrs") or {}), **(p.get("attrs") or {})}

    # WHAT THE NOS CALLS EACH PORT comes from the overlay's `interfaces:` rules
    # and from nowhere else. None means no NOS: the document is the hardware's
    # own, and names its ports by the id on the faceplate.
    names = overlay_names(overlay) if overlay is not None else None

    console, mgmt_sfp, bays = [], [], []
    for view in views_for(dev, cfg_name):
        parts = view_parts(view)
        for p in scoped(parts["placements"], cfg_name):
            a = attrs_of(p)
            role, media = a.get("role"), a.get("media")
            if role == "console" and media == "rj45-serial":
                console.append({"name": "Console", "type": "rj-45"})
            elif role == "console" and p["ref"].startswith("std/usb-c"):
                console.append({"name": "Console (USB-C)", "type": "usb-c"})
            elif (role == "mgmt" and a.get("speed") == "10g"
                  and not (names and p["id"] in names)):
                mgmt_sfp.append({"name": p["id"].replace("port-", ""),
                                 "type": "10gbase-x-sfpp", "mgmt_only": True,
                                 "description": "10G management port (faceplate label; "
                                                "not presented as a switch interface)"})
        for b in scoped(parts["bays"], cfg_name):
            name = (b["id"].replace("psu-", "PSU ").replace("fan-", "Fan ")
                    .replace("front-", "Front ").replace("rear-", "Rear "))
            bay = {"name": name, "position": b["id"].rsplit("-", 1)[-1]}
            # Neither library can express what a bay accepts as data yet, so it
            # goes where a person will still see it. Truncated to the 200 the
            # NetBox schema allows on a bay description.
            acc = b.get("accepts") or []
            if acc:
                short = ", ".join(a.split("/")[-1].split("@")[0] for a in acc)
                bay["description"] = f"Accepts: {short}"[:200]
            bays.append(bay)

    # Switch and management interfaces. With an overlay, a placement is an
    # interface exactly when a rule names it - `mgmt-eth` becomes `ma1` because
    # the overlay says so, not because a media attr happened to match. Without
    # one, every `port-N` that is not console or management is an interface
    # under its faceplate id: unspecific, but a fact about the metal rather than
    # a convention borrowed from a NOS the box may not run.
    ports = {}
    for view in views_for(dev, cfg_name):
        for p in scoped(view_parts(view)["placements"], cfg_name):
            pid = p["id"]
            a = attrs_of(p)
            if names is not None:
                if pid not in names:
                    continue
                name, breakout = names[pid]
            else:
                if not pid.startswith("port-") or a.get("role") in ("mgmt", "console"):
                    continue
                name, breakout = pid, None
            t = iface_type(p, a)
            if t is None:                      # unknown combination: skip, do not guess
                continue
            iface = {"name": name, "type": t}
            if a.get("role") == "mgmt":
                iface["mgmt_only"] = True
            if breakout:
                iface["description"] = breakout_note(breakout, _num(pid.rsplit("-", 1)[-1]))
            # management first, then by faceplate number - the order a person
            # reads the front panel in
            ports.setdefault(name, ((0 if a.get("role") == "mgmt" else 1),
                                    _num(pid.rsplit("-", 1)[-1]), iface))

    ifaces = ([i for _, _, i in sorted(ports.values(), key=lambda k: k[:2]) if i.get("mgmt_only")]
              + sorted(mgmt_sfp, key=lambda i: i["name"])
              + [i for _, _, i in sorted(ports.values(), key=lambda k: k[:2]) if not i.get("mgmt_only")])

    if console:
        out["console-ports"] = console
    if ifaces:
        out["interfaces"] = ifaces
    if bays:
        out["module-bays"] = sorted(
            bays, key=lambda b: (b["name"].split()[0], _num(b["position"])))

    body = comments_for(dev, cfg_name, cfg)
    if body:
        out["comments"] = body
    return out


def build_module(contract, manufacturer):
    """A module contract as a DCIM module type."""
    attrs = contract.get("attrs") or {}
    model = str(attrs.get("model") or contract["name"])
    out = {"manufacturer": manufacturer, "model": model}

    if attrs.get("weight-kg"):
        out["weight"] = round(float(attrs["weight-kg"]), 2)
        out["weight_unit"] = "kg"

    if contract.get("description"):
        out["description"] = contract["description"].strip().split(".")[0][:200]

    # Which interface type this card's cages actually run at. The cage ref gives
    # the floor; an attr naming a faster media raises it.
    ifaces, consoles, powers = [], [], []
    for part in contract.get("parts") or []:
        if not isinstance(part, dict):
            continue
        full_ref = part["ref"]
        ref = full_ref.split("@")[0]
        pid = str(part.get("id") or "")
        if ref in PART_SKIP:
            continue
        # The placement is more specific than the ref, so it is checked first.
        # Reaching PART_CONSOLE with an rj45-telemetry part would file a
        # rectifier link as a console port, which is how #29 read before.
        placed = placed_type(part)
        if placed:
            iface = {"name": pid, "type": placed}
            if placed == "other":
                iface["label"] = "RJ45"
            ifaces.append(iface)
        elif full_ref in FAMILY_PART:
            # Checked on the un-stripped ref, before PART_CONSOLE/PART_IFACE
            # below drop the @major and would otherwise catch every version of
            # std/rj45 alike - see FAMILY_PART's comment for why that is wrong.
            # What the PLACEMENT says beats what the ref says, both ways round.
            timing = rj45_timing_label(part)
            if timing:
                ifaces.append({"name": pid, "type": "other", "label": timing})
            elif RJ45_CONSOLE.search(rj45_words(part)):
                consoles.append({"name": pid or "Console", "type": "rj-45"})
            else:
                kind, t = FAMILY_PART[full_ref]
                if kind == "console":
                    consoles.append({"name": pid or "Console", "type": t})
                else:
                    ifaces.append({"name": pid, "type": t})
        elif ref in PART_POWER:
            powers.append({"name": pid or "Inlet", "type": PART_POWER[ref]})
        elif ref in PART_CONSOLE:
            consoles.append({"name": pid or "Console", "type": PART_CONSOLE[ref]})
        elif ref in PART_RF:
            t, connector = PART_RF[ref]
            # The type says what the signal is; the label keeps the connector,
            # which is the part the type cannot express.
            ifaces.append({"name": pid or t, "type": t, "label": connector})
        elif ref in PART_IFACE:
            ifaces.append({"name": pid, "type": cage_type(ref, attrs)})

    if consoles:
        out["console-ports"] = consoles
    if ifaces:
        out["interfaces"] = ifaces
    if powers:
        out["power-ports"] = powers

    body = []
    if contract.get("description"):
        body += [contract["description"].strip(), ""]
    facts = [f"- {k}: {v}" for k, v in attrs.items()
             if k != "model" and isinstance(v, (str, int, float))]
    if facts:
        body.append("Facts carried in the model that this schema has no field for:")
        body += facts
        body.append("")
    # Same reasoning as the device stamp: a module type is cached in a DCIM too,
    # and its faceplate can move under it.
    if contract.get("version"):
        body.append(f"Contract version {contract['version']}.")
    if body:
        out["comments"] = "\n".join(body).strip()
    return out


def _num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


class Indented(yaml.SafeDumper):              # match the library's list indentation
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def overlay_identity(dist, ns, model, profile):
    """What the device is SOLD AS when it runs this NOS, or None.

    A disaggregated box is two products from two companies: Edgecore made the
    metal and the buyer's asset register may well say the software house, because
    that is who invoiced them. Modelling that by duplicating the hardware means
    keeping two full definitions in step forever, so the hardware is modelled once
    and the overlay carries only what the software changes - here, who sells it.

    Absence is meaningful and is the default: an overlay without `identity:` is a
    naming and mapping layer, and its export stays under the manufacturer of
    record exactly as before.
    """
    if not profile:
        return None
    ov = dist.overlay(ns, model, profile)
    return (ov or {}).get("identity") or None


def apply_identity(doc, identity, vendors):
    """Re-file a device type under the software vendor that sells it."""
    if not identity:
        return doc
    display = ((vendors.get(identity["vendor"]) or {}).get("display")
               or identity["vendor"])
    hw_model = doc["model"]
    name = identity["model"]
    if "{model}" in name:
        name = name.replace("{model}", hw_model)
    elif hw_model.lower() not in name.lower():
        # THE HARDWARE'S SKUs DO NOT COLLAPSE. One device can be four orderable
        # things - AC and 48 V, front-to-back and back-to-front - and they are
        # four device types on the hardware side. A NOS identity that names none
        # of them would write four documents to one filename, keeping whichever
        # happened to be last. Appending the hardware model is not elegant; it is
        # the option that loses nothing, and `{model}` exists so an author who
        # cares about the phrasing never reaches this branch.
        name = f"{name} ({hw_model})"
    doc["manufacturer"] = display
    doc["model"] = name
    doc["slug"] = slugify(f"{display}-{name}")
    if identity.get("part-number"):
        doc["part_number"] = identity["part-number"]
    else:
        # The hardware's part number is the METAL's, and this document is no
        # longer about the metal alone. Leaving it would attribute an Edgecore
        # SKU to an Arrcus product.
        doc.pop("part_number", None)
    return doc


def load_vendors(dist):
    """The vendor registry, as published. `vendors.json` is the same content as
    spec/schemas/vendors.yaml and is in the build."""
    return dist.vendors


def write(doc, root, target, nos):
    d = Path(root) / target / "device-types" / doc["manufacturer"]
    d.mkdir(parents=True, exist_ok=True)
    name = doc["model"] + (f"-{nos}" if nos else "") + ".yaml"
    f = d / name
    f.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                     width=100, default_flow_style=False))
    return f


def rasterize(src, png, scale):
    """One compiled drawing to one PNG. None if the drawing or cairosvg is absent.

    Resolves the custom properties first, which cairosvg has no support for -
    it reads `var(--led-color, #3a3f44)` as a hex literal beginning "ar". Every
    use in the compiled output is a lamp colour and every one carries a
    fallback, so taking the fallback yields the unlit faceplate. That is the
    right picture for a type either way: a type has no live state to show.
    """
    if not src.exists():
        return None
    try:
        import cairosvg
    except ImportError:
        return None
    svg = re.sub(r"var\(\s*--[\w-]+\s*,\s*([^)]*)\)", r"\1", src.read_text())
    png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png), scale=scale)
    return png


# TWO JOBS, ONE FLAG, UNTIL NOW. `--images` both wrote `front_image: true` into
# the YAML and rasterised the PNG behind it. The boolean means "a rendered face
# exists in dist", which is true whenever the build ran; the rasterisation is
# 1104 pictures and about two minutes. CI needs the first and throws the second
# away - every PNG under library/exports is gitignored - but dropping `--images`
# to save the time also deleted 692 lines of tracked YAML across 346 files,
# because one switch drove both. `--no-raster` separates them.
RASTER = True


def render_image(dist, root, target, doc, dev_name, cfg_name, face):
    """Rasterise a compiled face into the library's elevation-images tree."""
    # 2 px/mm. A 440 mm faceplate lands near 880 px, which is the range the
    # libraries' own elevation images sit in - theirs run 37 KB to 350 KB. At 4
    # px/mm the 13 RU C100G alone came to 1.9 MB, and a contribution that ships
    # 29 MB of PNG is not one anybody wants to merge.
    return rasterize(Path(dist) / f"{dev_name}.{cfg_name}.{face}.svg",
                     Path(root) / target / "elevation-images" / doc["manufacturer"]
                     / f"{doc['slug']}.{face}.png", 2)


def render_module_image(dist, root, target, doc, ns, name, ver):
    """Rasterise a module's faceplate into the library's module-images tree.

    Keyed by MODEL, not by slug: a module type has no slug property in either
    schema, and the libraries' own trees are named for the model. The filename
    is sanitised the same way the YAML's is, so the pair always agree.

    The drawing keeps its own orientation. A card is drawn as the skin draws it,
    and which way up it ends up is a property of the chassis it is seated in -
    an A9K line card is horizontal in a 9010 and vertical in a 9910 - so there
    is no one rotation that is true of the part itself.
    """
    # Scale 1: the drawing at its own size. cairosvg's scale multiplies the CSS
    # pixel size, so a 41 mm x 396 mm card renders 157 x 1496 - an SFP cage
    # lands near 53 x 30 px, which reads at thumbnail size. It also keeps the
    # files in the range the libraries' own module images occupy: theirs average
    # 58 KB and the Cisco A9K ones are 7 KB, and these come out 10-80 KB. Going
    # up one stop tripled that for detail nothing displays.
    return rasterize(Path(dist) / "components" / f"{ns}--{name}--{ver}--default.svg",
                     Path(root) / target / "module-images" / doc["manufacturer"]
                     / (doc["model"].replace("/", "-") + ".front.png"), 1)


def export_modules(dist, root, images=None):
    """Every module contract in the library, as module types for both targets.

    A module type is an orderable part, so it needs a manufacturer. The
    namespace gives it - learned from the devices, which are the only place the
    library states a manufacturer - and the generic `common/` namespace is
    skipped: a part with no vendor is not something a DCIM can order.
    """
    wrote = skipped = 0
    imaged = set()
    # components.json in place of a glob over contracts, and devices.json in
    # place of one over manifests. The index carries `ns` on both sides, which is
    # what the namespace-to-manufacturer join needs and what a checkout used to
    # be opened for.
    for contract in sorted(dist.modules(), key=lambda c: (c.get("ns") or "", c.get("name") or "")):
        ns = contract.get("ns")
        man = dist.manufacturer_of(ns)
        if not man:
            skipped += 1
            continue
        doc = build_module(contract, man)
        # `major` ARRIVES PREFIXED. It is the version directory's own name, so
        # components.json carries `v1` and not `1` - every other reader strips
        # with `major[1:]` rather than adding. Prefixing again asked for
        # `casa--oob-2p8--vv1--default.svg`, which no build produces, and
        # `rasterize` answers None for an absent drawing rather than raising,
        # so all 376 module images stopped rendering without a word.
        name, ver = contract.get("name"), contract.get("major")
        for target in TARGETS:
            d = Path(root) / target / "module-types" / man
            d.mkdir(parents=True, exist_ok=True)
            # Cisco ships part numbers with slashes in them - A9K-16T/8-B - and
            # a slash is a path separator, not a character. The model keeps the
            # real name; only the filename is sanitised.
            out = d / (doc["model"].replace("/", "-") + ".yaml")
            out.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                               width=100, default_flow_style=False))
            if images and RASTER:
                if render_module_image(images, root, target, doc, ns, name, ver):
                    imaged.add(doc["model"])
        wrote += 1
        print(f"{doc['model']}  ({len(doc.get('interfaces', []))} interfaces, "
              f"{len(doc.get('power-ports', []))} power ports)")
    print(f"module types: {wrote} written, {skipped} skipped for having no manufacturer")
    if images and RASTER:
        print(f"module images: {len(imaged)} of {wrote} rendered")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # THE INPUT IS A PUBLISHED BUILD, NOT A CHECKOUT. Everything this reads is in
    # `dist/`: the compiled SVG carries the device manifest, components.json the
    # contract fields, vendors.json and overlays.json the registries. That is
    # what lets the export live outside the repository that produces them.
    ap.add_argument("--dist", required=True, help="a published build (library/dist)")
    ap.add_argument("--out", required=True, help="root of the exports tree")
    ap.add_argument("--device", help="one device by name; default is every device")
    ap.add_argument("--modules", action="store_true", help="export module types instead")
    ap.add_argument("--nos", action="append", default=[],
                    help="NOS profile to name interfaces for; repeatable")
    ap.add_argument("--no-raster", action="store_true",
                    help="write the image booleans but skip rendering the PNGs "
                         "behind them. What CI wants: the YAML is tracked, the "
                         "pictures are gitignored")
    ap.add_argument("--images", action="store_true",
                    help="rasterise elevations and module faces from the same build")
    args = ap.parse_args()

    dist = Dist(args.dist)
    # A NOS NOBODY DESCRIBES IS AN ERROR, NOT A DEFAULT. `--nos sonic` used to
    # answer from a Python branch and wrote 144 device types for a NOS with no
    # overlay anywhere; now the only source of a NOS name is an overlay, so a
    # profile no overlay declares has nothing to say and the run stops here,
    # before a file is written, naming where the overlay would go.
    known = dist.profiles()
    for p in args.nos:
        if p not in known:
            raise SystemExit(f"--nos {p}: no overlay in {args.dist} declares it. A NOS is "
                             f"described by devices/<vendor>/<model>/overlays/{p}.yaml, "
                             f"with `interfaces:` rules for its names"
                             + (f"; known: {', '.join(sorted(known))}" if known else ""))
    global RASTER
    RASTER = not args.no_raster
    images = args.dist if args.images else None

    if args.modules:
        export_modules(dist, args.out, images)
        return

    names = [args.device] if args.device else [d["name"] for d in dist.devices]
    for name in names:
        export_device(dist, name, args.out, args.nos, images)


def _config_rank(cfg):
    """Which of two collapsing configurations should name the device type.

    Lower wins, and ties keep the one already there so the order inside a rank
    is still the file's. A device states its own default; failing that, `base` is
    the chassis-as-you-order-it and the next best answer.
    """
    cfg = cfg or {}
    if cfg.get("default"):
        return 0
    if cfg.get("kind") == "base":
        return 1
    return 2


def export_device(dist, device_name, out_root, nos, images):
    dev = dist.manifest(device_name)
    frus = module_models(dist)

    # One device type per SKU, not per configuration.
    #
    # A device type is the empty chassis; what is seated in a bay is a property
    # of the DEVICE. So configurations carrying their own part number are
    # separate types - an AC front-to-back and a DC back-to-front are different
    # things to order - while configurations differing only in how the bays are
    # populated are one type with one picture. The C100G's `bdm2m-11plus1` and
    # `docsis-classic` are two redundancy schemes for one chassis, and treating
    # them as two device types wrote the same file twice.
    #
    # The key has to be the SAME sku build() will name the type after, FRUs
    # filtered out - otherwise two configurations collapse under one key and
    # then get written under two different models, or the reverse.
    #
    # Keyed on the SKU and on which bays the configuration renders. The SKU
    # alone was enough while configurations differed only in what was seated;
    # `only-in` means they can now differ in which bays EXIST, and a C40G's
    # `ac-power` has neither pem-1 nor pem-2. Collapsing on the SKU alone hands
    # the AC chassis two module bays it has not got.
    cfgs = dev.get("configurations") or {}
    # AN ILLUSTRATION IS NOT A DEVICE TYPE. `kind: example` is a redundancy
    # scheme or a worked population - a picture, not a thing anyone can order -
    # and before configurations said which they were, the C40G exported a device
    # type called "C40G bdm-3plus1", named after whichever drawing happened to be
    # listed second while two others collapsed into it silently.
    #
    # Kept for rendering: the elevation images still come from every
    # configuration, because "here is a C40G wired for classic DOCSIS" is worth
    # looking at. It is only the ORDERABLE identity that examples must not claim.
    orderable = {n: c for n, c in cfgs.items()
                 if (c or {}).get("kind") in (None, "base", "orderable", "model")}
    cfgs = orderable or cfgs
    # A CONFIGURATION WITH NO SKU, ON A DEVICE THAT HAS THEM, IS NOT A PRODUCT.
    # The ASR 9006's `base` carries no part number of its own - you order the AC
    # chassis or the DC one - so it fell back to the model name and emitted a
    # second device type called "ASR 9006", for the same hardware, under a name
    # nobody can order. That is the complaint this whole issue is about, arriving
    # by a different route.
    #
    # Only when SOMETHING here has a SKU. A device whose configurations carry no
    # part numbers at all still exports, under its model, because a descriptive
    # name beats no device type.
    with_sku = {n: c for n, c in cfgs.items() if (c or {}).get("part-numbers")}
    if with_sku and len(with_sku) < len(cfgs):
        cfgs = with_sku
    by_sku = {}
    for name, cfg in cfgs.items():
        chassis = sorted(k for k in (cfg.get("part-numbers") or {}) if k not in frus)
        key = (chassis[0] if chassis else None, bay_signature(dev, name))
        # WHEN SEVERAL CONFIGURATIONS COLLAPSE, THE DEFAULT ONE NAMES THE TYPE.
        # They share a SKU and share their bays, so the exporter is right to emit
        # one type - but they can still differ in what the type SAYS, and the
        # S7801-54XS is the case: `base` is front-to-rear and `ac-back-to-front`
        # is not, so whichever won supplied the airflow. That was decided by dict
        # order, which is the source file's key order, which is not a decision at
        # all - and it changed the moment the manifest arrived sorted.
        # `default` is the device's own answer to "which one is this, normally".
        prev = by_sku.get(key)
        if prev is None or _config_rank(cfg) < _config_rank(prev[1]):
            by_sku[key] = (name, cfg)
    if not by_sku:
        by_sku = {(None, ()): (None, {})}

    # When one SKU yields more than one chassis, the model has to say which -
    # two files cannot share a name. There is nothing better to name them by:
    # the C40G's four configurations carry no part numbers at all, so the
    # configuration name is what is left. A device whose configurations DO carry
    # part numbers never reaches this and keeps its real SKU as its model.
    per_sku = {}
    for sku, _ in by_sku:
        per_sku[sku] = per_sku.get(sku, 0) + 1
    labels = {key: (key[1] and by_sku[key][0]) if per_sku[key[0]] > 1 else None
              for key in by_sku}

    wrote = 0
    vendors = load_vendors(dist)
    for key, (cfg_name, cfg) in by_sku.items():
        label = labels[key]
        # THE HARDWARE'S OWN DOCUMENT, ALWAYS; A NOS DOCUMENT ONLY WHERE AN
        # OVERLAY DECLARES THAT NOS FOR THIS DEVICE. Asking for `--nos arcos`
        # used to write an ArcOS type for every switch in the library with names
        # made up in Python, UfiSpace and Juniper included, and `--nos sonic` did
        # the same for a NOS no overlay describes (#63, #56). A device with no
        # overlay for a profile now gets nothing for it - the neutral type names
        # its ports by the faceplate and says no more than it knows.
        ns = dev.get("ns")
        profiles = [None] + [p for p in nos if dist.overlay(ns, device_name, p)]

        for profile in profiles:
            overlay = dist.overlay(ns, device_name, profile) if profile else None
            doc = build(dev, cfg_name, cfg, overlay, images, frus, label)
            # DEVICE name, not the configuration's. `name` is rebound by the
            # by-SKU loop above and means a configuration from there on, which
            # silently looked up an overlay that does not exist and filed every
            # ArcOS box under Edgecore instead of Arrcus.
            ident = overlay_identity(dist, dev.get("ns"), device_name, profile)
            doc = apply_identity(doc, ident, vendors)
            if not any(k in doc for k in
                       ("console-ports", "interfaces", "module-bays")):
                continue                       # nothing but a header: not worth a file
            for target in TARGETS:
                f = write(doc, out_root, target, None if ident else profile)
                for face in ("front", "rear"):
                    if doc.get(f"{face}_image") and RASTER:
                        render_image(images, out_root, target, doc,
                                     dev["name"], cfg_name, face)
                wrote += 1
                print(f"{f}  ({len(doc.get('interfaces', []))} interfaces, "
                      f"{len(doc.get('module-bays', []))} bays)")
    if not wrote:
        print(f"skip {dev['name']}: nothing to export")


if __name__ == "__main__":
    main()
