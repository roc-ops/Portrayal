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
# its contract was corrected to `sfp: 40` (roc-ops/ndv#23). Letting the attr win
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
# telemetry link - roc-ops/ndv#27 and #29 are the same defect seen twice. The
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


def nos_name(profile, kind, n, origin=1):
    """Interface name for a port, per NOS convention.

    `origin` is the group's index-origin - where the vendor's own numbering
    starts. SONiC counts lanes from zero whatever the faceplate says, so the
    first port is Ethernet0 on a box silkscreened 1 and on a box silkscreened 0
    alike; assuming 1 gave the AS7946-30XB an interface called `Ethernet-4`.
    """
    if profile == "arcos":
        return {"switch": f"swp{n}", "mgmt": "ma1"}[kind]
    if profile == "sonic":                    # SONiC numbers by lane, not by port
        return {"switch": f"Ethernet{(n - origin) * 4}", "mgmt": "eth0"}[kind]
    raise SystemExit(f"unknown NOS profile: {profile}")


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

    if dev.get("maturity"):
        lines.append(f"Model maturity: {dev['maturity']}. Every dimension in the "
                     f"source records where it came from.")
    return "\n".join(lines).strip()


def module_models(library):
    """Every model the library carries as a MODULE, for telling a FRU part
    number from a chassis one. Empty set if the library cannot be located,
    which leaves the old behaviour rather than guessing."""
    out = set()
    try:
        for f in Path(library).glob("components/*/*/*/contract.yaml"):
            c = yaml.safe_load(f.read_text())
            if c.get("kind") != "module":
                continue
            m = str((c.get("attrs") or {}).get("model") or c.get("name") or "")
            if m:
                out.add(m)
    except OSError:
        pass
    return out


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


def bay_signature(dev, cfg_name):
    """Which bays this configuration renders, as a comparable key.

    Two configurations are the same device type only if they are the same
    CHASSIS. Before `only-in` that could be assumed - configurations differed
    only in what was seated - but a C40G's `ac-power` genuinely has no pem-1 or
    pem-2, so collapsing it with the DC configurations would give the AC SKU two
    module bays that are not on it.
    """
    ids = []
    for view in (dev.get("views") or {}).values():
        for b in scoped(view_parts(view)["bays"], cfg_name):
            ids.append(str(b.get("id") or ""))
    return tuple(sorted(ids))


def build(dev, cfg_name, cfg, profile, dist=None, frus=None, label=None):
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
    sku = sorted(chassis_pns)[0] if chassis_pns else dev["model"].split(" (")[0]
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

    console, mgmt_rj, mgmt_sfp, bays = [], [], [], []
    for view in (dev.get("views") or {}).values():
        parts = view_parts(view)
        for p in scoped(parts["placements"], cfg_name):
            a = attrs_of(p)
            role, media = a.get("role"), a.get("media")
            if role == "console" and media == "rj45-serial":
                console.append({"name": "Console", "type": "rj-45"})
            elif role == "console" and p["ref"].startswith("std/usb-c"):
                console.append({"name": "Console (USB-C)", "type": "usb-c"})
            elif role == "mgmt" and media == "rj45" and profile:
                mgmt_rj.append({"name": nos_name(profile, "mgmt", 0),
                                "type": "1000base-t", "mgmt_only": True})
            elif role == "mgmt" and a.get("speed") == "10g":
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

    ifaces = mgmt_rj + sorted(mgmt_sfp, key=lambda i: i["name"])
    ports = []
    for view in (dev.get("views") or {}).values():
        for p in scoped(view_parts(view)["placements"], cfg_name):
            if not p["id"].startswith("port-"):
                continue
            a = attrs_of(p)
            if a.get("role") in ("mgmt", "console"):
                continue
            ref = p["ref"]
            fam = ("qsfp" if "qsfp" in ref else
                   "rj45" if "rj45" in ref else
                   "sfp" if "sfp" in ref else None)
            if fam is None:
                continue
            speed = a.get("speed") or {"qsfp": "100g", "sfp": "25g", "rj45": "1g"}[fam]
            t = IFACE_TYPE.get((fam, speed))
            if t is None:                      # unknown combination: skip, do not guess
                continue
            try:
                n = int(p["id"].split("-")[1])
            except ValueError:
                continue
            origin = (dev_groups.get(p.get("group")) or {}).get("index-origin", 1)
            ports.append((n, t, origin))

    if profile:
        for n, t, origin in sorted(set(ports)):
            ifaces.append({"name": nos_name(profile, "switch", n, origin), "type": t})

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
    return out, bool(ports)


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
        ref = part["ref"].split("@")[0]
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


def overlay_identity(device_yaml, profile):
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
    f = pathlib.Path(device_yaml).resolve().parent / "overlays" / f"{profile}.yaml"
    if not f.exists():
        return None
    doc = yaml.safe_load(f.read_text()) or {}
    return doc.get("identity") or None


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


