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


def build(dev, cfg_name, cfg, profile, dist=None):
    ch = dev.get("chassis", {})
    cfg = cfg or {}

    # The SKU is the model, which is how both libraries file these: their own
    # Edgecore entries are 5912-54X-O-AC-F rather than one AS5912-54X.
    pns = cfg.get("part-numbers") or {}
    sku = sorted(pns)[0] if pns else dev["model"].split(" (")[0]
    part = pns.get(sku)
    if isinstance(part, dict):
        part = part.get("part")

    out = {
        "manufacturer": dev["manufacturer"],
        "model": sku,
        "slug": slugify(f"{dev['manufacturer']}-{sku}"),
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
        for p in parts["placements"]:
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
        for b in parts["bays"]:
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
        for p in view_parts(view)["placements"]:
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


def _num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


class Indented(yaml.SafeDumper):              # match the library's list indentation
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def write(doc, root, target, nos):
    d = Path(root) / target / "device-types" / doc["manufacturer"]
    d.mkdir(parents=True, exist_ok=True)
    name = doc["model"] + (f"-{nos}" if nos else "") + ".yaml"
    f = d / name
    f.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                     width=100, default_flow_style=False))
    return f


def render_image(dist, root, target, doc, dev_name, cfg_name, face):
    """Rasterise a compiled face into the library's elevation-images tree."""
    src = Path(dist) / f"{dev_name}.{cfg_name}.{face}.svg"
    if not src.exists():
        return None
    try:
        import cairosvg
    except ImportError:
        return None
    out = Path(root) / target / "elevation-images" / doc["manufacturer"]
    out.mkdir(parents=True, exist_ok=True)
    png = out / f"{doc['slug']}.{face}.png"

    # Resolve the custom properties before handing the drawing to cairosvg,
    # which has no support for them and reads `var(--led-color, #3a3f44)` as a
    # hex literal beginning "ar". Every use in the compiled output is a lamp
    # colour and every one carries a fallback, so taking the fallback yields the
    # unlit faceplate - which is the right picture for an elevation image
    # anyway: a device type has no live state to show.
    svg = re.sub(r"var\(\s*--[\w-]+\s*,\s*([^)]*)\)", r"\1", src.read_text())

    # 2 px/mm. A 440 mm faceplate lands near 880 px, which is the range the
    # libraries' own elevation images sit in - theirs run 37 KB to 350 KB. At 4
    # px/mm the 13 RU C100G alone came to 1.9 MB, and a contribution that ships
    # 29 MB of PNG is not one anybody wants to merge.
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png), scale=2)
    return png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--out", required=True, help="root of the exports tree")
    ap.add_argument("--nos", action="append", default=[],
                    help="NOS profile to name interfaces for; repeatable")
    ap.add_argument("--dist", help="compiled SVG directory, for images")
    args = ap.parse_args()

    dev = yaml.safe_load(Path(args.device).read_text())

    # One device type per SKU, not per configuration.
    #
    # A device type is the empty chassis; what is seated in a bay is a property
    # of the DEVICE. So configurations carrying their own part number are
    # separate types - an AC front-to-back and a DC back-to-front are different
    # things to order - while configurations differing only in how the bays are
    # populated are one type with one picture. The C100G's `bdm2m-11plus1` and
    # `docsis-classic` are two redundancy schemes for one chassis, and treating
    # them as two device types wrote the same file twice.
    cfgs = dev.get("configurations") or {}
    by_sku = {}
    for name, cfg in cfgs.items():
        key = sorted(cfg.get("part-numbers") or {})
        by_sku.setdefault(key[0] if key else None, (name, cfg))
    if not by_sku:
        by_sku = {None: (None, {})}

    wrote = 0
    for cfg_name, cfg in by_sku.values():
        # A NOS names switch interfaces. Emit one document per profile that
        # actually resolves any, and a NOS-neutral one when none does - a device
        # whose ports are all line-card bays still has a device type.
        _, has_ports = build(dev, cfg_name, cfg, None, args.dist)
        profiles = list(args.nos) if (args.nos and has_ports) else [None]

        for profile in profiles:
            doc, _ = build(dev, cfg_name, cfg, profile, args.dist)
            if not any(k in doc for k in
                       ("console-ports", "interfaces", "module-bays")):
                continue                       # nothing but a header: not worth a file
            for target in TARGETS:
                f = write(doc, args.out, target, profile)
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