def load_vendors(schemas=None):
    root = pathlib.Path(schemas) if schemas else \
        pathlib.Path(__file__).resolve().parents[2] / "schemas"
    try:
        return (yaml.safe_load((root / "vendors.yaml").read_text()) or {}).get("vendors") or {}
    except (OSError, yaml.YAMLError):
        return {}


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


def export_modules(library, root, dist=None):
    """Every module contract in the library, as module types for both targets.

    A module type is an orderable part, so it needs a manufacturer. The
    namespace gives it - learned from the devices, which are the only place the
    library states a manufacturer - and the generic `common/` namespace is
    skipped: a part with no vendor is not something a DCIM can order.
    """
    lib = Path(library)
    ns2man = {}
    for f in sorted(lib.glob("devices/*/*/device.yaml")):
        ns = f.parts[-3]
        ns2man.setdefault(ns, yaml.safe_load(f.read_text()).get("manufacturer"))

    wrote = skipped = 0
    imaged = set()
    for f in sorted(lib.glob("components/*/*/*/contract.yaml")):
        contract = yaml.safe_load(f.read_text())
        if contract.get("kind") != "module":
            continue
        ns = f.parts[-4]
        man = ns2man.get(ns)
        if not man:
            skipped += 1
            continue
        doc = build_module(contract, man)
        name, ver = f.parts[-3], f.parts[-2]
        for target in TARGETS:
            d = Path(root) / target / "module-types" / man
            d.mkdir(parents=True, exist_ok=True)
            # Cisco ships part numbers with slashes in them - A9K-16T/8-B - and
            # a slash is a path separator, not a character. The model keeps the
            # real name; only the filename is sanitised.
            out = d / (doc["model"].replace("/", "-") + ".yaml")
            out.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                               width=100, default_flow_style=False))
            if dist:
                if render_module_image(dist, root, target, doc, ns, name, ver):
                    imaged.add(doc["model"])
        wrote += 1
        print(f"{doc['model']}  ({len(doc.get('interfaces', []))} interfaces, "
              f"{len(doc.get('power-ports', []))} power ports)")
    print(f"module types: {wrote} written, {skipped} skipped for having no manufacturer")
    if dist:
        print(f"module images: {len(imaged)} of {wrote} rendered")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device", nargs="?")
    ap.add_argument("--modules", help="export module types from this library root")
    ap.add_argument("--out", required=True, help="root of the exports tree")
    ap.add_argument("--nos", action="append", default=[],
                    help="NOS profile to name interfaces for; repeatable")
    ap.add_argument("--dist", help="compiled SVG directory, for images")
    ap.add_argument("--library", help="library root; inferred from the manifest path")
    args = ap.parse_args()

    if args.modules:
        export_modules(args.modules, args.out, args.dist)
        return
    if not args.device:
        raise SystemExit("give a device manifest, or --modules LIBRARY")

    dev = yaml.safe_load(Path(args.device).read_text())

    # <library>/devices/<ns>/<name>/device.yaml - so the library is four up.
    # --library overrides it for a tree laid out differently.
    lib = args.library or str(Path(args.device).resolve().parents[3])
    frus = module_models(lib)

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
    by_sku = {}
    for name, cfg in cfgs.items():
        chassis = sorted(k for k in (cfg.get("part-numbers") or {}) if k not in frus)
        key = (chassis[0] if chassis else None, bay_signature(dev, name))
        by_sku.setdefault(key, (name, cfg))
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
    vendors = load_vendors()
    for key, (cfg_name, cfg) in by_sku.items():
        label = labels[key]
        # A NOS names switch interfaces. Emit one document per profile that
        # actually resolves any, and a NOS-neutral one when none does - a device
        # whose ports are all line-card bays still has a device type.
        _, has_ports = build(dev, cfg_name, cfg, None, args.dist, frus, label)
        profiles = list(args.nos) if (args.nos and has_ports) else [None]

        for profile in profiles:
            doc, _ = build(dev, cfg_name, cfg, profile, args.dist, frus, label)
            ident = overlay_identity(args.device, profile)
            doc = apply_identity(doc, ident, vendors)
            if not any(k in doc for k in
                       ("console-ports", "interfaces", "module-bays")):
                continue                       # nothing but a header: not worth a file
            for target in TARGETS:
                f = write(doc, args.out, target, None if ident else profile)
                for face in ("front", "rear"):
                    if doc.get(f"{face}_image"):
                        render_image(args.dist, args.out, target, doc,
                                     dev["name"], cfg_name, face)
                wrote += 1
                print(f"{f}  ({len(doc.get('interfaces', []))} interfaces, "
                      f"{len(doc.get('module-bays', []))} bays)")
    if not wrote:
        print(f"skip {dev['name']}: nothing to export")


if __name__ == "__main__":
    main()
